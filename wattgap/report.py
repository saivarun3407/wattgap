"""Economics summary on the real ERCOT days: fair-baseline gap, zone finding, member statement.

Run:  python3 -m wattgap.report
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from functools import lru_cache

from . import econ
from .data import INTERVAL_H, EVALUATION, dam_day, SCENARIOS, SELECTION, ZONES, days_between

MONTH = EVALUATION
COMPARED = ("scheduled", "trailing", "wattgap")


def day_summary(d: date) -> dict:
    r = econ.compare_day(d)
    return {
        "day": d.isoformat(),
        "per_home": {p: round(r.net(p), 2) for p in econ.POLICIES},
        "gap_vs_fair": round(r.gap_vs_fair, 2),
        "by_zone": {
            z: {p: {"net": round(x.net, 2), "min_soc": round(x.min_soc, 3),
                    "kwh_out": round(x.kwh_discharged, 1), "kwh_to_home": round(x.kwh_to_home, 1),
                    "kwh_exported": round(x.kwh_exported, 1), "wear": round(x.wear, 2),
                    "terminal": round(x.terminal_value, 2)}
                for p, x in res.items()}
            for z, res in r.by_zone.items()
        },
        "prices": [{"t": s.start[11:16], **{z: r.by_zone[z]["wattgap"].steps[i].price for z in ZONES}}
                   for i, s in enumerate(r.by_zone[ZONES[0]]["wattgap"].steps)],
        "dam": {z: [h[z] for h in dam_day(d)] for z in ZONES},
        "plan": {z: {"charge": sorted(pl.charge), "discharge": sorted(pl.discharge)}
                 for z in ZONES for pl in [econ.dam_plan(d, z, econ.PLANNER.window_h)]},
        "soc": {p: [round(s.soc, 3) for s in r.by_zone["LZ_HOUSTON"][p].steps] for p in COMPARED},
    }


def month_summary() -> dict:
    days = days_between(*MONTH)
    per_day = [econ.compare_day(d) for d in days]
    won = sum(r.gap_vs_fair > 0 for r in per_day)
    won_v1 = sum(r.net("trailing") > r.net("scheduled") for r in per_day)
    cont = {p: {z: econ.simulate(p, z, days) for z in ZONES} for p in COMPARED}
    per_home = {p: sum(x.net for x in v.values()) / len(ZONES) for p, v in cont.items()}
    best = max(per_day, key=lambda r: r.gap_vs_fair)
    worst = min(per_day, key=lambda r: r.gap_vs_fair)
    return {
        "first": MONTH[0].isoformat(), "last": MONTH[1].isoformat(), "days": len(days),
        "per_home": {p: round(v, 2) for p, v in per_home.items()},
        "gap_vs_fair": round(per_home["wattgap"] - per_home["scheduled"], 2),
        "v1_gap_vs_fair": round(per_home["trailing"] - per_home["scheduled"], 2),
        "days_won": won,
        "v1_days_won": won_v1,
        "best_day": {"day": best.day.isoformat(), "gap": round(best.gap_vs_fair, 2)},
        "worst_day": {"day": worst.day.isoformat(), "gap": round(worst.gap_vs_fair, 2)},
        "min_soc": round(min(x.min_soc for v in cont.values() for x in v.values()), 3),
    }


def _events(steps: list[econ.Step]) -> list[dict]:
    """Group consecutive discharge intervals into member-readable events (end = interval end)."""
    events, cur = [], None
    for s in steps:
        if s.action == "DISCHARGE":
            if cur is None:
                cur = {"start": s.start, "end": s.start, "kwh": 0.0, "value": 0.0,
                       "peak_price": 0.0, "reason": s.reason}
            end = datetime.fromisoformat(s.start) + timedelta(minutes=15)
            cur["end"], cur["kwh"] = end.isoformat(), cur["kwh"] + s.grid_kwh
            cur["value"] += s.cash
            cur["peak_price"] = max(cur["peak_price"], s.price)
        elif cur:
            events.append(cur)
            cur = None
    if cur:
        events.append(cur)
    return events


def member_statement(zone: str = "LZ_HOUSTON") -> dict:
    """What one home's battery did in September 2023 under WattGap, from real prices."""
    days = days_between(*MONTH)
    res = econ.simulate("wattgap", zone, days)
    fair = econ.simulate("scheduled", zone, days)
    events = _events(res.steps)
    spike = econ.simulate("wattgap", zone, [SCENARIOS["spike"]])
    top = max(events, key=lambda e: e["value"])
    home_kw = sum(s.home_kwh for s in res.steps) / len(res.steps) / INTERVAL_H
    reserve_kwh = econ.SPEC.reserve_soc * econ.SPEC.capacity_kwh * econ.SPEC.leg_eff
    return {
        "zone": zone,
        "month": "September 2023",
        "kwh_to_home": round(res.kwh_to_home, 1),
        "kwh_exported": round(res.kwh_exported, 1),
        "home_kwh_month": round(sum(s.home_kwh for s in res.steps), 1),
        "avg_home_kw": round(home_kw, 2),
        "reserve_backup_hours": round(reserve_kwh / home_kw, 1),
        "net_value": round(res.net, 2),
        "fair_schedule_value": round(fair.net, 2),
        "energy_cash": round(res.energy_cash, 2),
        "wear": round(res.wear, 2),
        "kwh_out": round(res.kwh_discharged, 1),
        "kwh_in": round(res.kwh_charged, 1),
        "events": len(events),
        "min_soc": round(res.min_soc, 3),
        "reserve_soc": econ.SPEC.reserve_soc,
        "top_event": {**top, "kwh": round(top["kwh"], 1), "value": round(top["value"], 2)},
        "spike_day": {"day": SCENARIOS["spike"].isoformat(), "net": round(spike.net, 2),
                      "min_soc": round(spike.min_soc, 3),
                      "events": [{**e, "kwh": round(e["kwh"], 1), "value": round(e["value"], 2)}
                                 for e in _events(spike.steps)]},
    }


