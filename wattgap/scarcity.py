"""Scarcity Radar: before each operating day, score how likely a real-time price spike is.

Timing (ERCOT Protocols 4.1, 4.5.3): Day-Ahead Market bids and offers close at 10:00 CT the day
before, and ERCOT posts DAM Settlement Point Prices and ancillary-service clearing prices (MCPC)
by 13:30 CT. The score for day D is computed at 13:30 CT on D-1 from exactly that:

  * the zone's 24 DAM prices for D (NP4-180-ER archive / NP4-190-CD daily)
  * the day's DAM ancillary-service clearing prices for D (NP4-181-ER archive / NP4-188-CD daily)

It never reads a real-time price. ERCOT's load, wind and solar forecast *vintages* (NP3-565-CD,
NP4-732-CD, NP4-737-CD ...) would be natural inputs, but the no-key MIS keeps only ~7 days of them,
so there is no history to fit or test on; `forecast_context` reads the live ones as context only.

A spike day is a day on which the zone's real-time price reaches $1,000/MWh in at least one
15-minute interval. The model is a three-feature logistic regression, fit on 2019-2023 only.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from math import exp, log
from pathlib import Path

import numpy as np

from . import econ
from .data import INTERVAL_H, dam_day, day, read_archive
from .econ import Battery, Context, Decision, PlannerParams, Policy, breakeven, dam_plan

SPIKE = 1000.0  # $/MWh: a day with any 15-min RT interval at or above this is a spike day
TRAIN = (2019, 2023)  # fit and parameter choice
EVAL = (2024, 2025)  # held out: never used to fit or choose anything
FEATURES = ("log DAM max", "log DAM max / median", "log DAM AS max")
MODEL_FILE = Path(__file__).resolve().parents[1] / "data" / "derived" / "scarcity_model.json"


@lru_cache(maxsize=None)
def _as_by_day(year: int) -> dict[date, float]:
    """Highest DAM ancillary-service clearing price of each day across RRS, NSPIN and ECRS, $/MW-h."""
    starts, cols = read_archive("as", year)
    keep = [c for c in ("RRS", "NSPIN", "ECRS") if c in cols]
    out: dict[date, float] = {}
    for k, t in enumerate(starts):
        out[t.date()] = max(out.get(t.date(), 0.0), *(cols[c][k] for c in keep))
    return out


def features_from(dam: list[float], as_max: float) -> tuple[float, float, float]:
    """The three features from one zone's 24 DAM prices and the day's highest DAM AS clearing price."""
    prices = sorted(dam)
    top, mid = max(prices[-1], 1.0), max((prices[11] + prices[12]) / 2, 1.0)
    return log(top), log(top / mid), log(max(as_max, 1.0))


def features(d: date, zone: str) -> tuple[float, float, float]:
    """Everything ERCOT had published by 13:30 CT on the day before `d`. No real-time prices."""
    return features_from([h[zone] for h in dam_day(d)], _as_by_day(d.year)[d])


def spiked(d: date, zone: str) -> bool:
    return max(i.prices[zone] for i in day(d)) >= SPIKE


@dataclass(frozen=True)
class Model:
    mean: tuple[float, ...]
    scale: tuple[float, ...]
    coef: tuple[float, ...]  # intercept first
    threshold: float  # score at or above which the planner goes into scarcity mode
    hold: float  # scarcity reserve: share of usable energy kept back in the planned hour unless RT beats the bar
    spike_mult: float  # in scarcity mode, sell at full power once RT beats this x max(top DAM, breakeven)
    refill: bool  # in scarcity mode, recharge in any hour RT is under the charge ceiling

    def score(self, x) -> float:
        z = self.coef[0] + sum(c * (v - m) / s for c, v, m, s in zip(self.coef[1:], x, self.mean, self.scale, strict=True))
        return 1 / (1 + exp(-z))


def fit(x: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 50) -> tuple[tuple, tuple, tuple]:
    """Logistic regression by Newton's method on standardized features, small ridge penalty."""
    mean, scale = x.mean(0), x.std(0) + 1e-9
    a = np.hstack([np.ones((len(x), 1)), (x - mean) / scale])
    w = np.zeros(a.shape[1])
    pen = np.eye(len(w)) * l2
    pen[0, 0] = 0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-a @ w))
        g = a.T @ (p - y) + pen @ w
        h = a.T @ (a * (p * (1 - p))[:, None]) + pen
        w -= np.linalg.solve(h, g)
    return tuple(mean), tuple(scale), tuple(w)


