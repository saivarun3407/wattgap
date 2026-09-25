#!/usr/bin/env python3
"""The forecasts ERCOT had published by 10:00 CT the day before (DAM bid close), for every day MIS still allows.

MIS keeps each posting of these hourly forecast products for only ~7 days, and the history of past
postings (the vintages) needs the Public API key, so this is all the vintage data available without one:
  * NP3-565-CD  Seven-Day Load Forecast by Model and Weather Zone (reportTypeId 14837)
  * NP4-737-CD  Solar Power Production, hourly actual and forecast: STPPF (reportTypeId 13483)
  * NP4-732-CD  Wind Power Production, hourly actual and forecast: STWPF (reportTypeId 13028)
For each operating day D it takes the latest posting at or before 10:00 CT on D-1, and writes one row to
data/derived/forecast_vintages.csv: forecast system peak load, the spread between ERCOT's load models at
that hour (model disagreement), wind and solar at the net-load peak, and the net-load peak.
Usage:  pip install requests && python3 scripts/fetch_vintages.py
"""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "data" / "derived" / "forecast_vintages.csv"
LIST = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId={}"
GET = "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={}"
PRODUCTS = {"load": 14837, "solar": 13483, "wind": 13028}
CUTOFF_HOUR = 10  # DAM bids and offers close at 10:00 CT the day before


def postings(rid: int) -> list[tuple[datetime, str]]:
    docs = requests.get(LIST.format(rid), timeout=60).json()["ListDocsByRptTypeRes"]["DocumentList"]
    return sorted((datetime.fromisoformat(d["Document"]["PublishDate"]), d["Document"]["DocID"])
                  for d in docs if "_csv" in d["Document"]["FriendlyName"])


def table(doc_id: str) -> list[dict]:
    z = zipfile.ZipFile(io.BytesIO(requests.get(GET.format(doc_id), timeout=120).content))
    return list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode())))


def he(s: str) -> int:
    return int(s.split(":")[0])


def main() -> None:
    posts = {k: postings(rid) for k, rid in PRODUCTS.items()}
    first = max(p[0][0] for p in posts.values()).date() + timedelta(days=1)
    last = min(p[-1][0] for p in posts.values()).date() + timedelta(days=1)
    rows = []
    d = first
    while d <= last:
        cutoff = datetime(d.year, d.month, d.day, CUTOFF_HOUR) - timedelta(days=1)
        pick = {}
        for k, ps in posts.items():
            ok = [p for p in ps if p[0].replace(tzinfo=None) <= cutoff]
            pick[k] = ok[-1] if ok else None
        if all(pick.values()):
            want = d.strftime("%m/%d/%Y")
            load = [r for r in table(pick["load"][1]) if r["DeliveryDate"] == want]
            inuse = {he(r["HourEnding"]): float(r["SystemTotal"]) for r in load if r["InUseFlag"] == "Y"}
            spread = {}
            for r in load:
                spread.setdefault(he(r["HourEnding"]), []).append(float(r["SystemTotal"]))
            solar = {int(r["HOUR_ENDING"]): float(r["STPPF_SYSTEM_WIDE"] or 0)
                     for r in table(pick["solar"][1]) if r["DELIVERY_DATE"] == want}
            wind = {int(r["HOUR_ENDING"]): float(r["STWPF_SYSTEM_WIDE"] or 0)
                    for r in table(pick["wind"][1]) if r["DELIVERY_DATE"] == want}
            net = {h: inuse[h] - solar.get(h, 0) - wind.get(h, 0) for h in inuse}
            peak_h = max(inuse, key=inuse.get)
            net_h = max(net, key=net.get)
            rows.append({"day": d.isoformat(), **{f"{k}_posted": pick[k][0].isoformat() for k in PRODUCTS},
                         "load_peak_mw": round(inuse[peak_h]), "load_peak_he": peak_h,
                         "load_model_spread_mw": round(max(spread[peak_h]) - min(spread[peak_h])),
                         "net_load_peak_mw": round(net[net_h]), "net_load_peak_he": net_h,
                         "wind_at_net_peak_mw": round(wind.get(net_h, 0)), "solar_at_net_peak_mw": round(solar.get(net_h, 0))})
            print(rows[-1], flush=True)
        d += timedelta(days=1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
