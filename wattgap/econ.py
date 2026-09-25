"""Battery physics, dispatch policies and fair backtest economics on real ERCOT prices.

All money is in dollars, energy in kWh, prices in $/MWh. Times are America/Chicago.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from math import sqrt
from statistics import median
from typing import Callable

from .data import INTERVAL_H, ZONES, Interval, day


@dataclass(frozen=True)
class Spec:
    """Assumed home battery. Stated assumptions, not Base Core specifications."""

    capacity_kwh: float = 40.0
    power_kw: float = 20.0
    round_trip_eff: float = 0.90
    degradation_per_kwh: float = 0.02  # $ per kWh discharged (cycle wear)
    reserve_soc: float = 0.20  # member backup reserve: never discharged below this
    max_soc: float = 1.0

    @property
    def leg_eff(self) -> float:
        """Charge and discharge each lose sqrt(RTE), so a full cycle loses RTE."""
        return sqrt(self.round_trip_eff)


SPEC = Spec()


@dataclass
class Battery:
    soc: float
    spec: Spec = SPEC
    reserve_soc: float | None = None  # per-home override (e.g. Protect raises it)

    @property
    def floor(self) -> float:
        return max(self.spec.reserve_soc, self.reserve_soc or 0.0)

    @property
    def stored_kwh(self) -> float:
        return self.soc * self.spec.capacity_kwh

    def max_discharge_kw(self, hours: float) -> float:
        """Grid-side kW this battery can deliver for `hours` without touching its reserve."""
        usable = max(0.0, (self.soc - self.floor) * self.spec.capacity_kwh)
        return min(self.spec.power_kw, usable * self.spec.leg_eff / hours)

    def max_charge_kw(self, hours: float) -> float:
        room = max(0.0, (self.spec.max_soc - self.soc) * self.spec.capacity_kwh)
        return min(self.spec.power_kw, room / self.spec.leg_eff / hours)

    def charge(self, kw: float, hours: float) -> float:
        """Draw up to `kw` from the grid. Returns grid kWh drawn."""
        grid = min(kw, self.max_charge_kw(hours)) * hours
        self.soc += grid * self.spec.leg_eff / self.spec.capacity_kwh
        return grid

    def discharge(self, kw: float, hours: float) -> float:
        """Deliver up to `kw` to the grid. Returns grid kWh delivered."""
        grid = min(kw, self.max_discharge_kw(hours)) * hours
        self.soc -= grid / self.spec.leg_eff / self.spec.capacity_kwh
        return grid


# ---------------------------------------------------------------- policies


@dataclass(frozen=True)
class Context:
    interval: Interval
    zone: str
    trailing: list[float]  # this zone's prices over the previous 24 h (96 intervals)
    trailing_system: list[float]
    battery: Battery

    @property
    def price(self) -> float:
        return self.interval.prices[self.zone]

    @property
    def hour(self) -> float:
        t = self.interval.start
        return t.hour + t.minute / 60


Decision = tuple[str, float]  # (CHARGE | DISCHARGE | HOLD, kW)
Policy = Callable[[Context], Decision]
HOLD: Decision = ("HOLD", 0.0)


def percentile(xs: list[float], p: float) -> float:
    ys = sorted(xs)
    k = (len(ys) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(ys) - 1)
    return ys[lo] + (ys[hi] - ys[lo]) * (k - lo)


def naive_overnight(ctx: Context) -> Decision:
    """Reference only: charge 23:00-07:00 CT, never discharge. Not a fair baseline."""
    if ctx.hour >= 23 or ctx.hour < 7:
        return ("CHARGE", ctx.battery.spec.power_kw)
    return HOLD


CHARGE_WINDOW = (0.0, 6.0)  # CT hours
PEAK_WINDOW = (17.0, 21.0)


def scheduled(ctx: Context) -> Decision:
    """Fair baseline: charge overnight, spread discharge evenly over the 5-9 PM CT peak."""
    b = ctx.battery
    if CHARGE_WINDOW[0] <= ctx.hour < CHARGE_WINDOW[1]:
        return ("CHARGE", b.spec.power_kw)
    if PEAK_WINDOW[0] <= ctx.hour < PEAK_WINDOW[1]:
        hours_left = PEAK_WINDOW[1] - ctx.hour
        usable_grid_kwh = b.max_discharge_kw(hours_left) * hours_left
        return ("DISCHARGE", usable_grid_kwh / hours_left)
    return HOLD


CHARGE_PCT = 25  # charge when price is in the cheapest quarter of the trailing 24 h
DISCHARGE_PCT = 90  # discharge only in the top tenth


def breakeven(ctx: Context) -> float:
    """Lowest $/MWh at which selling beats the cost of having bought and worn the energy."""
    spec = ctx.battery.spec
    cheap = percentile(ctx.trailing, CHARGE_PCT)
    return max(cheap, 0.0) / spec.round_trip_eff + spec.degradation_per_kwh * 1000


def aware(ctx: Context) -> Decision:
    """WattGap: causal, uses only the trailing 24 h of this zone's real prices."""
    b = ctx.battery
    if ctx.price <= percentile(ctx.trailing, CHARGE_PCT):
        return ("CHARGE", b.spec.power_kw)
    if ctx.price >= max(percentile(ctx.trailing, DISCHARGE_PCT), breakeven(ctx)):
        return ("DISCHARGE", b.spec.power_kw)
    return HOLD


