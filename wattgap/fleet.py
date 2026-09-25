"""The supervisor: coordinates independent battery devices over a transport.

It never trusts that a unit is alive. It only counts units whose signed, physically plausible
telemetry arrived last tick. Commitments are per zone, since ERCOT settles by load zone, and each
carries failure headroom. Lost megawatts are re-spread over healthy units in the same zone. If a
zone still can't cover its commitment, the supervisor raises an ALARM and re-commits that zone
lower instead of pretending. Supervisor state is numpy arrays (see fleetmath.py).
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

import numpy as np

from . import fleetmath as fm
from .audit import AuditLog
from .data import INTERVAL_H, ZONES, Interval
from .desk import Desk
from .econ import POLICIES, SPEC, Battery, Context, reason
from .security import Registry, Rejected, Signed, public_hex, sign
from .transport import DeviceSpec, LocalTransport

COMMIT_FRACTION = 0.7  # commit 70% of healthy capacity per zone; the rest is failure headroom
BATCH_TICKS = 4  # an approved earn batch covers one hour of 15-minute intervals
REPLY_IDLE_TIMEOUT_S = 0.25  # stop waiting once no reply has arrived for this long
ENROLL_TIMEOUT_S = 20.0
FEED_STALE_S = 600.0  # a price feed whose own timestamp is older than this means HOLD everything


@dataclass
class TickReport:
    tick: int
    interval: str
    target_mw: float
    delivered_mw: float
    charging_mw: float
    home_mw: float  # household use behind the meters of units that reported
    export_mw: float  # delivered minus what those homes used themselves
    healthy: int
    total: int
    alarm: str
    degraded: list[str]
    batch: str | None
    zone_actions: dict[str, str]
    zone_target_mw: dict[str, float]
    zone_delivered_mw: dict[str, float]


class Fleet:
    def __init__(self, clock, audit: AuditLog, desk: Desk, key, size: int = 400, seed: int = 7,
                 transport=None, reply_timeout: float = REPLY_IDLE_TIMEOUT_S):
        self.clock, self.audit, self.desk, self.key = clock, audit, desk, key
        self.reply_timeout = reply_timeout
        self.ids = [f"core-{n:05d}" for n in range(size)]
        self.index = {u: i for i, u in enumerate(self.ids)}
        self.zone = np.arange(size) % len(ZONES)
        rng = np.random.default_rng(seed)
        self.soc = rng.uniform(0.45, 0.95, size).round(3)
        self.home_scale = rng.uniform(0.7, 1.3, size).round(2)
        self.reserve = np.full(size, SPEC.reserve_soc)
        self.misses = np.zeros(size, dtype=np.int64)
        self.state = np.full(size, fm.HEALTHY, dtype=np.int8)
        self.commanded = np.zeros(size)  # kW sent last tick: + discharge, - charge
        self.registry = Registry(set(self.ids))
        self.transport = transport or LocalTransport(clock)
        self.protected_homes: set[str] = set()
        self.history: list[TickReport] = []
        self.stale_feed_ticks = 0
        self.feed_at: float | None = None  # the price feed's own timestamp (epoch s), when a live feed is wired in
        self.warnings: dict = {}  # zone -> latest warn.Signal (Signals app), if wired in
        self.partition_ticks = 0
        self.tick_no = 0

    async def start(self) -> None:
        specs = [DeviceSpec(u, ZONES[self.zone[i]], float(self.soc[i]), float(self.home_scale[i]))
                 for i, u in enumerate(self.ids)]
        await self.transport.start(specs, public_hex(self.key))
        loop = asyncio.get_running_loop()
        deadline = loop.time() + ENROLL_TIMEOUT_S
        while len(self.registry.keys) < len(self.ids) and loop.time() < deadline:
            try:
                hello = await asyncio.wait_for(self.transport.to_supervisor.get(), deadline - loop.time())
                self.registry.enroll(hello, self.clock.now())
            except Rejected as e:
                self.audit.write(self.clock.now(), "registry", "enroll_rejected", unit=hello.device_id, why=str(e))
            except TimeoutError:
                break
        missing = [u for u in self.ids if u not in self.registry.keys]
        self.state[[self.index[u] for u in missing]] = fm.DEAD
        self.audit.write(self.clock.now(), "registry", "fleet_enrolled", units=len(self.registry.keys),
                         missing=len(missing))

    async def stop(self) -> None:
        await self.transport.stop()

    def zone_ids(self, zone: str) -> list[str]:
        zi = ZONES.index(zone)
        return [u for u, z in zip(self.ids, self.zone, strict=True) if z == zi]

    # ------------------------------------------------------------ chaos
    def kill_zone(self, zone: str, fraction: float = 0.3) -> list[str]:
        """Really stop `fraction` of a zone's running units (tasks cancelled or processes SIGKILLed)."""
        alive = [u for u in self.zone_ids(zone) if self.transport.alive(u)]
        groups = self.transport.kill_unit_of(alive)
        chosen = random.Random(self.tick_no).sample(groups, round(len(groups) * fraction))
        victims = self.transport.kill([u for g in chosen for u in g])
        self.audit.write(self.clock.now(), "chaos", "kill_zone", zone=zone, killed=len(victims), of=len(alive))
        return victims

    def partition(self, zone: str, ticks: int = 3) -> int:
        ids = set(self.zone_ids(zone))
        self.transport.partitioned |= ids
        self.partition_ticks = ticks
        self.audit.write(self.clock.now(), "chaos", "partition", zone=zone, units=len(ids), ticks=ticks)
        return len(ids)

    def stale_feed(self, ticks: int = 2) -> None:
        self.stale_feed_ticks = ticks
        self.audit.write(self.clock.now(), "chaos", "stale_feed", ticks=ticks)

    def make_rogue(self, zone: str = "LZ_NORTH") -> str:
        """A healthy in-process device starts reporting a fake SoC."""
        uid = next(u for u in self.zone_ids(zone) if self.state[self.index[u]] == fm.HEALTHY)
        self.transport.devices[uid].rogue = True
        self.audit.write(self.clock.now(), "chaos", "rogue_unit", unit=uid)
        return uid

    def revoke(self, uid: str, why: str = "operator revoked key") -> None:
        self.registry.revoke(uid, why)
        self.state[self.index[uid]] = fm.REVOKED
        self.audit.write(self.clock.now(), "registry", "key_revoked", unit=uid, why=why)

    def protect(self, on: bool) -> None:
        """Storm mode for the whole fleet: cancel earning and lock every reserve at its current charge."""
        self.desk.protect(on)
        self.reserve = np.maximum(SPEC.reserve_soc, self.soc) if on else np.full(len(self.ids), SPEC.reserve_soc)
        if not on:
            for u in self.protected_homes:
                self.reserve[self.index[u]] = max(SPEC.reserve_soc, self.soc[self.index[u]])

    def protect_home(self, uid: str, on: bool) -> None:
        """One member's Protect: that home stops earning and its reserve locks at its current charge.
        The device enforces the floor itself, because the reserve travels inside every signed command."""
        i = self.index[uid]
        self.reserve[i] = max(SPEC.reserve_soc, self.soc[i]) if on else SPEC.reserve_soc
        (self.protected_homes.add if on else self.protected_homes.discard)(uid)
        self.audit.write(self.clock.now(), "member", "protect_home_on" if on else "protect_home_off", unit=uid,
                         reserve=round(float(self.reserve[i]), 3))

    # ------------------------------------------------------------ one tick
    def _zone_actions(self, iv: Interval, trailing, trailing_sys) -> dict[str, str]:
        ctx = {z: Context(iv, z, trailing[z][-96:], trailing_sys[-96:], Battery(0.5)) for z in ZONES}
        return {z: POLICIES["wattgap"](c)[0] for z, c in ctx.items()}

    def _plan_earn(self, iv, trailing, trailing_sys, earn_zones, healthy) -> None:
        # commit what healthy units can sustain for the whole batch window, minus failure headroom
        sustain = np.where(healthy, fm.usable_kw(self.soc, self.reserve, hours=BATCH_TICKS * INTERVAL_H), 0.0)
        cap = fm.zone_sums(sustain, self.zone, len(ZONES))
        zone_mw = {z: float(COMMIT_FRACTION * cap[ZONES.index(z)] / 1000) for z in earn_zones
                   if cap[ZONES.index(z)] > 0}
        if sum(zone_mw.values()) * 1000 < SPEC.power_kw:  # skip batches smaller than one battery
            return
        parts = (reason(Context(iv, z, trailing[z][-96:], trailing_sys[-96:], Battery(0.5))) for z in zone_mw)
        why = "; ".join(dict.fromkeys(p for r in parts for p in r.split("; ")))
        warned = [f"early warning {z}: {self.warnings[z].why}" for z in zone_mw
                  if z in self.warnings and self.warnings[z].action == "DISCHARGE-NOW"]
        why = "; ".join([*warned, why])
        self.desk.submit("earn", sum(zone_mw.values()), BATCH_TICKS, why, tuple(zone_mw), zone_mw)

    async def tick(self, iv: Interval, trailing: dict[str, list[float]], trailing_sys: list[float]) -> TickReport:
        self.tick_no += 1
        now = self.clock.now()
        degraded, alarms = [], []
        zone_actions = self._zone_actions(iv, trailing, trailing_sys)
        for z, sig in self.warnings.items():  # early warning: an input to the plan, never a dispatch
            if sig.action == "DISCHARGE-NOW" and z in zone_actions:
                zone_actions[z] = "DISCHARGE"  # proposes an earn batch; the desk's approval rules still apply
            elif sig.action == "PRE-CHARGE" and zone_actions.get(z) == "HOLD":
                zone_actions[z] = "CHARGE"
        feed_age = None if self.feed_at is None else now - self.feed_at
        stale = self.stale_feed_ticks > 0 or (feed_age is not None and feed_age > FEED_STALE_S)
        if stale:
            self.stale_feed_ticks = max(0, self.stale_feed_ticks - 1)
            zone_actions = dict.fromkeys(ZONES, "HOLD")
            degraded.append(f"stale price feed ({feed_age:.0f} s old): HOLD all" if feed_age and feed_age > FEED_STALE_S
                            else "stale price feed: HOLD all")
        if not self.desk.alive:
            degraded.append("desk offline: new earn batches wait and expire (fail closed)")

        healthy = self.state == fm.HEALTHY
        headroom = np.where(healthy, fm.usable_kw(self.soc, self.reserve), 0.0)
        earn_zones = [z for z, a in zone_actions.items() if a == "DISCHARGE"]
        if earn_zones and not self.desk.open("earn"):
            self._plan_earn(iv, trailing, trailing_sys, earn_zones, healthy)

        kw = np.zeros(len(self.ids))
        target = np.zeros(len(ZONES))
        live = None if stale else self.desk.live("earn")
        if live:  # an approved batch is a commitment: deliver each zone's MW for the whole window
            for z, mw in live.zone_mw.items():
                target[ZONES.index(z)] = mw * 1000
            kw, short = fm.allocate(target, headroom, self.zone)
            for zi in np.flatnonzero(short > 1e-6):
                z = ZONES[zi]
                alarms.append(f"{z} short by {short[zi] / 1000:.3f} MW")
                self.audit.write(now, "supervisor", "commitment_broken", batch=live.id, zone=z,
                                 committed_mw=round(float(target[zi]) / 1000, 3), short_mw=round(float(short[zi]) / 1000, 3))
                can = float(COMMIT_FRACTION * (target[zi] - short[zi]) / 1000)  # restore headroom on what's left
                self.desk.recommit(live, z, can, f"healthy capacity short by {short[zi] / 1000:.3f} MW")
            if alarms:
                degraded.append("zone capacity short: every healthy unit there at its limit; zone re-committed lower")
            self.desk.tick_done(live)
        charge_zones = [ZONES.index(z) for z, a in zone_actions.items() if a == "CHARGE"]
        if charge_zones:
            charge = self.desk.live("charge") or self.desk.submit(
                "charge", 0.0, BATCH_TICKS, f"cheap power in {', '.join(ZONES[i] for i in charge_zones)}",
                tuple(ZONES[i] for i in charge_zones))
            charging = healthy & np.isin(self.zone, charge_zones) & (kw == 0)
            kw[charging] = -fm.room_kw(self.soc[charging])
            self.desk.tick_done(charge)

        replies = await self._exchange(iv, kw, now)
        delivered_z, report = self._absorb(replies, now)

        if self.partition_ticks > 0:
            self.partition_ticks -= 1
            if self.partition_ticks == 0:
                self.transport.partitioned.clear()
                self.audit.write(now, "chaos", "partition_healed")

        target_kw = float(target.sum())
        if target_kw and float(report["delivered"]) + 1e-6 < target_kw and not alarms:
            alarms.append(f"delivered {report['delivered'] / 1000:.3f} of {target_kw / 1000:.3f} MW "
                          "(units went silent or failed checks)")
        rep = TickReport(
            self.tick_no, iv.start.isoformat(), target_kw / 1000, *(float(report[k]) / 1000 for k in (
                "delivered", "charging", "home", "export")),
            int((self.state == fm.HEALTHY).sum()), len(self.ids),
            ("ALARM: " + "; ".join(alarms)) if alarms else "", degraded, live.id if live else None, zone_actions,
            {z: round(float(target[i]) / 1000, 3) for i, z in enumerate(ZONES) if target[i]},
            {z: round(float(delivered_z[i]) / 1000, 3) for i, z in enumerate(ZONES)})
        self.history.append(rep)
        self.audit.write(now, "supervisor", "dispatch", tick=rep.tick, interval=rep.interval,
                         target_mw=round(rep.target_mw, 3), delivered_mw=round(rep.delivered_mw, 3),
                         charging_mw=round(rep.charging_mw, 3), export_mw=round(rep.export_mw, 3),
                         healthy=rep.healthy, total=rep.total, batch=rep.batch, alarm=rep.alarm,
                         degraded=degraded, zones=zone_actions, zone_target_mw=rep.zone_target_mw)
        return rep

    async def _exchange(self, iv: Interval, kw: np.ndarray, now: float) -> list[Signed]:
        """Sign one command per reachable unit, then gather replies until all answer or the wire idles."""
        self.pinged = np.isin(self.state, (fm.HEALTHY, fm.SUSPECT, fm.DEAD))
        self.commanded = np.where(self.pinged, kw, 0.0)
        start = iv.start.isoformat()
        for i in np.flatnonzero(self.pinged):
            k = float(kw[i])
            action = "DISCHARGE" if k > 0 else "CHARGE" if k < 0 else "HOLD"
            body = {"tick": self.tick_no, "action": action, "kw": abs(k), "reserve": float(self.reserve[i]),
                    "interval": start}
            self.transport.send(self.ids[i], sign(self.key, self.ids[i], body, now))
        got: list[Signed] = []
        answered: set[str] = set()
        expected = int(self.pinged.sum())
        while len(answered) < expected:
            try:
                msg = await asyncio.wait_for(self.transport.to_supervisor.get(), self.reply_timeout)
            except TimeoutError:
                break
            got.append(msg)
            if "rejected" not in msg.body:
                answered.add(msg.device_id)
        return got

    def _absorb(self, replies: list[Signed], now: float) -> tuple[np.ndarray, dict]:
        """Verify replies, then run heartbeat and SoC-physics checks on the whole fleet at once."""
        n = len(self.ids)
        replied = np.zeros(n, dtype=bool)
        rep_soc, rep_kw, home = np.zeros(n), np.zeros(n), np.zeros(n)
        for msg in replies:
            try:
                body = self.registry.verify(msg, now)
            except Rejected as e:
                self.audit.write(now, "supervisor", "telemetry_rejected", unit=msg.device_id, why=str(e))
                continue
            if "rejected" in body:  # a device refusing a command it couldn't verify
                self.audit.write(now, msg.device_id, "command_rejected", why=body["rejected"])
                continue
            i = self.index[msg.device_id]
            if body.get("tick") != self.tick_no or not self.pinged[i]:
                continue
            replied[i], rep_soc[i], rep_kw[i], home[i] = True, body["soc"], body["kw"], body["home_kw"]

        bad = replied & fm.implausible(rep_soc, self.soc, rep_kw)
        before = self.state.copy()
        new = fm.heartbeat(self.state, self.misses, self.pinged, replied & ~bad)
        new[bad] = fm.QUARANTINED
        for i in np.flatnonzero(new != before):
            u, z = self.ids[i], ZONES[self.zone[i]]
            if new[i] == fm.QUARANTINED:
                self.audit.write(now, "guard", "unit_quarantined", unit=u, zone=z, reported_soc=round(rep_soc[i], 3),
                                 physics_soc=round(float(fm.expected_soc(self.soc[i:i + 1], rep_kw[i:i + 1])[0]), 3))
            elif new[i] == fm.HEALTHY:
                self.audit.write(now, "supervisor", "unit_recovered", unit=u, zone=z)
            else:
                self.audit.write(now, "supervisor", f"unit_{fm.STATE_NAMES[new[i]]}", unit=u, zone=z,
                                 misses=int(self.misses[i]))
        self.state = new
        ok = replied & ~bad
        self.soc[ok] = rep_soc[ok]
        out = np.where(ok, np.maximum(rep_kw, 0.0), 0.0)
        return fm.zone_sums(out, self.zone, len(ZONES)), {
            "delivered": out.sum(),
            "charging": np.where(ok, np.maximum(-rep_kw, 0.0), 0.0).sum(),
            "home": home[ok].sum(),
            "export": np.where(ok, np.maximum(rep_kw - home, 0.0), 0.0).sum(),
        }

    def home_view(self, uid: str) -> dict:
        i = self.index[uid]
        act = "DISCHARGE" if self.commanded[i] > 0 else "CHARGE" if self.commanded[i] < 0 else "HOLD"
        return {"id": uid, "zone": ZONES[self.zone[i]], "state": fm.STATE_NAMES[self.state[i]],
                "soc": round(float(self.soc[i]), 3), "reserve": round(float(self.reserve[i]), 3),
                "action": act, "kw": round(float(self.commanded[i]), 2), "protected": uid in self.protected_homes}

    def view(self) -> dict:
        counts: dict[str, dict[str, int]] = {z: {} for z in ZONES}
        for zi, st in zip(self.zone, self.state, strict=True):
            name = fm.STATE_NAMES[st]
            counts[ZONES[zi]][name] = counts[ZONES[zi]].get(name, 0) + 1
        act = np.where(self.commanded > 0, "DISCHARGE", np.where(self.commanded < 0, "CHARGE", "HOLD"))
        return {
            "units": [{"id": u, "zone": ZONES[self.zone[i]], "state": fm.STATE_NAMES[self.state[i]],
                       "soc": round(float(self.soc[i]), 3), "action": str(act[i])} for i, u in enumerate(self.ids)],
            "by_zone": counts,
            "protected": self.desk.protected,
        }
