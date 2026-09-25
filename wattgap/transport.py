"""The wire between the supervisor and the batteries.

* LocalTransport: every device is its own asyncio task in this process, and queues are the wire.
  Tests, the web UI and `make demo` use it (fast, deterministic).
* TcpTransport: devices run in separate OS processes (`python -m wattgap.unithost`). Each device
  opens its own localhost TCP connection and speaks newline-delimited signed JSON.
  Chaos kills are real SIGKILLs. `make demo-net` uses it.

Both give the supervisor the same surface: send(), inject(), kill(), a `partitioned` set,
and one queue of signed messages coming back from devices.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from dataclasses import dataclass

from .device import Device
from .econ import Battery
from .security import Signed, Verifier


@dataclass(frozen=True)
class DeviceSpec:
    id: str
    zone: str
    soc: float
    home_scale: float


class LocalTransport:
    def __init__(self, clock):
        self.clock = clock
        self.to_supervisor: asyncio.Queue[Signed] = asyncio.Queue()
        self.partitioned: set[str] = set()
        self.last_sent: dict[str, Signed] = {}
        self.devices: dict[str, Device] = {}
        self._inboxes: dict[str, asyncio.Queue] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    async def start(self, specs: list[DeviceSpec], supervisor_pub: str) -> None:
        for s in specs:
            d = Device(s.id, s.zone, Battery(s.soc), Verifier.for_hex(supervisor_pub), s.home_scale)
            self.devices[s.id] = d
            self._inboxes[s.id] = asyncio.Queue()
            self._tasks[s.id] = asyncio.create_task(self._worker(d))
            self.to_supervisor.put_nowait(d.hello(self.clock.now()))

    async def _worker(self, d: Device) -> None:
        inbox = self._inboxes[d.id]
        while True:
            reply = d.handle(await inbox.get(), self.clock.now())
            if d.id not in self.partitioned:
                self.to_supervisor.put_nowait(reply)

    def send(self, uid: str, msg: Signed) -> None:
        if uid not in self.partitioned:
            self.last_sent[uid] = msg
            self._inboxes[uid].put_nowait(msg)

    def inject(self, uid: str, msg: Signed) -> None:
        """An attacker on the wire: deliver a message the supervisor never sent."""
        self._inboxes[uid].put_nowait(msg)

    def kill(self, uids: list[str]) -> list[str]:
        for u in uids:
            self._tasks[u].cancel()
        return uids

    def alive(self, uid: str) -> bool:
        return not self._tasks[uid].done()

    def kill_unit_of(self, uids: list[str]) -> list[list[str]]:
        """Smallest groups that die together: one device per group in-process."""
        return [[u] for u in uids]

    async def stop(self) -> None:
        for t in self._tasks.values():
            t.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)


class TcpTransport:
    """Devices in `hosts` child processes, one TCP connection per device, on 127.0.0.1."""

    def __init__(self, clock, per_host: int = 10):
        self.clock = clock
        self.per_host = per_host
        self.to_supervisor: asyncio.Queue[Signed] = asyncio.Queue()
        self.partitioned: set[str] = set()
        self.last_sent: dict[str, Signed] = {}
        self._writers: dict[str, asyncio.StreamWriter] = {}
        self._procs: list[tuple[asyncio.subprocess.Process, list[str]]] = []
        self._server: asyncio.AbstractServer | None = None

    async def start(self, specs: list[DeviceSpec], supervisor_pub: str) -> None:
        self._server = await asyncio.start_server(self._conn, "127.0.0.1", 0)
        port = self._server.sockets[0].getsockname()[1]
        by_zone: dict[str, list[DeviceSpec]] = {}
        for s in specs:
            by_zone.setdefault(s.zone, []).append(s)
        for zone_specs in by_zone.values():  # a host process only carries units of one zone
            for i in range(0, len(zone_specs), self.per_host):
                chunk = zone_specs[i:i + self.per_host]
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "wattgap.unithost", str(port), supervisor_pub,
                    json.dumps([s.__dict__ for s in chunk]))
                self._procs.append((proc, [s.id for s in chunk]))

    async def _conn(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        uid = None
        try:
            while line := await reader.readline():
                msg = Signed.from_json(line)
                if uid is None:  # first line is the device's hello
                    uid = msg.device_id
                    self._writers[uid] = writer
                if uid not in self.partitioned:
                    self.to_supervisor.put_nowait(msg)
        finally:
            if uid and self._writers.get(uid) is writer:
                del self._writers[uid]

    def send(self, uid: str, msg: Signed) -> None:
        w = self._writers.get(uid)
        if w and uid not in self.partitioned:
            self.last_sent[uid] = msg
            w.write(msg.to_json().encode() + b"\n")

    def inject(self, uid: str, msg: Signed) -> None:
        w = self._writers.get(uid)
        if w:
            w.write(msg.to_json().encode() + b"\n")

    def alive(self, uid: str) -> bool:
        return uid in self._writers

    def hosts(self) -> list[tuple[int, list[str], bool]]:
        """(pid, device ids, running) for every host process."""
        return [(p.pid, ids, p.returncode is None) for p, ids in self._procs]

    def kill_unit_of(self, uids: list[str]) -> list[list[str]]:
        """Devices die with their host process, so the groups are whole hosts."""
        wanted = set(uids)
        return [ids for proc, ids in self._procs if proc.returncode is None and wanted & set(ids)]

    def kill(self, uids: list[str]) -> list[str]:
        """SIGKILL every host process carrying one of `uids`. Returns every device that died."""
        dead = []
        for proc, ids in self._procs:
            if proc.returncode is None and set(ids) & set(uids):
                os.kill(proc.pid, signal.SIGKILL)
                dead += ids
        return dead

    async def stop(self) -> None:
        """Close every connection so hosts exit on their own; SIGKILL any still running after 2 s."""
        for w in list(self._writers.values()):
            w.close()
        if self._server:
            self._server.close()
        waits = asyncio.gather(*(p.wait() for p, _ in self._procs))
        try:
            await asyncio.wait_for(waits, 2.0)
        except TimeoutError:
            for proc, _ in self._procs:
                if proc.returncode is None:
                    proc.kill()
            await asyncio.gather(*(p.wait() for p, _ in self._procs))
