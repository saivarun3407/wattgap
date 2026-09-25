from fastapi.testclient import TestClient

from wattgap.server import app


def test_web_app_end_to_end():
    with TestClient(app) as c:
        assert "WattGap" in c.get("/").text
        assert c.get("/static/app.js").status_code == 200 and c.get("/static/app.css").status_code == 200
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
        assert c.post("/api/chaos/rogue?zone=LZ_NORTH").json()["ok"]
        assert isinstance(c.post("/api/chaos/revoke_quarantined").json()["result"], list)
        for kind in ("forge", "replay", "redirect"):
            assert c.post(f"/api/chaos/{kind}?zone=LZ_NORTH").json()["ok"]
        home = c.post("/api/protect?on=true&scope=home").json()
        assert home["scope"] == "home" and c.get("/api/state").json()["home"]["protected"] is True
        assert c.post("/api/protect?on=true&scope=moon").status_code == 400
        assert c.post("/api/protect?on=true&scope=fleet").json()["protected"] is True
        assert c.get("/api/export").json()["summary"]["approvals_count"] == 1
        assert "evidence pack" in c.get("/api/export.html").text
        g = c.get("/api/grid").json()
        assert {r["point"] for r in g["locations"]} == {"LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST", "HB_HUBAVG"}
        assert g["radar"]["capture"] and g["radar"]["model"]["train_years"] == [2019, 2023]
        assert g["signals"]["rtd_runs"] > 0
