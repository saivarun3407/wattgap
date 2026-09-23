#!/usr/bin/env python3
"""WattGap: identify ERCOT-like opportunities and quantify fleet inefficiency."""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

from fleet import Fleet, Unit, apply_action
from policy import Opportunity, aware_action, naive_action

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "sample_prices.csv"
ZONES = ["LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST"]


def load_rows(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def hour_of(ts: str) -> int:
    # 2024-08-20T16:10:00Z
    return int(ts[11:13])


def main() -> int:
    rng = random.Random(42)
    rows = load_rows(DATA)
    hist: dict[str, list[float]] = {z: [] for z in ZONES}

    naive = Fleet(
        [Unit(f"n-{i}", ZONES[i % 4], soc=rng.uniform(0.3, 0.7)) for i in range(50)]
    )
    aware = Fleet(
        [Unit(f"a-{i}", ZONES[i % 4], soc=u.soc) for i, u in enumerate(naive.units)]
    )

    opps: list[Opportunity] = []
    killed = False

    for i, row in enumerate(rows):
        ts = row["interval"]
        hour = hour_of(ts)
        load_frac = float(row["load_frac"])
        wind_drop = row["wind_drop"] == "1"
        stale = row.get("stale", "0") == "1"

        if i == 36 and not killed:
            n = aware.kill_zone("LZ_WEST", 0.3, rng)
            print(f"\nFAIL  interval {ts}  killed {n} LZ_WEST units (LTE)\n")
            killed = True

        for z in ZONES:
            price = float(row[z])
            hist[z].append(price)
            window = hist[z][-288:]  # ~24h if 5-min
            na = naive_action(hour)
            aa = aware_action(price, window, load_frac, wind_drop, True, stale, 0.5)
            if aa == "DISCHARGE" and na != aa:
                opps.append(
                    Opportunity(
                        ts,
                        z,
                        aa,
                        price,
                        "tight grid" if wind_drop or load_frac >= 0.9 else "price tail",
                    )
                )

            for u in naive.units:
                if u.zone == z:
                    apply_action(u, naive_action(hour), price)
            for u in aware.units:
                if u.zone == z:
                    act = aware_action(
                        price, window, load_frac, wind_drop, u.online, stale, u.soc
                    )
                    apply_action(u, act, price)

    naive_rev = sum(u.revenue for u in naive.units)
    aware_rev = sum(u.revenue for u in aware.units)
    gap = aware_rev - naive_rev
    online = sum(1 for u in aware.units if u.online)

    print("WattGap — opportunity + efficiency (sample_prices.csv)\n")
    print(f"intervals          {len(rows)}")
    print(f"opportunities      {len(opps)}  (aware action != naive)")
    print(f"naive $            {naive_rev:8.2f}")
    print(f"aware $            {aware_rev:8.2f}")
    print(f"WATTGAP $          {gap:8.2f}   ← projector number")
    print(f"fleet online       {online}/50 after kill")
    print("\nNext opportunities (first 8):")
    for o in opps[:8]:
        print(f"  {o.interval}  {o.zone:12}  {o.action:10}  ${o.price:7.1f}/MWh  {o.reason}")

    if opps:
        o = opps[len(opps) // 2]
        print("\nHomeowner receipt (facts only):")
        print(
            f"  Your Core in {o.zone.replace('LZ_', '').title()} would {o.action.lower()} "
            f"this interval because price was ${o.price:.0f}/MWh ({o.reason})."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
