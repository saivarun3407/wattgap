"""Multiprocess sharding for very large fleets.

Each shard process owns a contiguous slice of the fleet's arrays. A tick takes two round trips:
1. every shard reports its per-zone healthy headroom;
2. the coordinator turns zone targets into one share per zone, and each shard allocates, applies,
   checks physics and heartbeats for its own units, then reports per-zone delivery.
Only 4-number vectors cross process boundaries, so the coordinator's cost doesn't grow with fleet size.

MathShard simulates device physics inside the shard (vectorized, no crypto, no network).
SignedShard runs the full per-device ed25519 path in-process: sign, device verify and apply,
device sign, registry verify.
"""

from __future__ import annotations

import multiprocessing as mp

import numpy as np

from . import fleetmath as fm
from .data import SCENARIOS, ZONES, day
from .device import Device
from .econ import SPEC, Battery
from .security import Registry, Verifier, new_key, public_hex, sign

N_ZONES = len(ZONES)


def _math_shard(conn, n: int, offset: int, seed: int, drop_rate: float) -> None:
    rng = np.random.default_rng(seed)
    zone = (np.arange(n) + offset) % N_ZONES
    soc = rng.uniform(0.45, 0.95, n)
    truth = soc.copy()  # what the devices physically hold
    reserve = np.full(n, SPEC.reserve_soc)
    state = np.zeros(n, dtype=np.int8)
    misses = np.zeros(n, dtype=np.int64)
    conn.send("ready")
    while True:
        msg = conn.recv()
        if msg[0] == "stop":
            return
        healthy = state == fm.HEALTHY
        head = np.where(healthy, fm.usable_kw(soc, reserve), 0.0)
        if msg[0] == "headroom":
            conn.send(fm.zone_sums(head, zone, N_ZONES))
            continue
        _, target, charge_zones = msg
        kw, _ = fm.allocate(target, head, zone)
        charging = healthy & charge_zones[zone] & (kw == 0)
        kw[charging] = -fm.room_kw(soc[charging])
        truth = fm.expected_soc(truth, kw)  # devices apply the command
        pinged = state <= fm.DEAD
        replied = pinged & (rng.random(n) >= drop_rate)
        bad = replied & fm.implausible(truth, soc, kw)
        state = fm.heartbeat(state, misses, pinged, replied & ~bad)
        state[bad] = fm.QUARANTINED
        ok = replied & ~bad
        soc[ok] = truth[ok]
        conn.send((fm.zone_sums(np.where(ok, np.maximum(kw, 0.0), 0.0), zone, N_ZONES), int(ok.sum())))


def _signed_shard(conn, n: int, offset: int, seed: int, drop_rate: float) -> None:
    rng = np.random.default_rng(seed)
    sup = new_key()
    sup_pub = Verifier.for_hex(public_hex(sup)).public
    ids = [f"core-{offset + i:07d}" for i in range(n)]
    zones = [ZONES[(offset + i) % N_ZONES] for i in range(n)]
    socs = rng.uniform(0.45, 0.95, n)
    devices = [Device(u, z, Battery(float(s)), Verifier(sup_pub)) for u, z, s in zip(ids, zones, socs, strict=True)]
    reg = Registry(set(ids))
    for d in devices:
        reg.enroll(d.hello(0.0), 0.0)
    interval = day(SCENARIOS["spike"])[60].start.isoformat()
    conn.send("ready")
    tick = 0
    while True:
        msg = conn.recv()
        if msg[0] == "stop":
            return
        if msg[0] == "headroom":
            conn.send(np.zeros(N_ZONES))
            continue
        tick += 1
        now = float(tick)
        delivered = np.zeros(N_ZONES)
        ok = 0
        for d in devices:
            cmd = sign(sup, d.id, {"tick": tick, "action": "DISCHARGE", "kw": 1.0, "reserve": SPEC.reserve_soc,
                                   "interval": interval}, now)
            reply = d.handle(cmd, now)
            body = reg.verify(reply, now)
            if body.get("tick") == tick:
                ok += 1
                delivered[ZONES.index(d.zone)] += body["kw"]
        conn.send((delivered, ok))


class ShardPool:
    def __init__(self, units: int, shards: int, kind: str = "math", drop_rate: float = 0.001, seed: int = 7):
        target = {"math": _math_shard, "signed": _signed_shard}[kind]
        ctx = mp.get_context("fork")
        sizes = [units // shards + (i < units % shards) for i in range(shards)]
        offsets = np.cumsum([0, *sizes[:-1]])
        self.conns, self.procs = [], []
        for i, (n, off) in enumerate(zip(sizes, offsets, strict=True)):
            a, b = ctx.Pipe()
            p = ctx.Process(target=target, args=(b, n, int(off), seed + i, drop_rate), daemon=True)
            p.start()
            self.conns.append(a)
            self.procs.append(p)
        for c in self.conns:
            assert c.recv() == "ready"

    def tick(self, earn: np.ndarray, charge: np.ndarray, commit: float = 0.7) -> tuple[np.ndarray, int]:
        """earn/charge: per-zone booleans. Commits `commit` of each earning zone's healthy headroom."""
        for c in self.conns:
            c.send(("headroom",))
        headroom = sum(c.recv() for c in self.conns)
        target = np.where(earn, commit * headroom, 0.0)
        for c in self.conns:
            c.send(("apply", target, charge))
        results = [c.recv() for c in self.conns]
        return sum(r[0] for r in results), sum(r[1] for r in results)

    def close(self) -> None:
        for c in self.conns:
            c.send(("stop",))
        for p in self.procs:
            p.join(timeout=10)