@lru_cache(maxsize=1)
def build() -> dict:
    spread = econ.zone_spread(SCENARIOS["spike"])
    return {
        "assumptions": {**asdict(econ.SPEC), "interval_minutes": 15,
                        "charge_pct": econ.CHARGE_PCT, "discharge_pct": econ.DISCHARGE_PCT,
                        "planner": asdict(econ.PLANNER), "refill_hours": econ.refill_hours(econ.SPEC),
                        "selection_days": f"{SELECTION[0]} to {SELECTION[1]}",
                        "evaluation_days": f"{EVALUATION[0]} to {EVALUATION[1]}",
                        "home_load": "ERCOT backcasted RESHIWR profile (COAST/NCENT/SCENT/WEST weather zones)",
                        "fair_schedule": f"charge {econ.CHARGE_WINDOW[0]:02.0f}:00-{econ.CHARGE_WINDOW[1]:02.0f}:00 CT, "
                                         f"discharge evenly {econ.PEAK_WINDOW[0]:.0f}:00-{econ.PEAK_WINDOW[1]:.0f}:00 CT"},
        "labels": econ.LABELS,
        "days": {name: day_summary(d) for name, d in SCENARIOS.items()},
        "month": month_summary(),
        "zone_finding": spread,
        "members": {z: member_statement(z) for z in ZONES},
        "generated": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def main() -> None:
    rep = build()
    print("WattGap economics on real ERCOT real-time 15-min load-zone prices\n")
    print(f"{'day':<24}{'naive':>9}{'fair sched':>12}{'v1 trailing':>13}{'WattGap DA':>12}{'gap vs fair':>13}"
          "   ($/home, avg of 4 zones)")
    for name, d in rep["days"].items():
        p = d["per_home"]
        print(f"{name + ' ' + d['day']:<24}{p['naive_overnight']:>9.2f}{p['scheduled']:>12.2f}"
              f"{p['trailing']:>13.2f}{p['wattgap']:>12.2f}{d['gap_vs_fair']:>+13.2f}")
    m = rep["month"]
    p = m["per_home"]
    print(f"{'Sep 2023 (30 days)':<24}{'':>9}{p['scheduled']:>12.2f}{p['trailing']:>13.2f}{p['wattgap']:>12.2f}"
          f"{m['gap_vs_fair']:>+13.2f}   won {m['days_won']}/{m['days']} days (v1 {m['v1_days_won']}), "
          f"lowest SoC {m['min_soc']:.0%}")
    a = rep["assumptions"]
    print(f"  day-ahead planner: discharge in the top {a['planner']['window_h']} DAM hour(s), charge in the cheapest "
          f"{a['refill_hours']}, sell early if real time >= {a['planner']['spike_mult']}x the day's top DAM price; "
          f"chosen on {a['selection_days']} only")
    z = rep["zone_finding"]
    print(f"\nZone finding, {rep['days']['spike']['day']}: during {z['intervals']} scarcity intervals "
          f"(all-zone avg >= $1,000/MWh, {z['first'][11:16]}-{z['last'][11:16]} CT)")
    for zone in ZONES:
        print(f"  {zone:<11} avg {z[zone]['avg_vs_system']:+8.0f} $/MWh vs system, worst {z[zone]['worst']:+8.0f}")
    print("\nFull JSON: python3 -m wattgap.report --json")


if __name__ == "__main__":
    import sys
    if "--json" in sys.argv:
        print(json.dumps(build(), indent=2, default=str))
    else:
        main()
