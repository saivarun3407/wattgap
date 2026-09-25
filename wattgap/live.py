"""A running fleet replaying one real ERCOT day: shared by the demo script and the web UI."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from .audit import AuditLog
from .data import SCENARIOS, ZONES, day
from .desk import Clock, Desk, VirtualClock
from .fleet import Fleet, TickReport
from .security import new_key, sign, supervisor_key

SECONDS_PER_TICK = 15.0  # desk/crypto time that passes per replayed 15-minute interval


class Sim:
    def __init__(self, d: date = SCENARIOS["spike"], start: str = "12:00", size: int = 400,
                 clock: Clock | None = None, audit_path: Path | None = None, key=None,
                 reply_timeout: float | None = None, desk_ttl_s: float = 90.0, desk_timeout_s: float = 20.0,
                 transport=None):
        self.clock = clock or VirtualClock()
        self.audit = AuditLog(audit_path)
        self.desk = Desk(self.clock, self.audit, ttl_s=desk_ttl_s, heartbeat_timeout_s=desk_timeout_s)
        self.fleet = Fleet(self.clock, self.audit, self.desk, key or supervisor_key(), size=size,
                           transport=transport)
        if reply_timeout is not None:
            self.fleet.reply_timeout = reply_timeout
        self.day = d
        self.intervals = day(d - timedelta(days=1)) + day(d)
        self.first = 96 + next(i for i, iv in enumerate(day(d)) if iv.start.strftime("%H:%M") >= start)
        self.cursor = self.first
        self.desk_alive = True

    async def start(self) -> None:
        await self.fleet.start()

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
        f = self.fleet
        return next(u for u in f.zone_ids(zone) if f.state[f.index[u]] == 0 and u in f.transport.last_sent)

    def forge_command(self, zone: str = "LZ_SOUTH") -> str:
        """Put a discharge command signed with an attacker's key on a healthy unit's wire."""
        uid = self._healthy_in(zone)
        body = {"tick": self.fleet.tick_no, "action": "DISCHARGE", "kw": 20.0, "reserve": 0.0,
                "interval": self.interval.start.isoformat()}
        self.fleet.transport.inject(uid, sign(new_key(), uid, body, self.clock.now()))
        self.audit.write(self.clock.now(), "chaos", "forged_command", unit=uid)
        return uid

    def replay_command(self, zone: str = "LZ_WEST") -> str:
        """Re-send a command a unit already executed (captured off the wire)."""
        uid = self._healthy_in(zone)
        self.fleet.transport.inject(uid, self.fleet.transport.last_sent[uid])
        self.audit.write(self.clock.now(), "chaos", "replayed_command", unit=uid)
        return uid

    def redirect_command(self, zone: str = "LZ_HOUSTON") -> tuple[str, str]:
        """Deliver one unit's genuine, supervisor-signed command to a different unit."""
        a, b = self.fleet.zone_ids(zone)[:2]
        self.fleet.transport.inject(b, self.fleet.transport.last_sent[a])
        self.audit.write(self.clock.now(), "chaos", "redirected_command", unit=b, from_unit=a)
        return a, b

    def view(self) -> dict:
        iv = self.interval
        return {
            "day": self.day.isoformat(),
            "interval": iv.start.isoformat(),
            "prices": iv.prices,
            "desk_alive": self.desk.alive,
            "desk_ttl_s": self.desk.ttl_s,
            "desk": self.desk.view(),
            "fleet": self.fleet.view(),
            "last": self.fleet.history[-1].__dict__ if self.fleet.history else None,
            "history": [{"t": h.interval[11:16], "target": round(h.target_mw, 3),
                         "delivered": round(h.delivered_mw, 3), "export": round(h.export_mw, 3),
                         "alarm": bool(h.alarm)}
                        for h in self.fleet.history[-40:]],
            "audit": self.audit.events[-60:],
        }
