"""The real network boundary: devices in child processes over localhost TCP."""

from wattgap.desk import Clock
from wattgap.live import Sim
from wattgap.security import new_key
from wattgap.transport import TcpTransport


def test_tcp_fleet_enrolls_dispatches_and_survives_sigkill(run):
    async def go():
        clock = Clock()
        transport = TcpTransport(clock, per_host=3)
        sim = Sim(start="14:15", size=24, clock=clock, key=new_key(), transport=transport, reply_timeout=0.5)
        await sim.start()
        enrolled = len(sim.fleet.registry.keys)
        first = await sim.step()
        pids = {pid for pid, _, _ in transport.hosts()}
        victims = sim.fleet.kill_zone("LZ_WEST", 0.5)  # one of West's two host processes
        await sim.step()
        after = await sim.step()
        hosts = transport.hosts()
        await sim.stop()
        return enrolled, first, pids, victims, after, hosts, sim
    enrolled, first, pids, victims, after, hosts, sim = run(go())
    assert enrolled == 24 and first.healthy == 24 and first.home_mw > 0
    assert len(pids) == 8  # 4 zones x 2 processes of 3 devices, all separate OS processes
    assert len(victims) == 3 and sum(not running for _, _, running in hosts) == 1
    assert after.healthy == 21
    dead = {e["unit"] for e in sim.audit.of_kind("unit_dead")}
    assert dead == set(victims)
