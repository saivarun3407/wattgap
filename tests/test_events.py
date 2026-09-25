from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from wattgap import events

CT = ZoneInfo("America/Chicago")


def _series(bump_day: date, bump: float) -> dict:
    """Two seasons' worth of Saturdays at a flat $20, with `bump` added to LZ_AEN all day on bump_day."""
    out = {}
    for s in (2024,):
        for d in events.saturdays(s):
            t = datetime(d.year, d.month, d.day, tzinfo=CT)
            for k in range(96):
                ts = t + timedelta(minutes=15 * k)
                aen = 20.0 + (bump if d == bump_day else 0.0)
                out[ts] = {"LZ_AEN": aen, "HB_HUBAVG": 20.0, "LZ_LCRA": 20.0}
    return out


def test_saturdays_and_game_file():
    sats = events.saturdays(2024)
    assert all(d.weekday() == 5 for d in sats) and sats[0] == date(2024, 8, 31) and sats[-1] == date(2024, 11, 30)
    games = events.read_games()
    assert games and all(g.weekday() == 5 for g in games)  # the Friday games are excluded
    assert len([g for g in games if g.year in events.SEASONS]) == 17


def test_delta_finds_a_planted_effect_and_none_when_absent():
    kick = datetime(2024, 9, 14, 18, 0, tzinfo=CT)
    controls = {2024: [d for d in events.saturdays(2024) if d != kick.date()]}
    metric = events.METRICS["LZ_AEN - HB_HUBAVG"]
    planted = _series(kick.date(), 50.0)
    assert events.deltas(planted, [kick], controls, metric) == [50.0]
    assert events.deltas(_series(kick.date(), 0.0), [kick], controls, metric) == [0.0]
    lo, hi = events.bootstrap_ci(planted, [kick], controls, metric, n=200)
    assert lo == hi == 50.0


def test_window_is_kickoff_minus_2h_to_plus_4h():
    kick = datetime(2024, 9, 14, 18, 0, tzinfo=CT)
    s = _series(kick.date(), 0.0)
    for t, p in s.items():
        if t.date() == kick.date() and kick - timedelta(hours=2) <= t < kick + timedelta(hours=4):
            p["LZ_AEN"] = 44.0
    assert events.window_mean(s, kick.date(), kick, events.METRICS["LZ_AEN"]) == 44.0
