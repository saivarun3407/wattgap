"""Measured throughput and per-tick latency, four ways. Prints a markdown table.

Run:  python3 -m wattgap.bench            (or: make bench)

* fleet   the real supervisor (live.Sim): one asyncio task per device, an ed25519 signature on
          every command and every reply, SoC physics checks. Single process.
* tcp     the same supervisor, but the devices run in separate OS processes over localhost TCP.
* signed  the per-device ed25519 path (sign, verify and apply, sign, registry verify), sharded
          over one process per CPU. No asyncio or network overhead.
* math    the vectorized supervisor math (headroom, per-zone allocation, physics check, heartbeat),
          sharded over one process per CPU. Device physics is simulated in the shard: no crypto,
          no network.
"""

from __future__ import annotations

import asyncio
import os
import platform
import statistics
import sys
import time

import numpy as np

from .desk import Clock
from .live import Sim
from .security import new_key
from .shard import ShardPool
from .transport import TcpTransport

CPUS = os.cpu_count() or 1


def summarize(mode: str, units: int, startup: float, lat: list[float], note: str) -> dict:
    p50 = statistics.median(lat)
    p95 = sorted(lat)[max(0, round(0.95 * len(lat)) - 1)]
    return {"mode": mode, "units": units, "startup_s": startup, "ticks": len(lat), "p50_ms": p50 * 1000,
            "p95_ms": p95 * 1000, "cmds_per_s": units / p50, "note": note}


async def fleet(units: int, ticks: int = 8, tcp: bool = False) -> dict:
    clock = Clock()
    transport = TcpTransport(clock, per_host=50) if tcp else None
    # 15:00 CT on 2023-09-06: every zone is discharging, so every unit gets real work
    sim = Sim(start="15:00", size=units, key=new_key(), clock=clock, transport=transport,
              desk_timeout_s=3600, reply_timeout=1.0 if tcp else 0.25)
    t0 = time.perf_counter()
    await sim.start()
    startup = time.perf_counter() - t0
    lat = []
    for _ in range(ticks):
        for b in [b for b in sim.desk.batches.values() if b.status == "pending"]:
            sim.desk.approve(b.id)
        t = time.perf_counter()
        rep = await sim.step()
        lat.append(time.perf_counter() - t)
    await sim.stop()
    assert rep.healthy == units, rep
    note = f"{units // 50} device processes" if tcp else "1 process"
    return summarize("tcp" if tcp else "fleet", units, startup, lat, note)


def sharded(kind: str, units: int, ticks: int) -> dict:
    t0 = time.perf_counter()
    pool = ShardPool(units, CPUS, kind)
    startup = time.perf_counter() - t0
    earn, charge = np.ones(4, dtype=bool), np.zeros(4, dtype=bool)
    lat = []
    for _ in range(ticks):
        t = time.perf_counter()
        _, ok = pool.tick(earn, charge)
        lat.append(time.perf_counter() - t)
    pool.close()
    assert ok > 0.99 * units
    return summarize(kind, units, startup, lat, f"{CPUS} shard processes")


SUITE = [
    ("fleet", 1_000), ("fleet", 10_000),
    ("tcp", 2_000),
    ("signed", 10_000), ("signed", 100_000),
    ("math", 10_000), ("math", 100_000), ("math", 1_000_000), ("math", 10_000_000),
]


def run(mode: str, units: int) -> dict:
    if mode in ("fleet", "tcp"):
        return asyncio.run(fleet(units, tcp=mode == "tcp"))
    return sharded(mode, units, ticks=20 if mode == "math" else 5)


def main(suite=SUITE) -> None:
    print(f"python {platform.python_version()} · {platform.machine()} · {CPUS} CPUs · "
          f"{time.strftime('%Y-%m-%d %H:%M %Z')}\n")
    print("| mode | units | startup | p50 tick | p95 tick | unit commands/s | where |")
    print("|---|---:|---:|---:|---:|---:|---|")
    for mode, units in suite:
        r = run(mode, units)
        print(f"| {r['mode']} | {r['units']:,} | {r['startup_s']:.2f} s | {r['p50_ms']:,.1f} ms | "
              f"{r['p95_ms']:,.1f} ms | {r['cmds_per_s']:,.0f} | {r['note']} |", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    main([(args[i], int(args[i + 1])) for i in range(0, len(args), 2)] if args else SUITE)
