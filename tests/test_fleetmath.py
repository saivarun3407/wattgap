import numpy as np

from wattgap import fleetmath as fm
from wattgap.bench import run as bench_run
from wattgap.econ import SPEC
from wattgap.shard import ShardPool


def test_allocate_is_per_zone_proportional_and_reports_shortfall():
    zone = np.array([0, 0, 1, 1, 1])
    head = np.array([2.0, 6.0, 1.0, 1.0, 0.0])  # the last unit must not work
    kw, short = fm.allocate(np.array([4.0, 5.0]), head, zone)
    assert np.allclose(kw, [1.0, 3.0, 1.0, 1.0, 0.0])  # zone 0: half of each unit; zone 1: capped
    assert np.allclose(short, [0.0, 3.0])
    assert (kw <= head).all()


def test_usable_kw_respects_reserve_and_power():
    soc = np.array([SPEC.reserve_soc, 0.5, 1.0])
    kw = fm.usable_kw(soc, np.full(3, SPEC.reserve_soc))
    assert kw[0] == 0 and 0 < kw[1] <= SPEC.power_kw and kw[2] == SPEC.power_kw
    assert fm.usable_kw(np.array([0.6]), np.array([0.6]))[0] == 0  # a Protect floor at current charge


def test_physics_check_catches_a_lie_but_not_honest_rounding():
    soc, kw = np.array([0.8, 0.8]), np.array([5.0, 5.0])
    honest = fm.expected_soc(soc, kw)
    assert honest[0] < 0.8
    reported = np.array([honest[0] + 0.001, 1.0])
    assert fm.implausible(reported, soc, kw).tolist() == [False, True]


def test_heartbeat_goes_suspect_then_dead_and_recovers():
    state, misses = np.zeros(2, dtype=np.int8), np.zeros(2, dtype=np.int64)
    pinged, replied = np.array([True, True]), np.array([True, False])
    state = fm.heartbeat(state, misses, pinged, replied)
    assert [fm.STATE_NAMES[s] for s in state] == ["healthy", "suspect"]
    state = fm.heartbeat(state, misses, pinged, replied)
    assert state[1] == fm.DEAD
    state = fm.heartbeat(state, misses, pinged, np.array([True, True]))
    assert (state == fm.HEALTHY).all() and (misses == 0).all()


def test_sharded_math_matches_commitment():
    pool = ShardPool(4000, 3, kind="math", drop_rate=0.0)
    try:
        earn = np.array([True, False, True, False])
        delivered, replied = pool.tick(earn, ~earn)
    finally:
        pool.close()
    assert replied == 4000
    assert delivered[1] == delivered[3] == 0 and delivered[0] > 0 and delivered[2] > 0


def test_sharded_signed_path_round_trips_every_device():
    pool = ShardPool(40, 2, kind="signed")
    try:
        delivered, replied = pool.tick(np.ones(4, bool), np.zeros(4, bool))
    finally:
        pool.close()
    assert replied == 40 and delivered.sum() == 40.0


def test_bench_reports_latency_and_throughput():
    r = bench_run("math", 2000)
    assert r["units"] == 2000 and r["p95_ms"] >= r["p50_ms"] > 0 and r["cmds_per_s"] > 0
