#!/usr/bin/env python3
"""Drive the running web app with headless Chromium and save screenshots.

Usage:  uvicorn wattgap.server:app --port 8765 &  python3 scripts/screenshots.py http://localhost:8765 docs/shots
Needs:  pip install playwright   (uses the system Chrome if present, else `playwright install chromium`)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def scroll_to(page, n: int) -> None:
    page.evaluate(f"document.querySelectorAll('h2')[{n}].scrollIntoView({{block: 'start'}})")
    page.wait_for_timeout(400)


def main(url: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page.goto(url)
        page.request.post(f"{url}/api/control/reset")
        page.request.post(f"{url}/api/control/play")
        page.wait_for_timeout(1500)
        page.screenshot(path=out / "01-overview.png")

        # wait for the planner to ask the desk, shoot the pending batch, then approve it
        deadline = time.time() + 30
        while time.time() < deadline and not page.locator(".st.pending").count():
            page.wait_for_timeout(500)
        page.request.post(f"{url}/api/control/pause")
        page.wait_for_timeout(1200)
        scroll_to(page, 1)
        page.screenshot(path=out / "02-desk-pending.png")
        page.locator(".btn.go").first.click()
        page.request.post(f"{url}/api/control/step")
        page.request.post(f"{url}/api/chaos/kill?zone=LZ_HOUSTON")
        page.request.post(f"{url}/api/control/step")
        page.wait_for_timeout(1500)
        page.screenshot(path=out / "03-kill-alarm.png")
        page.request.post(f"{url}/api/control/step")
        page.wait_for_timeout(1500)
        page.screenshot(path=out / "04-rebalanced.png")
        page.request.post(f"{url}/api/chaos/rogue")
        page.request.post(f"{url}/api/control/step")
        page.wait_for_timeout(1500)
        page.screenshot(path=out / "05-rogue-quarantined.png")

        scroll_to(page, 2)
        page.screenshot(path=out / "06-member.png")
        page.screenshot(path=out / "00-full-page.png", full_page=True)
        browser.close()
    print("\n".join(str(f) for f in sorted(out.glob("*.png"))))


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
