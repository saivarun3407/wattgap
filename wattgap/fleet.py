"""Independent battery workers (asyncio tasks) coordinated by a supervisor.

The supervisor never trusts that a unit is alive: it only counts units whose signed,
physically plausible heartbeat arrived last tick. Lost megawatts are re-spread over the
healthy units within their power and reserve limits; if that can't cover the target it
raises an ALARM and runs degraded instead of pretending.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field

from .audit import AuditLog
from .data import INTERVAL_H, ZONES, Interval
from .desk import Desk
from .econ import SPEC, Battery, Context, aware, reason
from .security import Rejected, Signed, Verifier, device_key, sign

COMMIT_FRACTION = 0.7  # commit 70% of healthy capacity; the rest is failure headroom
BATCH_TICKS = 4  # an approved earn batch covers one hour of 15-minute intervals
DEAD_AFTER_MISSES = 2
SOC_TOLERANCE = 0.02  # reported SoC may drift this far from physics before quarantine
REPLY_IDLE_TIMEOUT_S = 0.25  # stop waiting once no reply has arrived for this long


@dataclass
class Unit:
    id: str
    zone: str
    battery: Battery
    key: bytes
    verifier: Verifier
    rogue: bool = False  # reports a fake SoC (chaos)
    rejected: int = 0


@dataclass
class Record:
    """What the supervisor believes about one unit."""

    zone: str
    soc: float
    verifier: Verifier
    reserve: float = SPEC.reserve_soc
    misses: int = 0
    state: str = "healthy"  # healthy | suspect | dead | quarantined
    commanded: tuple[str, float] = ("HOLD", 0.0)


class Network:
    """Delivers messages; partitioned units lose everything in both directions."""

    def __init__(self, audit: AuditLog, clock):
        self.audit, self.clock = audit, clock
        self.partitioned: set[str] = set()
        self.last_sent: dict[str, Signed] = {}
        self.to_supervisor: asyncio.Queue[Signed] = asyncio.Queue()
        self.inboxes: dict[str, asyncio.Queue] = {}

    def send(self, unit_id: str, msg) -> None:
        if unit_id not in self.partitioned:
            self.last_sent[unit_id] = msg
            self.inboxes[unit_id].put_nowait(msg)

    def reply(self, msg: Signed) -> None:
        if msg.device_id not in self.partitioned:
            self.to_supervisor.put_nowait(msg)


async def unit_worker(u: Unit, net: Network, clock) -> None:
    inbox = net.inboxes[u.id]
    while True:
        msg = await inbox.get()
        try:
            cmd = u.verifier.verify(msg, clock.now())
        except Rejected as e:
            u.rejected += 1
            net.audit.write(clock.now(), u.id, "command_rejected", why=str(e))
            continue
        u.battery.reserve_soc = cmd["reserve"]  # the unit enforces the member reserve itself
        kw = 0.0
        if cmd["action"] == "DISCHARGE":
            kw = u.battery.discharge(cmd["kw"], INTERVAL_H) / INTERVAL_H
        elif cmd["action"] == "CHARGE":
            kw = -u.battery.charge(cmd["kw"], INTERVAL_H) / INTERVAL_H
        soc = 1.0 if u.rogue else u.battery.soc
        net.reply(sign(u.key, u.id, {"tick": cmd["tick"], "soc": soc, "kw": kw}, clock.now()))


@dataclass
class TickReport:
    tick: int
    interval: str
    target_mw: float
    delivered_mw: float
    charging_mw: float
    healthy: int
    total: int
    alarm: str
    degraded: list[str]
    batch: str | None
    zone_actions: dict[str, str]


@dataclass
class Fleet:
    clock: object
    audit: AuditLog
    desk: Desk
    secret: bytes
    size: int = 400
    seed: int = 7
    units: dict[str, Unit] = field(default_factory=dict)
    records: dict[str, Record] = field(default_factory=dict)
    tasks: dict[str, asyncio.Task] = field(default_factory=dict)
    history: list[TickReport] = field(default_factory=list)
    stale_feed_ticks: int = 0
    partition_ticks: int = 0
    tick_no: int = 0
    reply_timeout: float = REPLY_IDLE_TIMEOUT_S

    def start(self) -> None:
        self.net = Network(self.audit, self.clock)
        rng = random.Random(self.seed)
        for n in range(self.size):
            uid = f"core-{n:05d}"
            zone = ZONES[n % len(ZONES)]
            soc = round(rng.uniform(0.45, 0.95), 3)
            key = device_key(self.secret, uid)
            self.units[uid] = Unit(uid, zone, Battery(soc), key, Verifier(key))
            self.records[uid] = Record(zone, soc, Verifier(key))
            self.net.inboxes[uid] = asyncio.Queue()
            self.tasks[uid] = asyncio.create_task(unit_worker(self.units[uid], self.net, self.clock))

    async def stop(self) -> None:
        for t in self.tasks.values():
            t.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)

    # ------------------------------------------------------------ chaos
    def kill_zone(self, zone: str, fraction: float = 0.3) -> list[str]:
        alive = [u for u in self.units if self.units[u].zone == zone and not self.tasks[u].done()]
        victims = random.Random(self.tick_no).sample(alive, round(len(alive) * fraction))
        for uid in victims:
            self.tasks[uid].cancel()
        self.audit.write(self.clock.now(), "chaos", "kill_zone", zone=zone, killed=len(victims),
                         of=len(alive))
        return victims

    def partition(self, zone: str, ticks: int = 3) -> int:
        ids = {u for u in self.units if self.units[u].zone == zone}
        self.net.partitioned |= ids
        self.partition_ticks = ticks
        self.audit.write(self.clock.now(), "chaos", "partition", zone=zone, units=len(ids), ticks=ticks)
        return len(ids)

    def stale_feed(self, ticks: int = 2) -> None:
        self.stale_feed_ticks = ticks
        self.audit.write(self.clock.now(), "chaos", "stale_feed", ticks=ticks)

    def make_rogue(self, zone: str = "LZ_NORTH") -> str:
        uid = next(u for u, r in self.records.items() if r.state == "healthy" and r.zone == zone)
        self.units[uid].rogue = True
        self.audit.write(self.clock.now(), "chaos", "rogue_unit", unit=uid)
        return uid

    def protect(self, on: bool) -> None:
        """Lock every home's reserve at its current charge (or release the lock)."""
        self.desk.protect(on)
        for r in self.records.values():
            r.reserve = max(SPEC.reserve_soc, r.soc) if on else SPEC.reserve_soc

    # ------------------------------------------------------------ one tick
    def _usable_kw(self, r: Record) -> float:
        return Battery(r.soc, reserve_soc=r.reserve).max_discharge_kw(INTERVAL_H)

    def _allocate(self, ids: list[str], target_kw: float) -> tuple[dict[str, float], float]:
        """Spread target over units in proportion to headroom. Returns (plan, shortfall_kw)."""
        avail = {u: self._usable_kw(self.records[u]) for u in ids}
        total = sum(avail.values())
        if total <= 0:
            return {}, target_kw
        share = min(1.0, target_kw / total)
        return {u: a * share for u, a in avail.items() if a > 0}, max(0.0, target_kw - total)

    async def tick(self, iv: Interval, trailing: dict[str, list[float]],
                   trailing_sys: list[float]) -> TickReport:
        self.tick_no += 1
        now = self.clock.now()
        healthy = [u for u, r in self.records.items() if r.state == "healthy"]
        degraded, alarm = [], ""

        zone_actions = {}
        for z in ZONES:
            ctx = Context(iv, z, trailing[z][-96:], trailing_sys[-96:], Battery(0.5))
            zone_actions[z] = aware(ctx)[0]
        stale = self.stale_feed_ticks > 0
        if stale:
            self.stale_feed_ticks -= 1
            zone_actions = dict.fromkeys(ZONES, "HOLD")
            degraded.append("stale price feed: HOLD all")

        if not self.desk.alive:
            degraded.append("desk offline: new earn batches wait and expire (fail closed)")
        plan: dict[str, tuple[str, float]] = {}
        target_kw, batch = 0.0, None
        earn_zones = tuple(z for z, a in zone_actions.items() if a == "DISCHARGE")
        if earn_zones and not self.desk.open("earn"):
            ids = [u for u in healthy if self.records[u].zone in earn_zones]
            capacity_kw = sum(self._usable_kw(self.records[u]) for u in ids)
            if capacity_kw >= SPEC.power_kw:  # skip batches smaller than one battery
                parts = (reason(Context(iv, z, trailing[z][-96:], trailing_sys[-96:], Battery(0.5)))
                         for z in earn_zones)
                why = "; ".join(dict.fromkeys(p for r in parts for p in r.split("; ")))
                self.desk.submit("earn", COMMIT_FRACTION * capacity_kw / 1000, BATCH_TICKS, why, earn_zones)
        live = None if stale else self.desk.live("earn")
        if live:
            # an approved batch is a commitment: deliver its MW for its whole window
            batch = live.id
            target_kw = live.target_mw * 1000
            ids = [u for u in healthy if self.records[u].zone in live.zones]
            alloc, short_kw = self._allocate(ids, target_kw)
            plan.update({u: ("DISCHARGE", kw) for u, kw in alloc.items()})
            if short_kw > 1e-6:
                alarm = f"ALARM: healthy capacity short by {short_kw / 1000:.3f} MW"
                degraded.append("capacity short: running every healthy unit at its limit")
            self.desk.tick_done(live)
        charge_zones = [z for z, a in zone_actions.items() if a == "CHARGE"]
        if charge_zones:
            charge = self.desk.live("charge") or self.desk.submit(
                "charge", 0.0, BATCH_TICKS, f"cheap power in {', '.join(charge_zones)}", tuple(charge_zones))
            for u in healthy:
                if self.records[u].zone in charge_zones and u not in plan:
                    plan[u] = ("CHARGE", SPEC.power_kw)
            self.desk.tick_done(charge)

        # suspects get no work but are still pinged so they can prove they're back
        pinged = [u for u, r in self.records.items() if r.state in ("healthy", "suspect", "dead")]
        for u in pinged:
            action, kw = plan.get(u, ("HOLD", 0.0))
            r = self.records[u]
            r.commanded = (action, kw)
            body = {"tick": self.tick_no, "action": action, "kw": kw, "reserve": r.reserve}
            self.net.send(u, sign(self.units[u].key, u, body, now))

        replies = await self._collect(expected=len(pinged))
        delivered_kw = charging_kw = 0.0
        for u in pinged:
            r = self.records[u]
            msg = replies.get(u)
            if msg is None:
                r.misses += 1
                new = "dead" if r.misses >= DEAD_AFTER_MISSES else "suspect"
                if new != r.state:
                    self.audit.write(now, "supervisor", f"unit_{new}", unit=u, zone=r.zone, misses=r.misses)
                r.state = new
                continue
            try:
                t = r.verifier.verify(msg, now)
            except Rejected as e:
                self.audit.write(now, "supervisor", "telemetry_rejected", unit=u, why=str(e))
                continue
            expected = self._expected_soc(r, t["kw"])
            if abs(t["soc"] - expected) > SOC_TOLERANCE:
                r.state = "quarantined"
                self.audit.write(now, "guard", "unit_quarantined", unit=u, zone=r.zone,
                                 reported_soc=round(t["soc"], 3), physics_soc=round(expected, 3))
                continue
            if r.state != "healthy":
                self.audit.write(now, "supervisor", "unit_recovered", unit=u, zone=r.zone)
            r.state, r.misses, r.soc = "healthy", 0, t["soc"]
            if t["kw"] > 0:
                delivered_kw += t["kw"]
            else:
                charging_kw -= t["kw"]

        if self.partition_ticks > 0:
            self.partition_ticks -= 1
            if self.partition_ticks == 0:
                self.net.partitioned.clear()
                self.audit.write(now, "chaos", "partition_healed")

        if target_kw and delivered_kw + 1e-6 < target_kw and not alarm:
            alarm = f"ALARM: delivered {delivered_kw / 1000:.3f} of {target_kw / 1000:.3f} MW (units went silent)"
        rep = TickReport(
            self.tick_no, iv.start.isoformat(), target_kw / 1000, delivered_kw / 1000, charging_kw / 1000,
            sum(r.state == "healthy" for r in self.records.values()), len(self.records),
            alarm, degraded, batch, zone_actions)
        self.history.append(rep)
        self.audit.write(now, "supervisor", "dispatch", tick=rep.tick, interval=rep.interval,
                         target_mw=round(rep.target_mw, 3), delivered_mw=round(rep.delivered_mw, 3),
                         charging_mw=round(rep.charging_mw, 3), healthy=rep.healthy, total=rep.total,
                         batch=batch, alarm=alarm, degraded=degraded, zones=zone_actions)
        return rep

    def _expected_soc(self, r: Record, kw: float) -> float:
        cap, eff = SPEC.capacity_kwh, SPEC.leg_eff
        kwh = kw * INTERVAL_H
        return r.soc - kwh / eff / cap if kwh > 0 else r.soc - kwh * eff / cap

    async def _collect(self, expected: int) -> dict[str, Signed]:
        """Gather replies until everyone answered or the wire has been idle for reply_timeout."""
        got: dict[str, Signed] = {}
        while len(got) < expected:
            try:
                msg = await asyncio.wait_for(self.net.to_supervisor.get(), self.reply_timeout)
            except TimeoutError:
                break
            got[msg.device_id] = msg
        return got

    def view(self) -> dict:
        counts: dict[str, dict[str, int]] = {z: {} for z in ZONES}
        for r in self.records.values():
            counts[r.zone][r.state] = counts[r.zone].get(r.state, 0) + 1
        return {
            "units": [{"id": u, "zone": r.zone, "state": r.state, "soc": round(r.soc, 3),
                       "action": r.commanded[0]} for u, r in self.records.items()],
            "by_zone": counts,
            "protected": self.desk.protected,
        }
