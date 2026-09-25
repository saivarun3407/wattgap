"""Where a battery earns most: perfect-foresight upper bound and the fair schedule, per zone and year.

The upper bound is a linear program over a whole year of real 15-minute prices: the most any
battery with the stated physics could have earned with perfect knowledge of every price. It is a
ceiling for comparison, not a forecast. Needs the yearly archives (`make archive`).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np

from .data import INTERVAL_H, read_archive
from .econ import SPEC, Spec

DERIVED = Path(__file__).resolve().parents[1] / "data" / "derived"
# 1 MW / 2 MWh, same round-trip efficiency and wear as the home battery, no member reserve
MW_SPEC = Spec(capacity_kwh=2000.0, power_kw=1000.0, reserve_soc=0.0)
ZONE_POINTS = ("LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST", "LZ_AEN", "LZ_CPS", "LZ_LCRA", "LZ_RAYBN")
HUB_POINTS = ("HB_HOUSTON", "HB_NORTH", "HB_SOUTH", "HB_WEST", "HB_PAN", "HB_HUBAVG", "HB_BUSAVG")


@dataclass
class Bound:
    net: float  # $ over the run: energy cash minus wear
    cash: np.ndarray  # $ per interval (energy cash minus wear), for daily attribution
    grid_kwh: np.ndarray  # + delivered, - drawn
    soc: np.ndarray  # state of charge after each interval


def perfect_foresight(prices: np.ndarray, spec: Spec = SPEC, hours: float = INTERVAL_H) -> Bound:
    """Maximum net $ for one battery that knows every price in advance (linear program, HiGHS).

    Variables per interval: kWh drawn c, kWh delivered d, stored kWh s. Charging stores c*sqrt(RTE),
    delivering d empties d/sqrt(RTE). Starts empty at the floor; no value for energy left at the end.
    Simultaneous charge and discharge is not ruled out (an LP can't); it only pays at negative prices.
    """
    from scipy.optimize import linprog
    from scipy.sparse import diags, eye, hstack

    n, eta = len(prices), spec.leg_eff
    p = np.asarray(prices, dtype=float) / 1000  # $/kWh
    lo, hi = spec.reserve_soc * spec.capacity_kwh, spec.max_soc * spec.capacity_kwh
    step = spec.power_kw * hours
    obj = np.concatenate([p, -(p - spec.degradation_per_kwh), np.zeros(n)])  # minimize cost
    # s_t - s_{t-1} - eta*c_t + d_t/eta = 0, with s_{-1} = lo
    a = hstack([-eta * eye(n), eye(n) / eta, eye(n) - diags([np.ones(n - 1)], [-1])], format="csr")
    b = np.zeros(n)
    b[0] = lo
    bounds = [(0, step)] * (2 * n) + [(lo, hi)] * n
    r = linprog(obj, A_eq=a, b_eq=b, bounds=bounds, method="highs")
    if r.status != 0:
        raise RuntimeError(r.message)
    c, d, s = r.x[:n], r.x[n:2 * n], r.x[2 * n:]
    cash = p * (d - c) - spec.degradation_per_kwh * d
    return Bound(float(cash.sum()), cash, d - c, s)


def daily(starts, values) -> dict[date, float]:
    out: dict[date, float] = {}
    for t, v in zip(starts, values, strict=True):
        out[t.date()] = out.get(t.date(), 0.0) + float(v)
    return out


def concentration(by_day: dict[date, float], top: int = 10) -> tuple[float, date, float]:
    """Share of the total carried by the `top` best days, and the best day with its share."""
    total = sum(by_day.values())
    ranked = sorted(by_day.items(), key=lambda kv: -kv[1])
    return sum(v for _, v in ranked[:top]) / total, ranked[0][0], ranked[0][1] / total


def claimed_method(starts, prices: np.ndarray, rte: float = 0.9) -> float:
    """The earlier quick estimate, reproduced to check it: per day, hourly-average RT, sell the top 2 hours at
    rte and buy the bottom 2, no wear, no charge-before-discharge ordering. $ per MW."""
    hourly: dict[tuple, list[float]] = {}
    for t, v in zip(starts, prices, strict=True):
        hourly.setdefault((t.date(), t.utcoffset(), t.hour), []).append(v)
    days: dict[date, list[float]] = {}
    for (d, _, _), vs in hourly.items():
        days.setdefault(d, []).append(sum(vs) / len(vs))
    total = 0.0
    for hs in days.values():
        s = sorted(hs)
        total += max(rte * sum(s[-2:]) - sum(s[:2]), 0.0)
    return total


def year_prices(year: int, point: str) -> tuple[tuple, np.ndarray]:
    starts, cols = read_archive("rt", year)
    return starts, np.array(cols[point])


def read_table(name: str = "locations.csv") -> list[dict]:
    with (DERIVED / name).open() as f:
        return list(csv.DictReader(f))
