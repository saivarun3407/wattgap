"""Load the real ERCOT data committed in data/ (see data/PROVENANCE.md).

Real-time 15-minute load-zone prices, day-ahead hourly load-zone prices, and ERCOT's
backcasted residential load profile (kWh per 15 minutes for an average premise).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
ZONES = ("LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST")
INTERVAL_H = 0.25  # ERCOT real-time SPP settles on 15-minute intervals

RT_FILES = ("ercot_rtm_spp_2023-07_09.csv", "ercot_rtm_spp_2026-09-20_21.csv")
DAM_FILES = ("ercot_dam_spp_2023-07_09.csv", "ercot_dam_spp_2026-09-20_21.csv")
LOAD_FILE = "ercot_load_profile_reshiwr.csv"

# The two headline days. Both are real; each needs its prior day for trailing percentiles.
SCENARIOS = {
    "spike": date(2023, 9, 6),  # ERCOT EEA2 evening, prices near the $5,000 cap
    "quiet": date(2026, 9, 21),  # an ordinary September Monday, this week
}
SELECTION = (date(2023, 7, 2), date(2023, 8, 31))  # planner parameters are chosen here only (Jul 1 = look-back)
EVALUATION = (date(2023, 9, 1), date(2023, 9, 30))  # never used to choose anything


@dataclass(frozen=True)
class Interval:
    start: datetime  # timezone-aware, America/Chicago
    prices: dict[str, float]  # real-time $/MWh by load zone
    home_kwh: dict[str, float]  # household use this interval, kWh, by load zone

    @property
    def system_price(self) -> float:
        """Simple average of the four load zones: a proxy for system-wide conditions."""
        return sum(self.prices.values()) / len(self.prices)


def _read(name: str, key: str) -> dict[datetime, dict[str, float]]:
    with (DATA / name).open() as f:
        return {datetime.fromisoformat(r[key]): {z: float(r[z]) for z in ZONES} for r in csv.DictReader(f)}


@lru_cache(maxsize=None)
def _all_intervals() -> tuple[Interval, ...]:
    load = _read(LOAD_FILE, "interval_start_ct")
    rows = [Interval(t, p, load[t]) for name in RT_FILES for t, p in _read(name, "interval_start_ct").items()]
    return tuple(sorted(rows, key=lambda i: i.start))


@lru_cache(maxsize=None)
def _by_day() -> dict[date, list[Interval]]:
    out: dict[date, list[Interval]] = {}
    for i in _all_intervals():
        out.setdefault(i.start.date(), []).append(i)
    return out


def day(d: date) -> list[Interval]:
    rows = _by_day().get(d)
    if not rows:
        raise KeyError(f"no ERCOT data for {d}; see data/PROVENANCE.md")
    return rows


@lru_cache(maxsize=None)
def _dam() -> dict[date, list[dict[str, float]]]:
    out: dict[date, list[dict[str, float]]] = {}
    for name in DAM_FILES:
        for t, p in sorted(_read(name, "hour_start_ct").items()):
            out.setdefault(t.date(), []).append(p)
    return out


def dam_day(d: date) -> list[dict[str, float]]:
    """24 hourly day-ahead prices for delivery day `d`, published by ERCOT the day before."""
    hours = _dam().get(d)
    if not hours or len(hours) != 24:
        raise KeyError(f"no ERCOT day-ahead prices for {d}; see data/PROVENANCE.md")
    return hours


def days_between(first: date, last: date) -> list[date]:
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]


@lru_cache(maxsize=None)
def _load_by_start() -> dict[str, dict[str, float]]:
    return {i.start.isoformat(): i.home_kwh for i in _all_intervals()}


def home_kwh(start_iso: str, zone: str) -> float:
    """Average-premise household kWh for the interval starting at `start_iso` in `zone`."""
    return _load_by_start()[start_iso][zone]
