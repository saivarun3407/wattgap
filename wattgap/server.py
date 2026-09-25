"""One-page web app: real-day economics, live fleet with chaos, desk queue, member view.

Run:  uvicorn wattgap.server:app --port 8000     (or: make serve)
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from . import report
from .data import ZONES
from .desk import Clock
from .export import build_pack, write
from .live import Sim

STATIC = Path(__file__).resolve().parent / "static"
EXPORT_DIR = Path(__file__).resolve().parents[1] / "out" / "ui-export"
TICK_S = 2.0  # one replayed 15-minute interval every 2 real seconds


class App:
    sim: Sim
    playing = True
    loop_task: asyncio.Task | None = None

    async def reset(self) -> None:
        if getattr(self, "sim", None):
            await self.sim.stop()
        # real clock: desk TTLs and heartbeats count in real seconds, shortened for a live demo
        self.sim = Sim(start="13:00", size=400, clock=Clock(), desk_ttl_s=40.0, desk_timeout_s=6.0,
                       reply_timeout=0.1)
        await self.sim.start()

    async def run(self) -> None:
        while True:
            if self.playing:
                await self.sim.step()
            await asyncio.sleep(TICK_S)


state = App()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await state.reset()
    report.build()  # warm the economics cache
    state.loop_task = asyncio.create_task(state.run())
    yield
    state.loop_task.cancel()
    await state.sim.stop()


app = FastAPI(title="WattGap", lifespan=lifespan)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/economics")
def economics() -> dict:
    return report.build()


@app.get("/api/state")
def live_state() -> dict:
    return {**state.sim.view(), "playing": state.playing}


@app.post("/api/control/{action}")
async def control(action: str) -> dict:
    if action == "play":
        state.playing = True
    elif action == "pause":
        state.playing = False
    elif action == "step":
        await state.sim.step()
    elif action == "reset":
        await state.reset()
    else:
        raise HTTPException(404, action)
    return {"ok": True}


@app.post("/api/chaos/{kind}")
def chaos(kind: str, zone: str = "LZ_HOUSTON") -> dict:
    if zone not in ZONES:
        raise HTTPException(400, "unknown zone")
    f = state.sim.fleet
    actions = {
        "kill": lambda: len(f.kill_zone(zone, 0.3)),
        "partition": lambda: f.partition(zone, ticks=3),
        "stale": lambda: f.stale_feed(ticks=2),
        "rogue": lambda: f.make_rogue(),
        "forge": lambda: state.sim.forge_command(),
        "replay": lambda: state.sim.replay_command(),
        "kill_desk": state.sim.kill_desk,
        "revive_desk": state.sim.revive_desk,
    }
    if kind not in actions:
        raise HTTPException(404, kind)
    return {"ok": True, "result": actions[kind]()}


@app.post("/api/desk/{batch_id}/{decision}")
def desk(batch_id: str, decision: str) -> dict:
    d = state.sim.desk
    if not state.sim.desk_alive:
        raise HTTPException(409, "desk is offline")
    if decision not in ("approve", "reject"):
        raise HTTPException(404, decision)
    ok = d.approve(batch_id) if decision == "approve" else d.reject(batch_id)
    return {"ok": ok}


@app.post("/api/protect")
def protect(on: bool = True) -> dict:
    state.sim.fleet.protect(on)
    return {"ok": True, "protected": on}


@app.get("/api/export")
def export_json() -> dict:
    return build_pack(state.sim.audit)


@app.get("/api/export.html", response_class=HTMLResponse)
def export_html() -> str:
    _, hpath = write(build_pack(state.sim.audit), EXPORT_DIR)
    return hpath.read_text()
