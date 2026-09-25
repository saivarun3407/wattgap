"""Load the real ERCOT data committed in data/ (see data/PROVENANCE.md).

Real-time 15-minute load-zone prices, day-ahead hourly load-zone prices, and ERCOT's
backcasted residential load profile (kWh per 15 minutes for an average premise).
"""

from __future__ import annotations

import csv
import gzip
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
# Yearly ERCOT archives (NP6-785-ER, NP4-180-ER, NP4-181-ER), every load zone and hub. Large and
# git-ignored: `make archive` (scripts/fetch_archive.py) writes them. Only the multi-year analyses need them.
ARCHIVE = DATA / "archive"

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
        return sum(self.prices[z] for z in ZONES) / len(ZONES)


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


def archive_path(kind: str, year: int) -> Path:
    return ARCHIVE / f"{kind}_{year}.csv.gz"


def archive_years() -> list[int]:
    """Years with both real-time and day-ahead archives on disk."""
    return sorted(int(p.name[3:7]) for p in ARCHIVE.glob("rt_*.csv.gz") if archive_path("dam", int(p.name[3:7])).exists())


@lru_cache(maxsize=None)
def read_archive(kind: str, year: int) -> tuple[tuple[datetime, ...], dict[str, tuple[float, ...]]]:
    """(interval starts, {settlement point or AS product: values}) from data/archive/{kind}_{year}.csv.gz."""
    path = archive_path(kind, year)
    if not path.exists():
        raise KeyError(f"no archive {path.name}; run `make archive`")
    with gzip.open(path, "rt") as f:
        r = csv.reader(f)
        head = next(r)
        rows = list(r)
    starts = tuple(datetime.fromisoformat(x[0]) for x in rows)
    cols = {h: tuple(float(x[k]) if x[k] else float("nan") for x in rows) for k, h in enumerate(head) if k}
    return starts, cols


@lru_cache(maxsize=None)
def _archive_days(year: int) -> dict[date, list[Interval]]:
    starts, cols = read_archive("rt", year)
    out: dict[date, list[Interval]] = {}
    for k, t in enumerate(starts):
        out.setdefault(t.date(), []).append(Interval(t, {p: v[k] for p, v in cols.items()}, {}))
    return out


@lru_cache(maxsize=None)
def _archive_dam(year: int) -> dict[date, list[dict[str, float]]]:
    """24 clock hours per day: the repeated fall-back hour is averaged, the missing spring hour copies the one before."""
    starts, cols = read_archive("dam", year)
    by: dict[date, dict[int, list[dict[str, float]]]] = {}
    for k, t in enumerate(starts):
        by.setdefault(t.date(), {}).setdefault(t.hour, []).append({p: v[k] for p, v in cols.items()})
    out = {}
    for d, hours in by.items():
        row = []
        for h in range(24):
            hs = hours.get(h)
            row.append({p: sum(x[p] for x in hs) / len(hs) for p in hs[0]} if hs else dict(row[-1]))
        out[d] = row
    return out


def day(d: date) -> list[Interval]:
    """One day's real-time intervals. The archive (every zone and hub) wins where present; the committed
    files carry the same load-zone prices plus home load, which is kept."""
    rows = _by_day().get(d)
    if archive_path("rt", d.year).exists() and d in _archive_days(d.year):
        load = {i.start: i.home_kwh for i in rows or []}
        rows = [Interval(i.start, i.prices, load.get(i.start, {})) for i in _archive_days(d.year)[d]]
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
    if not hours and archive_path("dam", d.year).exists():
        hours = _archive_dam(d.year).get(d)
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
