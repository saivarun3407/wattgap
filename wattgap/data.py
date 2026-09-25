"""Load the real ERCOT load-zone prices committed in data/ (see data/PROVENANCE.md)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
ZONES = ("LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST")
INTERVAL_H = 0.25  # ERCOT real-time SPP settles on 15-minute intervals

FILES = ("ercot_rtm_spp_2023-09.csv", "ercot_rtm_spp_2026-09-20_21.csv")

# The two headline days. Both are real; each needs its prior day for trailing percentiles.
SCENARIOS = {
    "spike": date(2023, 9, 6),  # ERCOT EEA2 evening, prices near the $5,000 cap
    "quiet": date(2026, 9, 21),  # an ordinary September Monday, this week
}


@dataclass(frozen=True)
class Interval:
    start: datetime  # timezone-aware, America/Chicago
    prices: dict[str, float]  # $/MWh by load zone

    @property
    def system_price(self) -> float:
        """Simple average of the four load zones: a proxy for system-wide conditions."""
        return sum(self.prices.values()) / len(self.prices)


@lru_cache(maxsize=None)
def _all_intervals() -> tuple[Interval, ...]:
    rows: list[Interval] = []
    for name in FILES:
        with (DATA / name).open() as f:
            for r in csv.DictReader(f):
                rows.append(
                    Interval(
                        datetime.fromisoformat(r["interval_start_ct"]),
                        {z: float(r[z]) for z in ZONES},
                    )
                )
    rows.sort(key=lambda i: i.start)
    return tuple(rows)


def day(d: date) -> list[Interval]:
    rows = [i for i in _all_intervals() if i.start.date() == d]
    if not rows:
        raise KeyError(f"no ERCOT data for {d}; see data/PROVENANCE.md")
    return rows


def days_between(first: date, last: date) -> list[date]:
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]
