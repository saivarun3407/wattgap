import asyncio

import pytest

from wattgap.live import Sim


@pytest.fixture
def run():
    """Run a coroutine to completion (keeps tests free of async plugins)."""
    return asyncio.run


async def make_sim(size: int = 40, start: str = "13:30", **kw) -> Sim:
    sim = Sim(start=start, size=size, secret=b"test-secret", reply_timeout=0.02, **kw)
    await sim.start()
    return sim


async def step_until_pending(sim: Sim, max_steps: int = 12):
    for _ in range(max_steps):
        pend = [b for b in sim.desk.batches.values() if b.status == "pending"]
        if pend:
            return pend[0]
        await sim.step()
    raise AssertionError("planner never asked the desk for an earn batch")
