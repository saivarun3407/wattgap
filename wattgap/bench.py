"""Throughput and per-tick latency of the supervisor + asyncio unit workers.

Run:  python3 -m wattgap.bench 10000 50000
Each tick: plan, sign one HMAC command per unit, every worker verifies and applies it,
signs telemetry, and the supervisor verifies every reply and checks SoC physics.
"""

from __future__ import annotations

import asyncio
import os
import platform
import statistics
import sys
import time

from .live import Sim

TICKS = 8


async def bench(size: int) -> dict:
    sim = Sim(start="13:45", size=size, secret=b"bench-secret")  # 13:45 CT: a discharge tick
    t0 = time.perf_counter()
    await sim.start()
    startup = time.perf_counter() - t0
    for b in sim.desk.batches.values():
        sim.desk.approve(b.id)
    lat = []
    for _ in range(TICKS):
        t = time.perf_counter()
        rep = await sim.step()
        lat.append(time.perf_counter() - t)
        for b in [b for b in sim.desk.batches.values() if b.status == "pending"]:
            sim.desk.approve(b.id)
    await sim.stop()
    return {
        "units": size, "ticks": TICKS, "startup_s": startup,
        "p50_ms": statistics.median(lat) * 1000, "max_ms": max(lat) * 1000,
        "units_per_s": size / statistics.median(lat),
        "last_healthy": rep.healthy, "last_delivered_mw": rep.delivered_mw,
    }


def main(sizes: list[int]) -> None:
    print(f"python {platform.python_version()} · {platform.machine()} · {os.cpu_count()} CPUs · single process")
    print(f"{'units':>8} {'startup s':>10} {'p50 tick ms':>12} {'max tick ms':>12} {'unit-cmds/s':>12} {'healthy':>8}")
    for n in sizes:
        r = asyncio.run(bench(n))
        print(f"{r['units']:>8} {r['startup_s']:>10.2f} {r['p50_ms']:>12.1f} {r['max_ms']:>12.1f} "
              f"{r['units_per_s']:>12,.0f} {r['last_healthy']:>8}")


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [10_000])
