from datetime import date, datetime

import pytest

from wattgap import econ
from wattgap.data import SCENARIOS, ZONES, day, days_between
from wattgap.econ import SPEC, Battery

MONTH = days_between(date(2023, 9, 1), date(2023, 9, 30))


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
    first = econ.simulate("wattgap", "LZ_WEST", [d]).steps[0]
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
