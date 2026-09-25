#!/usr/bin/env python3
"""Fit the Scarcity Radar on 2019-2023, then backtest it on held-out 2024 and 2025.

Needs the yearly archives (`make archive`). Steps:
  1. features (DAM prices and DAM ancillary prices, published by 13:30 CT the day before) and labels
     (did the zone's RT price reach $1,000/MWh) for every day and competitive load zone
  2. logistic regression fit on 2019-2023 only
  3. the planner's scarcity-mode parameters (score threshold, hold multiple) chosen on 2019-2023 only
  4. for every year: share of the perfect-foresight bound captured by the fair schedule, the planner,
     and the planner + radar (home battery: 40 kWh / 20 kW, 20% reserve)
Writes data/derived/scarcity_model.json, scarcity_capture.csv, scarcity_days.csv.
Run:  python3 scripts/scarcity.py
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import asdict
from datetime import date
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wattgap import econ  # noqa: E402
from wattgap import locations as L  # noqa: E402
from wattgap import scarcity as S  # noqa: E402
from wattgap.data import ZONES, days_between  # noqa: E402

YEARS = list(range(S.TRAIN[0], S.EVAL[1] + 1))
THRESHOLDS = (0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.85)
GRID = [(h, m, r) for h in (0.0, 0.5, 1.0) for m in (1.0, 1.25) for r in (False, True)]


def year_days(y: int) -> list[date]:
    return days_between(date(y, 1, 1), date(y, 12, 31))


def run(policy, y: int, z: str) -> float:
    return econ.simulate("", z, year_days(y), start_soc=econ.SPEC.reserve_soc, policy=policy, explain=False).net


def train_value(args) -> float:
    m = S.Model(*args)
    return sum(run(S.radar_planned(econ.PLANNER, m), y, z) for y in range(S.TRAIN[0], S.TRAIN[1] + 1) for z in ZONES)


def gap_split(y: int) -> dict:
    """Where the planner's gap to the bound sits: spike days vs ordinary days ($ per home, four zones).
    Daily $ is attributed to the day it was earned (a charge bought the night before counts on that day)."""
    out = {"spike_planner": 0.0, "spike_bound": 0.0, "other_planner": 0.0, "other_bound": 0.0}
    for z in ZONES:
        starts, prices = L.year_prices(y, z)
        bound = L.daily(starts, L.perfect_foresight(prices).cash)
        res = econ.simulate("", z, year_days(y), start_soc=econ.SPEC.reserve_soc, policy=econ.POLICIES["wattgap"], explain=False)
        mine: dict = {}
        for st in res.steps:
            d = date.fromisoformat(st.start[:10])
            mine[d] = mine.get(d, 0.0) + st.cash - st.wear
        for d in year_days(y):
            k = "spike" if S.spiked(d, z) else "other"
            out[f"{k}_planner"] += mine.get(d, 0.0) / len(ZONES)
            out[f"{k}_bound"] += bound[d] / len(ZONES)
    return out


def main() -> None:
    rows = [(y, d, z, S.features(d, z), S.spiked(d, z)) for y in YEARS for d in year_days(y) for z in ZONES]
    train = [r for r in rows if S.TRAIN[0] <= r[0] <= S.TRAIN[1]]
    mean, scale, coef = S.fit(np.array([r[3] for r in train]), np.array([r[4] for r in train], dtype=float))
    print("coefficients (intercept, " + ", ".join(S.FEATURES) + "):", [round(c, 3) for c in coef])

    # choose scarcity-mode params on the training years only
    pf = {(y, z): L.perfect_foresight(L.year_prices(y, z)[1]).net for y in YEARS for z in ZONES}
    base = {(y, z): run(econ.POLICIES["wattgap"], y, z) for y in YEARS for z in ZONES}
    fair = {(y, z): run(econ.POLICIES["scheduled"], y, z) for y in YEARS for z in ZONES}
    scores: dict = {}
    grid = []
    train_base = sum(base[(y, z)] for y in range(S.TRAIN[0], S.TRAIN[1] + 1) for z in ZONES)
    print(f"  train  planner without radar ${train_base / 20:8.2f}/home-yr")
    cands = [(mean, scale, coef, th, *g) for th in THRESHOLDS for g in GRID]
    with Pool() as pool:
        vals = pool.map(train_value, cands)
    for v, c in zip(vals, cands, strict=True):
        grid.append((v, *c[3:]))
        print(f"  train  threshold {c[3]:<4} hold {c[4]:<3} spike_mult {c[5]:<4} refill {c[6]!s:<5} ${v / 20:8.2f}/home-yr")
    v, th, hold, mult, refill = max(grid)
    model = S.Model(mean, scale, coef, th, hold, mult, refill)
    radar = {(y, z): run(S.radar_planned(econ.PLANNER, model, scores), y, z) for y in YEARS for z in ZONES}

    S.MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    S.MODEL_FILE.write_text(json.dumps({
        **asdict(model), "features": S.FEATURES, "spike_usd_per_mwh": S.SPIKE, "train_years": S.TRAIN,
        "eval_years": S.EVAL, "grid": [{"threshold": t, "hold": h, "spike_mult": m, "refill": r,
                                        "train_usd_per_home_yr": round(x / 20, 2)} for x, t, h, m, r in grid],
        "train_planner_usd_per_home_yr": round(train_base / 20, 2)}, indent=1) + "\n")

    out = []
    for y in YEARS:
        r = [x for x in rows if x[0] == y]
        sc = [model.score(x[3]) for x in r]
        lab = [x[4] for x in r]
        flag = [s >= th for s in sc]
        tp = sum(f and lab_ for f, lab_ in zip(flag, lab, strict=True))
        tot = {k: sum(v[(y, z)] for z in ZONES) for k, v in
               {"pf": pf, "fair": fair, "planner": base, "radar": radar}.items()}
        out.append({"year": y, "window": "train" if y <= S.TRAIN[1] else "held-out",
                    "spike_zone_days": sum(lab), "flagged_zone_days": sum(flag), "hits": tp,
                    "recall": round(tp / max(sum(lab), 1), 3), "precision": round(tp / max(sum(flag), 1), 3),
                    "auc": round(S.auc(sc, lab), 3) if 0 < sum(lab) < len(lab) else "",
                    **{f"{k}_usd_per_home": round(v / len(ZONES), 2) for k, v in tot.items()},
                    **{f"{k}_share": round(tot[k] / tot["pf"], 3) for k in ("fair", "planner", "radar")}})
    with (S.MODEL_FILE.parent / "scarcity_capture.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    with (S.MODEL_FILE.parent / "scarcity_days.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["day", "zone", "score", "flagged", "spiked"])
        for y, d, z, x, lab in rows:
            if y >= S.EVAL[0]:
                s = model.score(x)
                w.writerow([d.isoformat(), z, round(s, 4), int(s >= th), int(lab)])

    print(f"\nchosen on {S.TRAIN[0]}-{S.TRAIN[1]}: threshold {th}, hold {hold}, spike_mult {mult}, refill {refill}")
    print("| Year | Window | Spike zone-days | Flagged | Hits | AUC | Upper bound $/home | Fair | Planner | Planner + radar |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in out:
        print(f"| {r['year']} | {r['window']} | {r['spike_zone_days']} | {r['flagged_zone_days']} | {r['hits']} | {r['auc']} | "
              f"${r['pf_usd_per_home']:.2f} | {r['fair_share']:.1%} | {r['planner_share']:.1%} | {r['radar_share']:.1%} |")

    print("\nWhere the planner's gap to the bound sits ($ per home-year, four-zone average):")
    for y in S.EVAL[0], S.EVAL[1]:
        g = gap_split(y)
        print(f"  {y}: spike days planner ${g['spike_planner']:.2f} of ${g['spike_bound']:.2f} "
              f"({g['spike_planner'] / g['spike_bound']:.0%}); other days ${g['other_planner']:.2f} of "
              f"${g['other_bound']:.2f} ({g['other_planner'] / g['other_bound']:.0%})")


if __name__ == "__main__":
    main()
