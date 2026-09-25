from fastapi.testclient import TestClient

from wattgap.server import app


def test_web_app_end_to_end():
    with TestClient(app) as c:
        assert "WattGap" in c.get("/").text
        econ = c.get("/api/economics").json()
        assert set(econ["days"]) == {"spike", "quiet"} and econ["month"]["days"] == 30
        c.post("/api/control/pause")
        for _ in range(4):
            c.post("/api/control/step")
        state = c.get("/api/state").json()
        assert state["last"]["total"] == 400
        pending = [b for b in state["desk"] if b["status"] == "pending"]
        assert pending and c.post(f"/api/desk/{pending[0]['id']}/approve").json()["ok"]
        assert c.post("/api/chaos/kill?zone=LZ_WEST").json()["result"] == 30
        assert c.post("/api/chaos/nope").status_code == 404
        assert c.post("/api/chaos/kill?zone=LZ_MOON").status_code == 400
        c.post("/api/chaos/kill_desk")
        assert c.post(f"/api/desk/{pending[0]['id']}/approve").status_code == 409
        assert c.post("/api/protect?on=true").json()["protected"] is True
        assert c.get("/api/export").json()["summary"]["approvals_count"] == 1
        assert "evidence pack" in c.get("/api/export.html").text