def auc(scores, labels) -> float:
    s, y = np.asarray(scores), np.asarray(labels, dtype=bool)
    pos, neg = s[y], s[~y]
    return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())


def load_model(path: Path = MODEL_FILE) -> Model:
    m = json.loads(path.read_text())
    return Model(*(tuple(m[k]) for k in ("mean", "scale", "coef")), m["threshold"], m["hold"], m["spike_mult"], m["refill"])


# ---------------------------------------------------------------- planner + score


def radar_planned(params: PlannerParams, model: Model, scores: dict | None = None) -> Policy:
    """The day-ahead planner, with a scarcity mode on days the radar flags (score >= threshold).

    On a flagged day: (1) in the planned discharge hour, keep `hold` of the usable energy back as a
    scarcity reserve unless real time beats the bar (max of top DAM price and breakeven); (2) anywhere in
    the day, sell at full power once real time beats `spike_mult` x the bar; (3) if `refill`, recharge in
    any other hour real time is no dearer than the plan's cheap DAM hours, so the battery can sell twice around a
    spike. Unflagged days run the normal planner unchanged. The member's 20% floor is never touched.
    """
    base = econ.planned(params)
    cache = scores if scores is not None else {}

    def policy(ctx: Context) -> Decision:
        b, t = ctx.battery, ctx.interval.start
        key = (t.date(), ctx.zone)
        if key not in cache:
            cache[key] = model.score(features(t.date(), ctx.zone))
        if cache[key] < model.threshold:
            return base(ctx)
        plan = dam_plan(t.date(), ctx.zone, params.window_h, b.spec)
        floor_price = breakeven(b.spec, plan.charge_cost)
        bar = max(plan.top_dam, floor_price)
        if not plan.discharge and ctx.price < model.spike_mult * bar:
            return base(ctx)
        if ctx.price >= model.spike_mult * bar:
            return ("DISCHARGE", b.spec.power_kw)
        if t.hour in plan.discharge:
            if ctx.price < floor_price:
                return econ.HOLD
            keep = 0.0 if ctx.price >= bar else model.hold
            held = Battery(b.soc, b.spec, b.floor + keep * (b.spec.max_soc - b.floor))
            left_h = INTERVAL_H * sum(1 for h in plan.discharge for m in range(0, 60, 15)
                                      if (h, m) >= (t.hour, t.minute))
            return ("DISCHARGE", held.max_discharge_kw(left_h))
        # refill only at prices no worse than the plan's own charge hours were expected to cost
        cheap = max(plan.dam[h] for h in plan.charge)
        if model.refill and ctx.price <= cheap:
            return ("CHARGE", b.spec.power_kw)
        return base(ctx)

    return policy


def read_table(name: str) -> list[dict]:
    with (MODEL_FILE.parent / name).open() as f:
        return list(csv.DictReader(f))




# ---------------------------------------------------------------- live: tomorrow's score

LIVE_FILE = MODEL_FILE.parent / "radar_live.json"
ZONES4 = ("LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST")


def live(model: Model | None = None) -> dict:  # pragma: no cover - network
    """Score the next operating day from the DAM files ERCOT posted today (NP4-190-CD prices, NP4-188-CD AS)."""
    from datetime import datetime

    from .warn import CT, _latest
    model = model or load_model()
    dam = _latest(12331)
    cap = _latest(12329)
    day_ = dam[0]["DeliveryDate"]
    as_max = max(float(r["MCPC"]) for r in cap if r["DeliveryDate"] == day_ and r["AncillaryType"].strip() in ("RRS", "NSPIN", "ECRS"))
    out = {"computed": datetime.now(CT).isoformat(timespec="minutes"), "operating_day": day_, "as_max": as_max,
           "threshold": model.threshold, "zones": {}}
    for z in ZONES4:
        prices = [float(r["SettlementPointPrice"]) for r in dam if r["SettlementPoint"] == z and r["DeliveryDate"] == day_]
        s = model.score(features_from(prices, as_max))
        out["zones"][z] = {"score": round(s, 4), "flagged": s >= model.threshold, "dam_max": max(prices)}
    return out


if __name__ == "__main__":  # pragma: no cover
    res = live()
    LIVE_FILE.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
