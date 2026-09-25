#!/usr/bin/env python3
"""Drive the running web app with headless Chromium, save screenshots, and fail on console errors.

Usage:  uvicorn wattgap.server:app --port 8765 &  python3 scripts/screenshots.py http://localhost:8765 docs/shots
Needs:  pip install playwright   (uses the system Chrome if present, else `playwright install chromium`)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def main(url: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    errors: list[str] = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page = ctx.new_page()
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
        api = lambda path: page.request.post(f"{url}{path}")  # noqa: E731

        def shot(name: str, anchor: str | None = None, full: bool = False) -> None:
            if anchor:
                page.locator(anchor).scroll_into_view_if_needed()
                page.evaluate(f"document.querySelector('{anchor}').scrollIntoView({{block: 'start'}})")
            page.wait_for_timeout(900)
            page.screenshot(path=out / name, full_page=full)

        api("/api/control/reset")
        api("/api/control/pause")
        page.goto(url)
        page.wait_for_selector("#onb:not([hidden])")
        page.locator("#phone").scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        page.locator("#phone").screenshot(path=out / "07-member-onboarding.png")
        page.locator("#onb .btn.go").click()
        page.wait_for_timeout(300)
        page.locator("#phone").screenshot(path=out / "08-member-onboarding-reserve.png")
        page.locator("#onb [data-onb=skip], #onb [data-onb='-1']").first.click()
        page.evaluate("closeOnb()")
        page.evaluate("window.scrollTo(0, 0)")
        shot("01-overview.png")
        shot("02-real-days.png", "#results")

        # the planner asks the desk: shoot the pending batch with its TTL, then approve
        api("/api/control/play")
        deadline = time.time() + 40
        while time.time() < deadline and not page.locator(".batch.pending").count():
            page.wait_for_timeout(400)
        api("/api/control/pause")
        shot("03-desk-pending.png", "#fleet")
        page.locator(".batch.pending .btn.go").first.click()
        page.wait_for_function("S.desk.some(b => b.status === 'approved')")
        api("/api/control/step")
        page.select_option("#zoneSel", page.evaluate("S.desk.find(b => b.status === 'approved').zones[0]"))
        page.locator("[data-chaos=kill]").click()
        api("/api/control/step")
        shot("04-kill-alarm.png", "#fleet")
        api("/api/control/step")
        shot("05-rebalanced.png", "#fleet")
        page.locator("[data-chaos=rogue]").click()
        page.locator("[data-chaos=forge]").click()
        page.locator("[data-chaos=redirect]").click()
        api("/api/control/step")
        shot("06-rogue-quarantined.png", "#fleet")

        page.locator("[data-tab=today]").click()
        shot("09-member-receipt.png", "#member")
        page.locator("[data-tab=month]").click()
        page.locator("#phone").screenshot(path=out / "10-member-statement.png")
        page.locator("[data-tab=bill]").click()
        page.locator("[data-bill=credit]").click()
        page.locator("#phone").screenshot(path=out / "11-member-bill.png")
        page.locator("[data-tab=protect]").click()
        page.locator("#protectToggle").click()
        page.wait_for_timeout(1200)
        page.locator("#phone").screenshot(path=out / "12-member-protect.png")
        shot("13-evidence.png", "#evidence")
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=out / "00-full-page.png", full_page=True)

        mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True)
        m = mobile.new_page()
        m.on("console", lambda msg: msg.type == "error" and errors.append(msg.text))
        m.goto(url)
        m.wait_for_selector("#onb:not([hidden])")
        m.evaluate("closeOnb()")
        m.wait_for_timeout(800)
        m.screenshot(path=out / "14-mobile.png")
        m.locator("#member").scroll_into_view_if_needed()
        m.evaluate("document.querySelector('#member').scrollIntoView({block: 'start'})")
        m.wait_for_timeout(800)
        m.screenshot(path=out / "15-mobile-member.png")
        browser.close()
    print("\n".join(str(f) for f in sorted(out.glob("*.png"))))
    print(f"console errors: {len(errors)}")
    for e in errors:
        print("  ", e)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
