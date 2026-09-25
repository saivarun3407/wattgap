from datetime import date, datetime, timedelta

import numpy as np
import pytest

from wattgap import econ
from wattgap import locations as L
from wattgap.data import EVALUATION, day, days_between
from wattgap.econ import Spec


def test_perfect_foresight_matches_hand_calc():
    # 10 kWh / 10 kW, 81% round trip (0.9 each leg), no wear: buy one hour at $10, sell one at $100
    spec = Spec(capacity_kwh=10, power_kw=10, round_trip_eff=0.81, degradation_per_kwh=0.0, reserve_soc=0.0)
    b = L.perfect_foresight(np.array([10.0, 100.0]), spec, hours=1.0)
    # 10 kWh drawn fills 9 kWh; 9 kWh stored delivers 8.1 kWh
    assert b.net == pytest.approx(8.1 * 0.100 - 10 * 0.010)
    assert b.grid_kwh[0] == pytest.approx(-10) and b.grid_kwh[1] == pytest.approx(8.1)


def test_perfect_foresight_respects_physics_and_wear():
    spec = Spec(capacity_kwh=10, power_kw=5, round_trip_eff=0.81, degradation_per_kwh=0.05, reserve_soc=0.2)
    prices = np.array([20.0, -5.0, 300.0, 40.0, 10.0, 90.0, 60.0])
    b = L.perfect_foresight(prices, spec, hours=1.0)
    assert (b.soc >= 2 - 1e-6).all() and (b.soc <= 10 + 1e-6).all()
    assert (np.abs(b.grid_kwh) <= 5 + 1e-6).all()
    # a spread that doesn't pay for wear and losses is never traded
    flat = L.perfect_foresight(np.array([50.0, 51.0, 50.0, 51.0]), spec, hours=1.0)
    assert flat.net == pytest.approx(0.0, abs=1e-9)


def test_upper_bound_beats_every_real_policy():
    days = days_between(*EVALUATION)[:10]
    for zone in ("LZ_HOUSTON", "LZ_WEST"):
        prices = np.array([i.prices[zone] for d in days for i in day(d)])
        bound = L.perfect_foresight(prices).net
        for p in ("scheduled", "trailing", "wattgap"):
            res = econ.simulate(p, zone, days, start_soc=econ.SPEC.reserve_soc, explain=False)
            assert res.energy_cash - res.wear <= bound + 1e-6, (p, zone)


def test_daily_attribution_and_concentration():
    t0 = datetime(2024, 5, 7)
    starts = [t0 + timedelta(hours=6 * k) for k in range(12)]  # three days, four points each
    by_day = L.daily(starts, [1.0] * 4 + [2.0] * 4 + [5.0] * 4)
    assert by_day == {date(2024, 5, 7): 4.0, date(2024, 5, 8): 8.0, date(2024, 5, 9): 20.0}
    share, best, best_share = L.concentration(by_day, top=1)
    assert best == date(2024, 5, 9) and share == best_share == pytest.approx(20 / 32)


def test_quick_estimate_reproduces_the_earlier_method():
    t0 = datetime(2024, 1, 1)
    starts = [t0 + timedelta(minutes=15 * k) for k in range(96)]
    prices = np.array([10.0] * 8 + [50.0] * 80 + [200.0] * 8)  # two cheap hours, two dear hours
    assert L.claimed_method(starts, prices) == pytest.approx(0.9 * 400 - 20)


def test_committed_location_table_is_consistent():
    rows = L.read_table()
    assert {r["point"] for r in rows} >= {"LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST", "HB_HUBAVG"}
    assert {int(r["year"]) for r in rows} >= set(range(2019, 2026))
    for r in rows:
        assert float(r["fair_usd_per_mw"]) <= float(r["pf_usd_per_mw"])  # the bound bounds the schedule
        assert 0 < float(r["best_day_share"]) <= float(r["top10_share"]) <= 1
