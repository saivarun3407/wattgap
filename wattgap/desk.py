"""Human-in-the-loop dispatch desk. Fails closed: nothing risky runs without a live approval."""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field

from .audit import AuditLog


class Clock:
    def now(self) -> float:
        return time.time()


class VirtualClock(Clock):
    def __init__(self, start: float = 1_000_000.0):
        self.t = start

    def now(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


PENDING, AUTO, APPROVED, REJECTED, EXPIRED, CANCELLED, DONE = (
    "pending", "auto", "approved", "rejected", "expired", "cancelled", "done")
LIVE = (AUTO, APPROVED)


@dataclass
class Batch:
    id: str
    kind: str  # "earn" (discharge for money) | "charge"
    target_mw: float
    ticks: int  # how many dispatch ticks the batch covers once live
    created: float
    expires: float  # a pending batch dies at this time
    reason: str
    zones: tuple[str, ...] = ()
    zone_mw: dict[str, float] = field(default_factory=dict)  # per-zone commitment (earn batches)
    status: str = PENDING
    ticks_run: int = 0
    decided_by: str = ""

    def view(self, now: float) -> dict:
        return {
            "id": self.id, "kind": self.kind, "target_mw": round(self.target_mw, 3), "zones": self.zones,
            "zone_mw": {z: round(mw, 3) for z, mw in self.zone_mw.items()},
            "status": self.status, "reason": self.reason, "ticks": self.ticks,
            "ticks_run": self.ticks_run, "decided_by": self.decided_by,
            "ttl_left_s": max(0.0, round(self.expires - now, 1)) if self.status == PENDING else None,
        }


class Desk:
    def __init__(self, clock: Clock, audit: AuditLog, *, auto_cap_mw: float = 0.25,
                 ttl_s: float = 90.0, heartbeat_timeout_s: float = 20.0):
        self.clock, self.audit = clock, audit
        self.auto_cap_mw = auto_cap_mw
        self.ttl_s = ttl_s
        self.heartbeat_timeout_s = heartbeat_timeout_s
        self.batches: dict[str, Batch] = {}
        self.protected = False
        self.last_beat = clock.now()
        self._ids = itertools.count(1)

    # -- liveness
    def heartbeat(self) -> None:
        self.last_beat = self.clock.now()

    @property
    def alive(self) -> bool:
        return self.clock.now() - self.last_beat <= self.heartbeat_timeout_s

    # -- lifecycle
    def submit(self, kind: str, target_mw: float, ticks: int, reason: str,
               zones: tuple[str, ...] = (), zone_mw: dict[str, float] | None = None) -> Batch:
        now = self.clock.now()
        b = Batch(f"B{next(self._ids):03d}", kind, target_mw, ticks, now, now + self.ttl_s, reason, zones,
                  dict(zone_mw or {}))
        if kind == "earn" and self.protected:
            b.status, b.decided_by = REJECTED, "protect"
        elif kind == "charge" or (target_mw <= self.auto_cap_mw and self.alive):
            b.status, b.decided_by = AUTO, "auto-cap" if kind == "earn" else "auto-charge"
        self.batches[b.id] = b
        self.audit.write(now, "planner", "batch_submitted", batch=b.id, batch_kind=kind,
                         target_mw=round(target_mw, 3), zones=list(zones), status=b.status, reason=reason)
        return b

    def approve(self, batch_id: str, who: str = "operator") -> bool:
        return self._decide(batch_id, APPROVED, who)

    def reject(self, batch_id: str, who: str = "operator") -> bool:
        return self._decide(batch_id, REJECTED, who)

    def _decide(self, batch_id: str, status: str, who: str) -> bool:
        self.sweep()  # an approval can never revive an expired batch
        b = self.batches.get(batch_id)
        if not b or b.status != PENDING or (status == APPROVED and self.protected and b.kind == "earn"):
            return False
        b.status, b.decided_by = status, who
        self.audit.write(self.clock.now(), who, f"batch_{status}", batch=b.id, target_mw=round(b.target_mw, 3))
        return True

    def protect(self, on: bool, who: str = "member") -> None:
        """Member guarantee: cancel all earning and lock the backup reserve."""
        self.protected = on
        cancelled = []
        if on:
            for b in self.batches.values():
                if b.kind == "earn" and b.status in (PENDING, *LIVE):
                    b.status, b.decided_by = CANCELLED, who
                    cancelled.append(b.id)
        self.audit.write(self.clock.now(), who, "protect_on" if on else "protect_off", cancelled=cancelled)

    def sweep(self) -> None:
        """Expire pending batches past TTL, or all of them if the desk has gone silent."""
        now = self.clock.now()
        dead = not self.alive
        for b in self.batches.values():
            if b.status == PENDING and (dead or now >= b.expires):
                b.status, b.decided_by = EXPIRED, "desk-dead" if dead else "ttl"
                self.audit.write(now, "desk", "batch_expired", batch=b.id, why=b.decided_by)

    def live(self, kind: str) -> Batch | None:
        """The batch of `kind` allowed to execute right now, if any."""
        self.sweep()
        for b in self.batches.values():
            if b.kind == kind and b.status in LIVE and not (kind == "earn" and self.protected):
                return b
        return None

    def open(self, kind: str) -> Batch | None:
        """A batch of `kind` that is pending or live (so the planner doesn't pile up duplicates)."""
        self.sweep()
        return next((b for b in self.batches.values()
                     if b.kind == kind and b.status in (PENDING, *LIVE)), None)

    def recommit(self, b: Batch, zone: str, mw: float, why: str) -> None:
        """Lower one zone's commitment on a live batch after it broke. Lowering only ever
        reduces discharge, so it needs no new approval; raising would."""
        old = b.zone_mw.get(zone, 0.0)
        mw = min(mw, old)
        b.zone_mw[zone] = mw
        b.target_mw = sum(b.zone_mw.values())
        self.audit.write(self.clock.now(), "supervisor", "commitment_recommitted", batch=b.id, zone=zone,
                         from_mw=round(old, 3), to_mw=round(mw, 3), why=why)

    def tick_done(self, b: Batch) -> None:
        b.ticks_run += 1
        if b.ticks_run >= b.ticks:
            b.status = DONE
            self.audit.write(self.clock.now(), "desk", "batch_done", batch=b.id)

    def view(self) -> list[dict]:
        now = self.clock.now()
        return [b.view(now) for b in sorted(self.batches.values(), key=lambda b: b.created, reverse=True)]
