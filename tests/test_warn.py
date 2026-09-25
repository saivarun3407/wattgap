from datetime import datetime, timedelta

from conftest import make_sim

from wattgap import warn as W
from wattgap.fleet import FEED_STALE_S
from wattgap.warn import CT, Snapshot, WarnParams

T0 = datetime(2026, 9, 21, 17, 0, tzinfo=CT)


def snap(prices, at=T0, adder=0.0, prc=None, zone="LZ_NORTH"):
    fwd = tuple((at + timedelta(minutes=5 * (k + 1)), p) for k, p in enumerate(prices))
    return Snapshot(at, {zone: fwd}, adder, 25.0, prc)


def test_signal_actions():
    p = WarnParams()
    assert W.signal(snap([30] * 12), "LZ_NORTH", T0, p).action == W.HOLD
    assert W.signal(snap([1500] + [30] * 11), "LZ_NORTH", T0, p).action == W.DISCHARGE
    assert W.signal(snap([30, 30, 700] + [30] * 9), "LZ_NORTH", T0, p).action == W.PRECHARGE
    assert W.signal(snap([30] * 12, adder=5.0), "LZ_NORTH", T0, p).action == W.PRECHARGE
    assert W.signal(snap([30] * 12, prc=2400), "LZ_NORTH", T0, p).action == W.PRECHARGE
    # RTD's far intervals run high, so a price beyond the look-ahead is ignored
    assert W.signal(snap([30] * 10 + [5000, 5000]), "LZ_NORTH", T0, p).action == W.HOLD
    assert W.signal(snap([30] * 12), "LZ_SOUTH", T0, p).action == W.HOLD  # no data for the zone


def test_stale_feed_holds_even_in_a_spike():
    s = W.signal(snap([4000] * 12), "LZ_NORTH", T0 + timedelta(minutes=11), WarnParams())
    assert s.action == W.HOLD and "stale" in s.why and s.feed_age_s == 660


def test_snapshots_join_only_earlier_adders():
    rtd = [{"RTDTimestamp": "09/21/2026 17:00:03", "IntervalEnding": "09/21/2026 17:05:00", "SettlementPoint": "LZ_WEST", "LMP": "31"},
           {"RTDTimestamp": "09/21/2026 17:05:03", "IntervalEnding": "09/21/2026 17:10:00", "SettlementPoint": "LZ_WEST", "LMP": "33"}]
    adders = [{"SCEDTimestamp": "09/21/2026 17:00:00", "RTRDPA": "0"}, {"SCEDTimestamp": "09/21/2026 17:05:10", "RTRDPA": "9"}]
    lam = [{"SCEDTimeStamp": "09/21/2026 17:04:00", "CappedSystemLambda": "30"}]
    a, b = W.snapshots(rtd, adders, lam)
    assert (a.adder, a.system_lambda) == (0.0, 0.0)  # the lambda at 17:04 wasn't out yet at 17:00:03
    assert (b.adder, b.system_lambda) == (0.0, 30.0)  # the 17:05:10 adder came after this run


def test_settled_prices_and_backtest_counts():
    spp = [{"DeliveryDate": "09/21/2026", "DeliveryHour": "18", "DeliveryInterval": str(i), "SettlementPointName": "LZ_NORTH",
            "SettlementPointPrice": str(p)} for i, p in zip((1, 2, 3, 4), (40, 1200, 1300, 50), strict=True)]
    prices = W.settled(spp)
    assert prices["LZ_NORTH"][1] == (datetime(2026, 9, 21, 17, 15, tzinfo=CT), 1200.0)
    runs = [snap([30] * 12, T0 - timedelta(minutes=30)),  # quiet
            snap([30, 30, 800] + [30] * 9, T0 - timedelta(minutes=5)),  # warned 20 min ahead of 17:15
            snap([1500] + [30] * 11, T0 + timedelta(minutes=10)),
            snap([30] * 12, T0 + timedelta(minutes=40)),
            snap([900] + [30] * 11, T0 + timedelta(hours=3))]  # nothing follows: a false alarm
    b = W.backtest(runs, prices, 1000.0, WarnParams())
    assert (b.events, b.hits, b.alarms, b.false_alarms) == (1, 1, 2, 1)
    assert b.lead_min == [20.0] and b.hit_rate == 1.0 and b.false_alarm_rate == 0.5
    # causality: changing a later run can't change an earlier signal
    later = runs[:3] + [snap([5000] * 12, T0 + timedelta(minutes=40))] + runs[4:]
    assert [W.signal(s, "LZ_NORTH", s.at).action for s in later[:3]] == [W.signal(s, "LZ_NORTH", s.at).action for s in runs[:3]]


def test_look_ahead_bias_table():
    runs = [snap([100, 900], T0), snap([100, 50], T0 + timedelta(minutes=5))]
    rows = W.look_ahead_bias(runs)
    assert rows[0] == {"lead_min": 5, "n": 2, "mean_error": 0.0, "median_error": 0.0, "indicated_500": 0, "held_500": 0}
    assert rows[1]["mean_error"] == 800.0 and rows[1]["indicated_500"] == 1 and rows[1]["held_500"] == 0


def test_discharge_now_proposes_a_desk_batch_and_never_bypasses_approval(run):
    async def go():
        sim = await make_sim(size=120, start="10:00")  # quiet morning; batch above the 0.25 MW auto cap
        sim.fleet.warnings = {"LZ_NORTH": W.Signal("LZ_NORTH", W.DISCHARGE, T0, "RTD next interval $1,500/MWh")}
        reps = [await sim.step() for _ in range(2)]
        await sim.stop()
        return sim, reps
    sim, reps = run(go())
    earn = [b for b in sim.desk.batches.values() if b.kind == "earn"]
    assert earn and "early warning LZ_NORTH" in earn[0].reason
    assert earn[0].status == "pending" and all(r.delivered_mw == 0 for r in reps)


def test_stale_live_feed_holds_the_fleet(run):
    async def go():
        sim = await make_sim()
        sim.fleet.feed_at = sim.clock.now() - FEED_STALE_S - 60
        rep = await sim.step()
        await sim.stop()
        return rep
    rep = run(go())
    assert set(rep.zone_actions.values()) == {"HOLD"}
    assert any("stale price feed (660 s old)" in d for d in rep.degraded)
