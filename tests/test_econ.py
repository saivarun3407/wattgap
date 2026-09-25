from datetime import date, datetime

import pytest

from wattgap import econ
from wattgap.data import EVALUATION, SCENARIOS, SELECTION, ZONES, dam_day, day, days_between
from wattgap.econ import PLANNER, SPEC, Battery

MONTH = days_between(*EVALUATION)


@pytest.fixture(scope="module")
def month_runs():
    return {(p, z): econ.simulate(p, z, MONTH) for p in econ.POLICIES for z in ZONES}


def test_real_data_is_complete_and_central_time():
    for d in [*MONTH, date(2026, 9, 21)]:
        ivs = day(d)
        assert len(ivs) == 96, d
        assert all(i.start.utcoffset().total_seconds() == -5 * 3600 for i in ivs)  # CDT
    # the old bug read the UTC hour; 19:00 CT must be hour 19, not 00
    iv = next(i for i in day(SCENARIOS["spike"]) if i.start.hour == 19 and i.start.minute == 0)
    assert iv.start.isoformat() == "2023-09-06T19:00:00-05:00"


def test_reserve_never_violated(month_runs):
    for (p, z), res in month_runs.items():
        assert res.min_soc >= SPEC.reserve_soc - 1e-9, (p, z)


def test_no_discharge_below_floor():
    b = Battery(SPEC.reserve_soc)
    assert b.discharge(20, 0.25) == 0.0
    b = Battery(0.5, reserve_soc=0.5)  # Protect lock
    assert b.max_discharge_kw(0.25) == 0.0


def test_energy_conservation_with_efficiency():
    b = Battery(0.3)
    drawn = b.charge(20, 0.25)
    assert drawn == pytest.approx(5.0)
    assert (b.soc - 0.3) * SPEC.capacity_kwh == pytest.approx(drawn * SPEC.leg_eff)
    delivered = sum(b.discharge(20, 0.25) for _ in range(20))
    # everything added above the start comes back only after round-trip losses
    assert b.soc == pytest.approx(SPEC.reserve_soc)
    start_usable = (0.3 - SPEC.reserve_soc) * SPEC.capacity_kwh * SPEC.leg_eff
    assert delivered == pytest.approx(start_usable + drawn * SPEC.round_trip_eff)


def test_cash_matches_hand_calc(month_runs):
    res = month_runs[("wattgap", "LZ_HOUSTON")]
    for s in res.steps[:500]:
        assert s.cash == pytest.approx(s.grid_kwh * s.price / 1000)
        assert s.wear == pytest.approx(max(s.grid_kwh, 0) * SPEC.degradation_per_kwh)


def test_baselines_are_sane(month_runs):
    for z in ZONES:
        naive = month_runs[("naive_overnight", z)]
        assert naive.kwh_discharged == 0
        assert all(datetime.fromisoformat(s.start).hour in (23, 0, 1, 2, 3, 4, 5, 6)
                   for s in naive.steps if s.action == "CHARGE")
        fair = month_runs[("scheduled", z)]
        for s in fair.steps:
            h = datetime.fromisoformat(s.start).hour
            if s.action == "DISCHARGE":
                assert 17 <= h < 21
            if s.action == "CHARGE":
                assert 0 <= h < 6
        assert fair.kwh_discharged > 0


def test_trailing_window_uses_prior_day_not_empty_history():
    d = SCENARIOS["quiet"]
    assert len(econ.trailing_prices(d, "LZ_WEST")) == 96
    first = econ.simulate("trailing", "LZ_WEST", [d]).steps[0]
    assert first.action in ("CHARGE", "HOLD", "DISCHARGE")  # decided against yesterday's prices


def test_leftover_energy_is_valued():
    res = econ.simulate("naive_overnight", "LZ_HOUSTON", [SCENARIOS["quiet"]])
    assert res.kwh_charged > 0 and res.terminal_value > 0
    assert res.net == pytest.approx(res.energy_cash - res.wear + res.terminal_value)


