"""A running fleet replaying one real ERCOT day: shared by the demo script and the web UI."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path

from .audit import AuditLog
from .data import SCENARIOS, ZONES, day
from .desk import Clock, Desk, VirtualClock
from .fleet import Fleet, TickReport
from .security import device_key, fleet_secret, sign

SECONDS_PER_TICK = 15.0  # desk/crypto time that passes per replayed 15-minute interval


class Sim:
    def __init__(self, d: date = SCENARIOS["spike"], start: str = "12:00", size: int = 400,
                 clock: Clock | None = None, audit_path: Path | None = None, secret: bytes | None = None,
                 reply_timeout: float | None = None, desk_ttl_s: float = 90.0, desk_timeout_s: float = 20.0):
        self.clock = clock or VirtualClock()
        self.audit = AuditLog(audit_path)
        self.desk = Desk(self.clock, self.audit, ttl_s=desk_ttl_s, heartbeat_timeout_s=desk_timeout_s)
        self.fleet = Fleet(self.clock, self.audit, self.desk, secret or fleet_secret(), size=size)
        if reply_timeout is not None:
            self.fleet.reply_timeout = reply_timeout
        self.day = d
        self.intervals = day(d - timedelta(days=1)) + day(d)
        self.first = 96 + next(i for i, iv in enumerate(day(d)) if iv.start.strftime("%H:%M") >= start)
        self.cursor = self.first
        self.desk_alive = True

    async def start(self) -> None:
        self.fleet.start()
        await asyncio.sleep(0)

    async def stop(self) -> None:
        await self.fleet.stop()

    @property
    def interval(self):
        return self.intervals[self.cursor]

    async def step(self) -> TickReport:
        if self.desk_alive:
            self.desk.heartbeat()
        window = self.intervals[self.cursor - 96:self.cursor]
        trailing = {z: [i.prices[z] for i in window] for z in ZONES}
        trailing_sys = [i.system_price for i in window]
        rep = await self.fleet.tick(self.interval, trailing, trailing_sys)
        self.cursor = self.cursor + 1 if self.cursor + 1 < len(self.intervals) else self.first
        if isinstance(self.clock, VirtualClock):
            self.clock.advance(SECONDS_PER_TICK)
        return rep

    # -- operator / chaos controls
    def kill_desk(self) -> None:
        self.desk_alive = False
        self.audit.write(self.clock.now(), "chaos", "desk_killed")

    def revive_desk(self) -> None:
        self.desk_alive = True
        self.desk.heartbeat()
        self.audit.write(self.clock.now(), "operator", "desk_revived")

    def _healthy_in(self, zone: str) -> str:
        return next(u for u, r in self.fleet.records.items() if r.state == "healthy" and r.zone == zone)

    def forge_command(self, zone: str = "LZ_SOUTH") -> str:
        """Put a discharge command signed with the wrong key on a healthy unit's wire."""
        uid = self._healthy_in(zone)
        bad_key = device_key(b"attacker-guess", uid)
        body = {"tick": self.fleet.tick_no, "action": "DISCHARGE", "kw": 20.0, "reserve": 0.0}
        self.fleet.net.inboxes[uid].put_nowait(sign(bad_key, uid, body, self.clock.now()))
        self.audit.write(self.clock.now(), "chaos", "forged_command", unit=uid)
        return uid

    def replay_command(self, zone: str = "LZ_WEST") -> str:
        """Re-send a command a unit already executed (captured off the wire)."""
        uid = self._healthy_in(zone)
        self.fleet.net.inboxes[uid].put_nowait(self.fleet.net.last_sent[uid])
        self.audit.write(self.clock.now(), "chaos", "replayed_command", unit=uid)
        return uid

    def view(self) -> dict:
        iv = self.interval
        return {
            "day": self.day.isoformat(),
            "interval": iv.start.isoformat(),
            "prices": iv.prices,
            "desk_alive": self.desk.alive,
            "desk": self.desk.view(),
            "fleet": self.fleet.view(),
            "last": self.fleet.history[-1].__dict__ if self.fleet.history else None,
            "history": [{"t": h.interval[11:16], "target": round(h.target_mw, 3),
                         "delivered": round(h.delivered_mw, 3), "alarm": bool(h.alarm)}
                        for h in self.fleet.history[-40:]],
            "audit": self.audit.events[-60:],
        }
