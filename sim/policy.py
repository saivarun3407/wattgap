"""Naive overnight vs price-aware dispatch. No ML."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Opportunity:
    interval: str
    zone: str
    action: str  # CHARGE | DISCHARGE
    price: float
    reason: str


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    i = min(len(ys) - 1, max(0, int(round((p / 100) * (len(ys) - 1)))))
    return ys[i]


def naive_action(hour: int) -> str:
    return "CHARGE" if hour >= 23 or hour < 7 else "HOLD"


def aware_action(
    price: float,
    hist: list[float],
    load_frac: float,
    wind_drop: bool,
    online: bool,
    stale: bool,
    soc: float,
) -> str:
    if not online or stale:
        return "HOLD"
    p20 = percentile(hist, 20)
    p80 = percentile(hist, 80)
    tight = load_frac >= 0.9 or wind_drop
    if price <= p20 and soc < 0.9:
        return "CHARGE"
    if price >= p80 and tight and soc > 0.2:
        return "DISCHARGE"
    return "HOLD"
