"""Independent battery workers + supervisor rebalance on failure."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


KW = 20.0
KWH = 40.0


@dataclass
class Unit:
    id: str
    zone: str
    soc: float
    online: bool = True
    kwh_moved: float = 0.0
    revenue: float = 0.0


@dataclass
class Fleet:
    units: list[Unit] = field(default_factory=list)

    def online_kw(self) -> float:
        return sum(KW for u in self.units if u.online)

    def kill_zone(self, zone: str, frac: float, rng: random.Random) -> int:
        candidates = [u for u in self.units if u.zone == zone and u.online]
        n = int(len(candidates) * frac)
        for u in rng.sample(candidates, n) if n else []:
            u.online = False
        return n


def apply_action(u: Unit, action: str, price_mwh: float, minutes: float = 5.0) -> None:
    if not u.online or action == "HOLD":
        return
    hours = minutes / 60.0
    kwh = KW * hours
    if action == "CHARGE":
        room = (1.0 - u.soc) * KWH
        kwh = min(kwh, room)
        u.soc += kwh / KWH
        u.kwh_moved += kwh
        u.revenue -= kwh * (price_mwh / 1000.0)  # $/kWh
    elif action == "DISCHARGE":
        have = u.soc * KWH
        kwh = min(kwh, max(0.0, have - 0.2 * KWH))
        u.soc -= kwh / KWH
        u.kwh_moved += kwh
        u.revenue += kwh * (price_mwh / 1000.0)
