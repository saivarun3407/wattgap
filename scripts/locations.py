#!/usr/bin/env python3
"""Where a battery earns most: perfect-foresight bound and fair schedule per zone/hub and year.

Needs the yearly archives (`make archive`). Writes data/derived/locations.csv, docs/locations.svg
and prints the README table.  Run:  python3 scripts/locations.py [first_year last_year]
"""

from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wattgap import econ  # noqa: E402
from wattgap import locations as L  # noqa: E402
from wattgap.data import days_between  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CHART_POINTS = ("LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST")


def row(year: int, point: str) -> dict:
    starts, prices = L.year_prices(year, point)
    bound = L.perfect_foresight(prices, L.MW_SPEC)
    top10, best, best_share = L.concentration(L.daily(starts, bound.cash))
    days = days_between(date(year, 1, 1), date(year, 12, 31))
    fair = econ.simulate("scheduled", point, days, start_soc=0.0, spec=L.MW_SPEC, explain=False).net
    both = int(((prices < 0)).sum())
    return {"year": year, "point": point, "pf_usd_per_mw": round(bound.net), "fair_usd_per_mw": round(fair),
            "fair_share": round(fair / bound.net, 3), "top10_share": round(top10, 3), "best_day": best.isoformat(),
            "best_day_share": round(best_share, 3), "quick_estimate_usd_per_mw": round(L.claimed_method(starts, prices)),
            "negative_intervals": both}


def svg(rows: list[dict], years: list[int]) -> str:
    w, h, left, bottom, top = 640, 260, 56, 30, 20
    peak = max(r["pf_usd_per_mw"] for r in rows if r["point"] in CHART_POINTS)
    colors = {"LZ_HOUSTON": "#2563eb", "LZ_NORTH": "#dc2626", "LZ_SOUTH": "#16a34a", "LZ_WEST": "#d97706"}
    bw = (w - left - 10) / len(years) / (len(CHART_POINTS) + 1)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="sans-serif" font-size="11">',
           f'<text x="{left}" y="13">Perfect-foresight upper bound, $k per MW-year (1 MW / 2 MWh, real ERCOT RT prices)</text>']
    for k in range(0, int(peak / 1000) + 1, max(1, int(peak / 5000)) * 5 if peak > 50000 else 20):
        y = h - bottom - (h - bottom - top) * k * 1000 / peak
        out.append(f'<line x1="{left}" x2="{w - 10}" y1="{y:.1f}" y2="{y:.1f}" stroke="#ddd"/>'
                   f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end">{k}</text>')
    for i, y in enumerate(years):
        x0 = left + i * (len(CHART_POINTS) + 1) * bw
        out.append(f'<text x="{x0 + bw * 2:.1f}" y="{h - 12}" text-anchor="middle">{y}</text>')
        for j, p in enumerate(CHART_POINTS):
            v = next(r["pf_usd_per_mw"] for r in rows if r["point"] == p and r["year"] == y)
            bh = (h - bottom - top) * v / peak
            out.append(f'<rect x="{x0 + j * bw:.1f}" y="{h - bottom - bh:.1f}" width="{bw - 1:.1f}" height="{bh:.1f}" '
                       f'fill="{colors[p]}"><title>{p} {y}: ${v:,}</title></rect>')
    for j, p in enumerate(CHART_POINTS):
        out.append(f'<rect x="{w - 330 + j * 80}" y="24" width="10" height="10" fill="{colors[p]}"/>'
                   f'<text x="{w - 316 + j * 80}" y="33">{p[3:].title()}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main(years: list[int]) -> None:
    rows = [row(y, p) for y in years for p in (*L.ZONE_POINTS, *L.HUB_POINTS)
            if p in L.read_archive("rt", y)[1] and not np.isnan(L.read_archive("rt", y)[1][p]).any()]  # HB_PAN starts mid-2019
    L.DERIVED.mkdir(parents=True, exist_ok=True)
    with (L.DERIVED / "locations.csv").open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        wr.writeheader()
        wr.writerows(rows)
    (ROOT / "docs" / "locations.svg").write_text(svg(rows, years))
    print("| Year | " + " | ".join(p[3:].title() for p in CHART_POINTS) + " | Hub avg | Fair schedule (4-zone avg) | Top 10 days (North) | Best day (North) |")
    print("|---|" + "---:|" * (len(CHART_POINTS) + 4))
    for y in years:
        r = {x["point"]: x for x in rows if x["year"] == y}
        fair = sum(r[p]["fair_usd_per_mw"] for p in CHART_POINTS) / len(CHART_POINTS)
        n = r["LZ_NORTH"]
        print(f"| {y} | " + " | ".join(f"${r[p]['pf_usd_per_mw'] / 1000:.1f}k" for p in CHART_POINTS)
              + f" | ${r['HB_HUBAVG']['pf_usd_per_mw'] / 1000:.1f}k | ${fair / 1000:.1f}k | {n['top10_share']:.0%} | "
              f"{n['best_day']} ({n['best_day_share']:.0%}) |")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(list(range(int(a[0]), int(a[1]) + 1)) if a else list(range(2019, 2026)))
