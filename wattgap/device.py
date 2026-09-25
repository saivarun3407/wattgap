"""One home battery's controller: holds its own ed25519 key, obeys only verified commands,
enforces the member reserve itself, and reports signed telemetry (including home use)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .data import INTERVAL_H, home_kwh
from .econ import Battery
from .security import Rejected, Signed, Verifier, new_key, public_hex, sign


@dataclass
class Device:
    id: str
    zone: str
    battery: Battery
    supervisor: Verifier  # the supervisor's public key
    home_scale: float = 1.0  # this home's size relative to ERCOT's average-premise profile
    rogue: bool = False  # chaos: reports a fake SoC
    key: object = field(default_factory=new_key)  # generated on the device; never leaves it

    def hello(self, now: float) -> Signed:
        """Self-signed enrollment: proves possession of the private key behind `pubkey`."""
        return sign(self.key, self.id, {"pubkey": public_hex(self.key), "zone": self.zone}, now)

    def handle(self, msg: Signed, now: float) -> Signed:
        """Verify and apply one command. Refusals are reported as signed telemetry too."""
        try:
            if msg.device_id != self.id:
                raise Rejected("addressed to another device")
            cmd = self.supervisor.verify(msg, now)
        except Rejected as e:
            return sign(self.key, self.id, {"rejected": str(e)}, now)
        b = self.battery
        b.reserve_soc = cmd["reserve"]  # the unit enforces the member reserve itself
        kw = 0.0
        if cmd["action"] == "DISCHARGE":
            kw = b.discharge(cmd["kw"], INTERVAL_H) / INTERVAL_H
        elif cmd["action"] == "CHARGE":
            kw = -b.charge(cmd["kw"], INTERVAL_H) / INTERVAL_H
        home_kw = home_kwh(cmd["interval"], self.zone) * self.home_scale / INTERVAL_H
        soc = 1.0 if self.rogue else b.soc
        return sign(self.key, self.id, {"tick": cmd["tick"], "soc": soc, "kw": kw, "home_kw": home_kw}, now)