def test_reason_separates_system_from_zone():
    spike = SCENARIOS["spike"]
    iv = next(i for i in day(spike) if i.start.strftime("%H:%M") == "19:15")
    trailing = [i.prices["LZ_SOUTH"] for i in day(spike)][:76]
    ctx = econ.Context(iv, "LZ_SOUTH", trailing, [i.system_price for i in day(spike)][:76], Battery(0.5))
    text = econ.reason(ctx)
    assert "system-wide" in text and "LZ_SOUTH discount" in text


def test_gap_is_reported_against_fair_baseline():
    r = econ.compare_day(SCENARIOS["quiet"])
    assert r.gap_vs_fair == pytest.approx(r.net("wattgap") - r.net("scheduled"))


def test_day_ahead_prices_are_real_hourly_and_complete():
    for d in [*days_between(*SELECTION), *MONTH, *SCENARIOS.values()]:
        hours = dam_day(d)
        assert len(hours) == 24 and all(set(h) == set(ZONES) for h in hours)
    assert dam_day(SCENARIOS["spike"])[19]["LZ_HOUSTON"] == 1271.22  # HE20 in ERCOT's own file


def test_selection_and_evaluation_days_do_not_overlap():
    assert SELECTION[1] < EVALUATION[0]
    assert SCENARIOS["spike"] >= EVALUATION[0] and SCENARIOS["quiet"].year == 2026


def test_plan_uses_only_day_ahead_prices_for_that_day():
    d = SCENARIOS["spike"]
    plan = econ.dam_plan(d, "LZ_WEST", PLANNER.window_h)
    prices = [h["LZ_WEST"] for h in dam_day(d)]
    assert plan.dam == tuple(prices)
    assert len(plan.discharge) == PLANNER.window_h and len(plan.charge) == econ.refill_hours(SPEC) == 2
    assert min(prices[h] for h in plan.discharge) >= max(prices[h] for h in plan.charge)
    assert not plan.charge & plan.discharge


def test_unprofitable_day_ahead_spread_plans_nothing(monkeypatch):
    flat = [dict.fromkeys(ZONES, 30.0)] * 24
    monkeypatch.setattr(econ, "dam_day", lambda d: flat)
    econ.dam_plan.cache_clear()
    try:
        plan = econ.dam_plan(date(2099, 1, 1), "LZ_WEST", 1)
        assert not plan.charge and not plan.discharge
    finally:
        econ.dam_plan.cache_clear()


def test_planner_trades_only_in_windows_or_on_a_spike(month_runs):
    for z in ZONES:
        for s in month_runs[("wattgap", z)].steps:
            t = datetime.fromisoformat(s.start)
            plan = econ.dam_plan(t.date(), z, PLANNER.window_h)
            if s.action == "CHARGE":
                assert t.hour in plan.charge
            if s.action == "DISCHARGE" and t.hour not in plan.discharge:
                assert s.price >= PLANNER.spike_mult * plan.top_dam  # the real-time override
            if s.action == "DISCHARGE" and t.hour in plan.discharge:
                assert s.price >= econ.breakeven(SPEC, plan.charge_cost) - 1e-9


def test_planner_is_causal_in_real_time():
    """Changing prices after an interval can't change the decision taken in it."""
    d = SCENARIOS["spike"]
    iv = day(d)[60]  # 15:00 CT
    ctx = econ.Context(iv, "LZ_HOUSTON", [0.0] * 96, [0.0] * 96, Battery(0.8))
    other = econ.Context(iv, "LZ_HOUSTON", [9999.0] * 96, [9999.0] * 96, Battery(0.8))
    assert econ.POLICIES["wattgap"](ctx) == econ.POLICIES["wattgap"](other)


def test_home_load_is_real_and_splits_discharge():
    res = econ.simulate("wattgap", "LZ_HOUSTON", MONTH[:7])
    assert all(s.home_kwh > 0 for s in res.steps)
    assert res.kwh_to_home + res.kwh_exported == pytest.approx(res.kwh_discharged)
    for s in res.steps:
        assert s.to_home_kwh <= s.home_kwh + 1e-12 and s.export_kwh >= 0
