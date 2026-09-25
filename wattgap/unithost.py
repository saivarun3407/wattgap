"""A process hosting a few battery devices; each opens its own TCP connection to the supervisor.

Started by TcpTransport:  python -m wattgap.unithost <port> <supervisor_pubkey_hex> <device specs json>
Each device generates its ed25519 key here, in this process, and sends only the public half.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time

from .device import Device
from .econ import Battery
from .security import Signed, Verifier


async def run_device(d: Device, port: int) -> None:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(d.hello(time.time()).to_json().encode() + b"\n")
    while line := await reader.readline():
        writer.write(d.handle(Signed.from_json(line), time.time()).to_json().encode() + b"\n")


async def main(port: int, supervisor_pub: str, specs: list[dict]) -> None:
    devices = [Device(s["id"], s["zone"], Battery(s["soc"]), Verifier.for_hex(supervisor_pub), s["home_scale"])
               for s in specs]
    await asyncio.gather(*(run_device(d, port) for d in devices), return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]), sys.argv[2], json.loads(sys.argv[3])))
