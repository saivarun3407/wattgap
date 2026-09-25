"""The scripted WattGap story, end to end, on the real 2023-09-06 ERCOT scarcity evening.

Run:  python3 -m wattgap.demo      (or: make demo)
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from . import report
from .export import build_pack, write
from .fleet import TickReport
from .live import Sim

OUT = Path(__file__).resolve().parents[1] / "out"
B, DIM, RED, GRN, YEL, CYN, END = "\033[1m", "\033[2m", "\033[31m", "\033[32m", "\033[33m", "\033[36m", "\033[0m"


def say(title: str) -> None:
    print(f"\n{B}{CYN}▶ {title}{END}")


def show(rep: TickReport, sim: Sim) -> None:
    hh = rep.interval[11:16]
    prices = " ".join(f"{z[3:6]} ${p:,.0f}" for z, p in sim.intervals[sim.cursor - 1].prices.items())
    line = (f"  {hh} CT  {DIM}{prices}{END}  target {rep.target_mw:5.2f} MW  delivered {rep.delivered_mw:5.2f} MW"
            f"  (export {rep.export_mw:4.2f})  charging {rep.charging_mw:4.2f} MW  healthy {rep.healthy}/{rep.total}")
    if rep.batch:
        line += f"  batch {rep.batch}"
    print(line)
    if rep.alarm:
        print(f"    {RED}{B}{rep.alarm}{END}")
    for d in rep.degraded:
        print(f"    {YEL}degraded: {d}{END}")


def pending(sim: Sim) -> list:
    return [b for b in sim.desk.batches.values() if b.status == "pending"]


async def approve_next(sim: Sim, max_steps: int = 12) -> None:
    """Step until the planner asks the desk for something, then approve it as the operator."""
    for _ in range(max_steps):
        if pending(sim):
            break
        show(await sim.step(), sim)
    for b in pending(sim):
        print(f"  {YEL}PENDING {b.id}: {b.target_mw:.2f} MW in {', '.join(b.zones)} — {b.reason}{END}")
        sim.desk.approve(b.id, "operator")
        print(f"  {GRN}operator APPROVED {b.id}; signed commands fan out{END}")


async def run_until(sim: Sim, hhmm: str) -> None:
    while sim.interval.start.strftime("%H:%M") < hhmm:
        show(await sim.step(), sim)


async def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    econ = report.build()

    say("1. Economics on real ERCOT prices (fair baseline = overnight charge + even 5-9 PM discharge)")
    report.main()

    sim = Sim(start="14:15", size=400, audit_path=OUT / "audit.jsonl")
    await sim.start()
    say(f"2. Replay {sim.day} with {len(sim.fleet.ids)} battery devices, each an independent asyncio task "
        f"holding its own ed25519 key ({len(sim.fleet.registry.keys)} enrolled)")
    await run_until(sim, "14:45")

    say("3. Real-time price jumps past the day-ahead plan: an earn batch above the auto-apply cap waits for the desk")
    await approve_next(sim)
    show(await sim.step(), sim)

    say("4. Chaos: kill 30% of LZ_SOUTH, the zone this batch is committed in, mid-dispatch")
    victims = sim.fleet.kill_zone("LZ_SOUTH", 0.3)
    print(f"  {RED}killed {len(victims)} South units{END}")
    show(await sim.step(), sim)
    show(await sim.step(), sim)

    say("5. Chaos: a rogue unit fakes its SoC; forged, replayed and redirected commands hit the wire")
    rogue = sim.fleet.make_rogue()
    forged = sim.forge_command()
    replayed = sim.replay_command()
    _, redirected = sim.redirect_command()
    show(await sim.step(), sim)
    for e in sim.audit.of_kind("command_rejected"):
        print(f"  {RED}REJECTED{END} by {e['actor']}: {e['why']}")
    for e in sim.audit.of_kind("unit_quarantined"):
        print(f"  {RED}QUARANTINED{END} {e['unit']}: reported SoC {e['reported_soc']:.0%}, physics says {e['physics_soc']:.0%}")
    sim.fleet.revoke(rogue, "quarantined for spoofed SoC")
    print(f"  {YEL}operator REVOKED {rogue}'s key; its telemetry is refused from now on{END}")
    print(f"  {DIM}(forged → {forged}, replayed → {replayed}, redirected → {redirected}){END}")

    say("6. Chaos: partition all of LZ_WEST during a live batch: its zone commitment breaks and is re-committed")
    await approve_next(sim)
    show(await sim.step(), sim)
    sim.fleet.partition("LZ_WEST", ticks=2)
    for _ in range(3):
        show(await sim.step(), sim)
    for e in sim.audit.of_kind("commitment_recommitted"):
        print(f"  {YEL}RE-COMMIT {e['batch']} {e['zone']}: {e['from_mw']:.3f} → {e['to_mw']:.3f} MW ({e['why']}){END}")
    sim.fleet.stale_feed(ticks=1)
    show(await sim.step(), sim)

    say("7. The desk dies: pending batches must expire, and nothing may discharge")
    sim.kill_desk()
    await run_until(sim, "18:45")
    for e in sim.audit.of_kind("batch_expired"):
        print(f"  {GRN}{e['batch']} expired ({e['why']}){END}")
    print(f"  {GRN}ticks that discharged without a live batch: "
          f"{sum(1 for h in sim.fleet.history if h.delivered_mw > 0 and not h.batch)}{END}")

    say("8. Desk back; operator approves; then the member presses Protect")
    sim.revive_desk()
    await approve_next(sim)
    show(await sim.step(), sim)
    sim.fleet.protect(True)
    e = sim.audit.of_kind("protect_on")[-1]
    print(f"  {YEL}PROTECT: cancelled {e['cancelled']}; every reserve locked at its current charge{END}")
    show(await sim.step(), sim)
    show(await sim.step(), sim)
    await sim.stop()

    say("9. Evidence pack")
    jpath, hpath = write(build_pack(sim.audit, econ), OUT)
    s = build_pack(sim.audit)["summary"]
    for k in SUMMARY_KEYS:
        print(f"  {k:<30} {s[k]}")
    print(f"  wrote {jpath.relative_to(OUT.parent)}, {hpath.relative_to(OUT.parent)}, out/audit.jsonl "
          f"({len(sim.audit.events)} lines)")


SUMMARY_KEYS = ("decisions_count", "approvals_count", "expirations_count", "alarms_count", "recommits_count",
                "quarantines_count", "revocations_count", "security_count", "discharge_without_live_batch",
                "mwh_delivered", "mwh_exported")


if __name__ == "__main__":
    asyncio.run(main())
