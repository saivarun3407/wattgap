"""The fleet across a real process boundary: every battery device runs in a separate OS process
and talks to the supervisor over localhost TCP. Chaos kills are real SIGKILLs.

Run:  python3 -m wattgap.netdemo      (or: make demo-net)
"""

from __future__ import annotations

import asyncio
import os
import time

from .demo import B, CYN, DIM, END, GRN, RED, YEL, pending, say, show
from .desk import Clock
from .live import Sim
from .transport import TcpTransport

UNITS, PER_HOST = 400, 10


async def main() -> None:
    clock = Clock()
    transport = TcpTransport(clock, per_host=PER_HOST)
    sim = Sim(start="14:30", size=UNITS, clock=clock, transport=transport, desk_ttl_s=60, desk_timeout_s=30)
    t0 = time.perf_counter()
    await sim.start()
    hosts = transport.hosts()
    say(f"1. {UNITS} devices in {len(hosts)} OS processes ({PER_HOST} per process), one TCP connection each, "
        f"supervisor pid {os.getpid()}")
    print(f"  {len(sim.fleet.registry.keys)} ed25519 public keys enrolled in {time.perf_counter() - t0:.1f} s "
          f"{DIM}(each private key was generated inside its device's process){END}")

    say("2. Replay the real 2023-09-06 afternoon until the planner asks the desk")
    batch = None
    while batch is None:
        t = time.perf_counter()
        rep = await sim.step()
        show(rep, sim)
        print(f"    {DIM}tick round trip over TCP: {(time.perf_counter() - t) * 1000:.0f} ms{END}")
        batch = next(iter(pending(sim)), None)
    sim.desk.approve(batch.id)
    print(f"  {GRN}operator APPROVED {batch.id}: {batch.target_mw:.2f} MW in {', '.join(batch.zones)}{END}")
    show(await sim.step(), sim)

    zone = batch.zones[0]
    say(f"3. SIGKILL 30% of the {zone} host processes")
    victims = set(sim.fleet.kill_zone(zone, 0.3))
    for pid, ids, _ in transport.hosts():
        if victims & set(ids):
            print(f"  {RED}kill -9 {pid}{END}  {DIM}({len(ids)} devices: {ids[0]} … {ids[-1]}){END}")
    await asyncio.sleep(0.2)
    for _ in range(2):
        show(await sim.step(), sim)
    alive = sum(running for _, _, running in transport.hosts())
    print(f"  {GRN}{alive}/{len(hosts)} host processes still running; the target was re-spread over them{END}")
    await sim.stop()
    print(f"\n{B}{CYN}done{END} {YEL}(audit events: {len(sim.audit.events)}){END}")


if __name__ == "__main__":
    asyncio.run(main())
