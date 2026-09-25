#!/usr/bin/env python3
"""Download the real ERCOT prices WattGap replays and write small CSVs to data/.

Straight from ERCOT's public MIS (no API key): real-time 15-minute Settlement Point Prices
for the four competitive load zones, Settlement Point Type "LZ" (the published load-zone
price, not the energy-weighted "LZEW" variant), in $/MWh, interval starts in US/Central.

  * NP6-785-ER  Historical RTM Load Zone and Hub Prices (reportTypeId 13061), 2023 workbook
  * NP6-905-CD  Settlement Point Prices at Resource Nodes, Hubs and Load Zones
                (reportTypeId 12301), one file per 15-min interval; ERCOT keeps only recent days

Usage:  pip install pandas openpyxl requests && python3 scripts/fetch_ercot.py
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

ZONES = ["LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST"]
DATA = Path(__file__).resolve().parents[1] / "data"
CT = ZoneInfo("America/Chicago")
LIST = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId={}"
GET = "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={}"


def documents(report_type: int) -> list[dict]:
    r = requests.get(LIST.format(report_type), timeout=60)
    r.raise_for_status()
    return [d["Document"] for d in r.json()["ListDocsByRptTypeRes"]["DocumentList"]]


def download(doc_id: str) -> zipfile.ZipFile:
    r = requests.get(GET.format(doc_id), timeout=120)
    r.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(r.content))


def interval_start(day: str, hour: int, interval: int) -> str:
    """ERCOT hour-ending 1-24 and interval 1-4 -> interval start, America/Chicago."""
    d = datetime.strptime(day, "%m/%d/%Y")
    t = datetime(d.year, d.month, d.day, tzinfo=CT) + timedelta(hours=hour - 1, minutes=15 * (interval - 1))
    return t.isoformat()


def to_wide(df: pd.DataFrame, cols: dict[str, str]) -> pd.DataFrame:
    df = df.rename(columns=cols)
    df = df[(df["type"] == "LZ") & df["name"].isin(ZONES)]
    df["interval_start_ct"] = [interval_start(*r) for r in zip(df["day"], df["hour"], df["interval"])]
    wide = df.pivot(index="interval_start_ct", columns="name", values="price")[ZONES]
    return wide.round(2).sort_index()


def historical_2023(first: date, last: date) -> pd.DataFrame:
    doc = next(d for d in documents(13061) if d["ConstructedName"].endswith("2023.zip"))
    z = download(doc["DocID"])
    sheets = pd.read_excel(z.open(z.namelist()[0]), sheet_name=None)
    df = pd.concat(sheets.values())
    days = {(first + timedelta(n)).strftime("%m/%d/%Y") for n in range((last - first).days + 1)}
    df = df[df["Delivery Date"].isin(days)]
    return to_wide(df, {"Delivery Date": "day", "Delivery Hour": "hour", "Delivery Interval": "interval",
                        "Settlement Point Name": "name", "Settlement Point Type": "type",
                        "Settlement Point Price": "price"}), doc["ConstructedName"]


def recent(days: list[date]) -> pd.DataFrame:
    wanted = {d.strftime("%Y%m%d") for d in days} | {(days[-1] + timedelta(1)).strftime("%Y%m%d")}
    docs = [d for d in documents(12301) if "_csv" in d["FriendlyName"]
            and d["FriendlyName"].split("_")[1] in wanted]
    frames = []
    for d in docs:
        z = download(d["DocID"])
        frames.append(pd.read_csv(z.open(z.namelist()[0])))
    df = pd.concat(frames)
    df = df[df["DeliveryDate"].isin({d.strftime("%m/%d/%Y") for d in days})]
    return to_wide(df, {"DeliveryDate": "day", "DeliveryHour": "hour", "DeliveryInterval": "interval",
                        "SettlementPointName": "name", "SettlementPointType": "type",
                        "SettlementPointPrice": "price"})


def main() -> None:
    out = {}
    sep, name = historical_2023(date(2023, 8, 31), date(2023, 9, 30))
    sep.to_csv(DATA / "ercot_rtm_spp_2023-09.csv")
    out["ercot_rtm_spp_2023-09.csv"] = {"source_file": name,
                                        "retrieved": datetime.now(CT).isoformat(timespec="minutes")}
    wk = recent([date(2026, 9, 20), date(2026, 9, 21)])
    wk.to_csv(DATA / "ercot_rtm_spp_2026-09-20_21.csv")
    out["ercot_rtm_spp_2026-09-20_21.csv"] = {"source_files": "96 NP6-905-CD csv files per day",
                                              "retrieved": datetime.now(CT).isoformat(timespec="minutes")}
    for f in out:
        rows = pd.read_csv(DATA / f)
        assert len(rows) % 96 == 0 and not rows.isna().any().any(), f
    (DATA / "retrieved_at.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
