#!/usr/bin/env python3
"""Download the real ERCOT data WattGap replays and write small CSVs to data/.

Straight from ERCOT's public MIS and website (no API key). Load zones only, $/MWh, US/Central.

  Real-time 15-min Settlement Point Prices (Settlement Point Type "LZ", not the "LZEW" variant)
  * NP6-785-ER  Historical RTM Load Zone and Hub Prices (reportTypeId 13061), 2023 workbook
  * NP6-905-CD  Settlement Point Prices at Resource Nodes, Hubs and Load Zones (reportTypeId 12301)
  Day-Ahead Market hourly Settlement Point Prices (published ~13:00 CT the day before delivery)
  * NP4-180-ER  Historical DAM Load Zone and Hub Prices (reportTypeId 13060), 2023 workbook
  * NP4-190-CD  DAM Settlement Point Prices (reportTypeId 12331), one file per delivery day
  Residential load shape (15-min kWh for an average premise of the profile class)
  * Backcasted (Actual) Load Profiles: 2023 annual workbook, and the daily extract ZP18-68-M
    (reportTypeId 4) for 2026

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
# weather zone whose residential profile stands in for each load zone's homes
WEATHER_ZONE = {"LZ_HOUSTON": "COAST", "LZ_NORTH": "NCENT", "LZ_SOUTH": "SCENT", "LZ_WEST": "WEST"}
PROFILE = "RESHIWR"  # residential, high winter ratio (electric heat)
DATA = Path(__file__).resolve().parents[1] / "data"
CT = ZoneInfo("America/Chicago")
LIST = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId={}"
GET = "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={}"
LP_2023 = "https://www.ercot.com/files/docs/2023/02/06/ERCOT-Backcasted-Load-Profiles-2023.zip"

HIST = (date(2023, 7, 1), date(2023, 9, 30))  # Jul-Aug = parameter selection, Sep = evaluation
RECENT = [date(2026, 9, 20), date(2026, 9, 21)]


def documents(report_type: int) -> list[dict]:
    r = requests.get(LIST.format(report_type), timeout=60)
    r.raise_for_status()
    return [d["Document"] for d in r.json()["ListDocsByRptTypeRes"]["DocumentList"]]


def fetch(url: str) -> bytes:
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    return r.content


def unzip_one(blob: bytes):
    z = zipfile.ZipFile(io.BytesIO(blob))
    return z.open(z.namelist()[0])


def mdy_days(first: date, last: date) -> set[str]:
    return {(first + timedelta(n)).strftime("%m/%d/%Y") for n in range((last - first).days + 1)}


def start_ct(day: str, hour: int, minute: int = 0) -> str:
    d = datetime.strptime(day, "%m/%d/%Y")
    return (datetime(d.year, d.month, d.day, tzinfo=CT) + timedelta(hours=hour, minutes=minute)).isoformat()


def wide(df: pd.DataFrame, index: str) -> pd.DataFrame:
    return df.pivot(index=index, columns="name", values="price")[ZONES].round(2).sort_index()


# ---------------------------------------------------------------- real-time
def rt_frame(df: pd.DataFrame, cols: dict[str, str]) -> pd.DataFrame:
    df = df.rename(columns=cols)
    df = df[(df["type"] == "LZ") & df["name"].isin(ZONES)].copy()
    # ERCOT hour-ending 1-24 and interval 1-4 -> interval start
    df["interval_start_ct"] = [start_ct(d, h - 1, 15 * (i - 1)) for d, h, i in zip(df["day"], df["hour"], df["interval"], strict=True)]
    return wide(df, "interval_start_ct")


def rt_2023() -> tuple[pd.DataFrame, str]:
    doc = next(d for d in documents(13061) if d["ConstructedName"].endswith("2023.zip"))
    df = pd.concat(pd.read_excel(unzip_one(fetch(GET.format(doc["DocID"]))), sheet_name=None).values())
    df = df[df["Delivery Date"].isin(mdy_days(*HIST))]
    return rt_frame(df, {"Delivery Date": "day", "Delivery Hour": "hour", "Delivery Interval": "interval",
                         "Settlement Point Name": "name", "Settlement Point Type": "type",
                         "Settlement Point Price": "price"}), doc["ConstructedName"]


def rt_recent() -> pd.DataFrame:
    wanted = {d.strftime("%Y%m%d") for d in RECENT} | {(RECENT[-1] + timedelta(1)).strftime("%Y%m%d")}
    docs = [d for d in documents(12301) if "_csv" in d["FriendlyName"] and d["FriendlyName"].split("_")[1] in wanted]
    df = pd.concat(pd.read_csv(unzip_one(fetch(GET.format(d["DocID"])))) for d in docs)
    df = df[df["DeliveryDate"].isin({d.strftime("%m/%d/%Y") for d in RECENT})]
    return rt_frame(df, {"DeliveryDate": "day", "DeliveryHour": "hour", "DeliveryInterval": "interval",
                         "SettlementPointName": "name", "SettlementPointType": "type",
                         "SettlementPointPrice": "price"})


# ---------------------------------------------------------------- day-ahead
def dam_frame(df: pd.DataFrame, cols: dict[str, str]) -> pd.DataFrame:
    df = df.rename(columns=cols)
    df = df[df["name"].isin(ZONES)].copy()
    df["hour_start_ct"] = [start_ct(d, int(he[:2]) - 1) for d, he in zip(df["day"], df["he"], strict=True)]
    return wide(df, "hour_start_ct")


def dam_2023() -> tuple[pd.DataFrame, str]:
    doc = next(d for d in documents(13060) if d["ConstructedName"].endswith("2023.zip"))
    df = pd.concat(pd.read_excel(unzip_one(fetch(GET.format(doc["DocID"]))), sheet_name=None).values())
    df = df[df["Delivery Date"].isin(mdy_days(*HIST))]
    return dam_frame(df, {"Delivery Date": "day", "Hour Ending": "he", "Settlement Point": "name",
                          "Settlement Point Price": "price"}), doc["ConstructedName"]


def dam_recent() -> tuple[pd.DataFrame, list[str]]:
    # each file is published the day before the delivery date it prices
    published = {(d - timedelta(1)).strftime("%Y%m%d") for d in RECENT}
    docs = [d for d in documents(12331) if "_csv" in d["FriendlyName"] and d["ConstructedName"].split(".")[3] in published]
    df = pd.concat(pd.read_csv(unzip_one(fetch(GET.format(d["DocID"])))) for d in docs)
    df = df[df["DeliveryDate"].isin({d.strftime("%m/%d/%Y") for d in RECENT})]
    return dam_frame(df, {"DeliveryDate": "day", "HourEnding": "he", "SettlementPoint": "name",
                          "SettlementPointPrice": "price"}), [d["ConstructedName"] for d in docs]


# ---------------------------------------------------------------- load shape
def profile_rows(rows, day_col: str, first_val: int) -> pd.DataFrame:
    """ERCOT profile rows (one per profile/day, 96 kWh values) -> kWh per interval by load zone."""
    keep = {f"{PROFILE}_{wz}": lz for lz, wz in WEATHER_ZONE.items()}
    out: dict[str, dict[str, float]] = {}
    for r in rows:
        if r[0] not in keep:
            continue
        day = r[day_col] if isinstance(r[day_col], str) else r[day_col].strftime("%m/%d/%Y")
        for k, kwh in enumerate(r[first_val:first_val + 96]):
            out.setdefault(start_ct(day, 0, 15 * k), {})[keep[r[0]]] = kwh
    return pd.DataFrame.from_dict(out, orient="index")[ZONES].rename_axis("interval_start_ct").sort_index()


def load_2023() -> pd.DataFrame:
    import openpyxl
    wb = openpyxl.load_workbook(unzip_one(fetch(LP_2023)), read_only=True)
    days = mdy_days(*HIST)
    rows = (r for m in ("July", "August", "September") for r in wb[m].iter_rows(min_row=2, values_only=True)
            if r[1].strftime("%m/%d/%Y") in days)
    return profile_rows(rows, 1, 2)


def load_recent() -> tuple[pd.DataFrame, list[str]]:
    names = {f"BcstPrfl{d.strftime('%m%d%Y')}" for d in RECENT}
    docs = [d for d in documents(4) if d["FriendlyName"] in names]
    frames = []
    for d in docs:
        df = pd.read_csv(io.BytesIO(fetch(GET.format(d["DocID"]))))
        frames.append(profile_rows(df.itertuples(index=False, name=None), 1, 2))
    return pd.concat(frames).sort_index(), [d["ConstructedName"] for d in docs]


def main() -> None:
    now = lambda: datetime.now(CT).isoformat(timespec="minutes")  # noqa: E731
    out = {}
    rt, name = rt_2023()
    rt.to_csv(DATA / "ercot_rtm_spp_2023-07_09.csv")
    out["ercot_rtm_spp_2023-07_09.csv"] = {"source_file": name, "retrieved": now()}
    rt_recent().to_csv(DATA / "ercot_rtm_spp_2026-09-20_21.csv")
    out["ercot_rtm_spp_2026-09-20_21.csv"] = {"source_files": "96 NP6-905-CD csv files per day", "retrieved": now()}
    dam, name = dam_2023()
    dam.to_csv(DATA / "ercot_dam_spp_2023-07_09.csv")
    out["ercot_dam_spp_2023-07_09.csv"] = {"source_file": name, "retrieved": now()}
    dam, names = dam_recent()
    dam.to_csv(DATA / "ercot_dam_spp_2026-09-20_21.csv")
    out["ercot_dam_spp_2026-09-20_21.csv"] = {"source_files": names, "retrieved": now()}
    recent, names = load_recent()
    pd.concat([load_2023(), recent]).round(3).to_csv(DATA / f"ercot_load_profile_{PROFILE.lower()}.csv")
    out[f"ercot_load_profile_{PROFILE.lower()}.csv"] = {
        "source_files": [LP_2023.rsplit("/", 1)[1], *names], "retrieved": now()}
    for f in out:
        rows = pd.read_csv(DATA / f)
        assert len(rows) and not rows.isna().any().any(), f
    (DATA / "retrieved_at.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