POLICIES: dict[str, Policy] = {
    "naive_overnight": naive_overnight,
    "scheduled": scheduled,
    "wattgap": aware,
}


def reason(ctx: Context) -> str:
    """Explain a decision by separating system-wide conditions from zone-specific ones."""
    sys_now = ctx.interval.system_price
    premium = ctx.price - sys_now
    parts = []
    if sys_now >= percentile(ctx.trailing_system, DISCHARGE_PCT):
        parts.append(f"system-wide: all-zone avg ${sys_now:,.0f}/MWh is in its top 10% of 24 h")
    elif sys_now <= percentile(ctx.trailing_system, CHARGE_PCT):
        parts.append(f"system-wide: all-zone avg ${sys_now:,.0f}/MWh is in its cheapest 25% of 24 h")
    if abs(premium) >= max(20.0, 0.10 * abs(sys_now)):
        word = "premium" if premium > 0 else "discount"
        parts.append(f"{ctx.zone} {word} ${abs(premium):,.0f}/MWh vs system avg (zone congestion)")
    if not parts:
        parts.append(f"{ctx.zone} ${ctx.price:,.0f}/MWh vs its own 24 h range")
    return "; ".join(parts)


# ---------------------------------------------------------------- backtest


@dataclass
class Step:
    start: str
    action: str
    grid_kwh: float  # + delivered to grid, - drawn from grid
    price: float
    cash: float
    wear: float
    soc: float
    reason: str


@dataclass
class Result:
    policy: str
    zone: str
    start_soc: float
    steps: list[Step] = field(default_factory=list)
    terminal_value: float = 0.0

    @property
    def energy_cash(self) -> float:
        return sum(s.cash for s in self.steps)

    @property
    def wear(self) -> float:
        return sum(s.wear for s in self.steps)

    @property
    def net(self) -> float:
        return self.energy_cash - self.wear + self.terminal_value

    @property
    def min_soc(self) -> float:
        return min([self.start_soc] + [s.soc for s in self.steps])

    @property
    def kwh_discharged(self) -> float:
        return sum(s.grid_kwh for s in self.steps if s.grid_kwh > 0)

    @property
    def kwh_charged(self) -> float:
        return -sum(s.grid_kwh for s in self.steps if s.grid_kwh < 0)


def trailing_prices(d: date, zone: str | None) -> list[float]:
    prior = day(d - timedelta(days=1))
    if zone is None:
        return [i.system_price for i in prior]
    return [i.prices[zone] for i in prior]


def simulate(policy_name: str, zone: str, days: list[date], start_soc: float = 0.5,
             spec: Spec = SPEC) -> Result:
    """Replay consecutive days. Leftover energy is valued at the last day's median price."""
    policy = POLICIES[policy_name]
    b = Battery(start_soc, spec)
    window = trailing_prices(days[0], zone)
    window_sys = trailing_prices(days[0], None)
    res = Result(policy_name, zone, start_soc)
    for d in days:
        for iv in day(d):
            ctx = Context(iv, zone, window[-96:], window_sys[-96:], b)
            action, kw = policy(ctx)
            grid = 0.0
            if action == "CHARGE":
                grid = -b.charge(kw, INTERVAL_H)
            elif action == "DISCHARGE":
                grid = b.discharge(kw, INTERVAL_H)
            if abs(grid) < 1e-9:
                action, grid = "HOLD", 0.0
            price = ctx.price
            res.steps.append(Step(
                iv.start.isoformat(), action, grid, price,
                cash=grid * price / 1000,
                wear=max(grid, 0.0) * spec.degradation_per_kwh,
                soc=b.soc,
                reason=reason(ctx) if action != "HOLD" else "",
            ))
            window.append(price)
            window_sys.append(iv.system_price)
    last_median = median(i.prices[zone] for i in day(days[-1]))
    delta_kwh = (b.soc - start_soc) * spec.capacity_kwh
    res.terminal_value = delta_kwh * spec.leg_eff * last_median / 1000
    return res


@dataclass
class DayReport:
    day: date
    by_zone: dict[str, dict[str, Result]]  # zone -> policy -> result

    def net(self, policy: str) -> float:
        """Average net $ per home across the four zones (one home per zone)."""
        return sum(r[policy].net for r in self.by_zone.values()) / len(self.by_zone)

    @property
    def gap_vs_fair(self) -> float:
        return self.net("wattgap") - self.net("scheduled")


def compare_day(d: date) -> DayReport:
    return DayReport(d, {z: {p: simulate(p, z, [d]) for p in POLICIES} for z in ZONES})


def zone_spread(d: date, scarcity: float = 1000.0) -> dict:
    """How far each zone sat from the all-zone average while the system was in scarcity."""
    ivs = [i for i in day(d) if i.system_price >= scarcity]
    if not ivs:
        return {"intervals": 0}
    out = {"intervals": len(ivs), "first": ivs[0].start.isoformat(), "last": ivs[-1].start.isoformat()}
    for z in ZONES:
        diffs = [i.prices[z] - i.system_price for i in ivs]
        out[z] = {"avg_vs_system": sum(diffs) / len(diffs), "worst": min(diffs)}
    return out
