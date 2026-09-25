from datetime import date

import numpy as np
import pytest

from wattgap import econ
from wattgap import scarcity as S
from wattgap.data import EVALUATION, SCENARIOS, day, days_between
from wattgap.econ import SPEC, Battery

MODEL = S.Model((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (0.0, 1.0, 0.0, 0.0), 0.5, 0.5, 1.0, True)


def test_features_use_only_day_ahead_data(monkeypatch):
    d = date(2024, 5, 8)
    monkeypatch.setattr(S, "dam_day", lambda _d: [{"LZ_NORTH": 20.0 + h} for h in range(23)] + [{"LZ_NORTH": 900.0}])
    monkeypatch.setattr(S, "_as_by_day", lambda _y: {d: 55.0})

    def no_real_time(_d):
        raise AssertionError("the radar must not read real-time prices")
    monkeypatch.setattr(S, "day", no_real_time)
    top, shape, as_max = S.features(d, "LZ_NORTH")
    assert top == pytest.approx(np.log(900)) and as_max == pytest.approx(np.log(55))
    assert shape == pytest.approx(np.log(900 / 31.5))


def test_score_is_causal_future_data_cannot_change_it(monkeypatch):
    """A day's score depends only on that day's DAM files; changing any other day changes nothing."""
    dam = {date(2024, 5, 8): 400.0, date(2024, 5, 9): 30.0}
    monkeypatch.setattr(S, "dam_day", lambda d: [{"LZ_WEST": 25.0}] * 23 + [{"LZ_WEST": dam[d]}])
    monkeypatch.setattr(S, "_as_by_day", lambda _y: {date(2024, 5, 8): 20.0, date(2024, 5, 9): 5.0})
    before = MODEL.score(S.features(date(2024, 5, 8), "LZ_WEST"))
    dam[date(2024, 5, 9)] = 5000.0  # tomorrow turns into a scarcity day
    assert MODEL.score(S.features(date(2024, 5, 8), "LZ_WEST")) == before


def test_radar_policy_is_causal_in_real_time():
    iv = day(SCENARIOS["spike"])[60]
    scores = {(iv.start.date(), "LZ_HOUSTON"): 0.9}
    pol = S.radar_planned(econ.PLANNER, MODEL, scores)
    a = econ.Context(iv, "LZ_HOUSTON", [0.0] * 96, [0.0] * 96, Battery(0.8))
    b = econ.Context(iv, "LZ_HOUSTON", [9999.0] * 96, [9999.0] * 96, Battery(0.8))
    assert pol(a) == pol(b)


def test_unflagged_days_run_the_normal_planner_and_reserve_holds():
    days = days_between(*EVALUATION)[:10]
    low = {(d, "LZ_SOUTH"): 0.0 for d in days}
    base = econ.simulate("", "LZ_SOUTH", days, policy=econ.POLICIES["wattgap"], explain=False)
    same = econ.simulate("", "LZ_SOUTH", days, policy=S.radar_planned(econ.PLANNER, MODEL, low), explain=False)
    assert same.net == pytest.approx(base.net)
    high = {(d, "LZ_SOUTH"): 1.0 for d in days}
    flagged = econ.simulate("", "LZ_SOUTH", days, policy=S.radar_planned(econ.PLANNER, MODEL, high), explain=False)
    assert flagged.min_soc >= SPEC.reserve_soc - 1e-9
    assert [s.action for s in flagged.steps] != [s.action for s in base.steps]


def test_fit_and_auc_on_separable_data():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(400, 3))
    y = (x[:, 0] + 0.2 * rng.normal(size=400) > 1.0).astype(float)
    mean, scale, coef = S.fit(x, y)
    m = S.Model(mean, scale, coef, 0.5, 0.0, 1.0, False)
    scores = [m.score(r) for r in x]
    assert S.auc(scores, y) > 0.95 and coef[1] > 0
    assert S.auc([0.1, 0.9], [False, True]) == 1.0


def test_committed_backtest_windows_do_not_overlap():
    m = S.load_model()
    assert S.TRAIN[1] < S.EVAL[0]
    rows = S.read_table("scarcity_capture.csv")
    for r in rows:
        assert r["window"] == ("train" if int(r["year"]) <= S.TRAIN[1] else "held-out")
        assert float(r["radar_share"]) <= 1 and float(r["planner_share"]) <= 1
        assert int(r["hits"]) <= min(int(r["flagged_zone_days"]), int(r["spike_zone_days"]))
    grid = __import__("json").loads(S.MODEL_FILE.read_text())["grid"]
    best = max(grid, key=lambda g: g["train_usd_per_home_yr"])
    assert (best["threshold"], best["hold"], best["spike_mult"], best["refill"]) == (m.threshold, m.hold, m.spike_mult, m.refill)
