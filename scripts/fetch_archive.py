#!/usr/bin/env python3
"""Download ERCOT's yearly price archives and write compact per-year CSVs to data/archive/.

Straight from ERCOT's public MIS (no API key). Every load zone and hub, $/MWh, US/Central.

  * NP6-785-ER  Historical RTM Load Zone and Hub Prices (reportTypeId 13061), 15-min, one workbook per year
  * NP4-180-ER  Historical DAM Load Zone and Hub Prices (reportTypeId 13060), hourly, one workbook per year
  * NP4-181-ER  Historical DAM Clearing Prices for Capacity (reportTypeId 13091), hourly AS MCPC per year

The raw zips (~14 MB per RT year) go to data/raw/ and the derived CSVs to data/archive/.
Both are git-ignored: they are large and fully reproducible with this script (`make archive`).

Usage:  pip install pandas python-calamine requests && python3 scripts/fetch_archive.py [first_year last_year]
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "archive"
CT = ZoneInfo("America/Chicago")
LIST = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId={}"
GET = "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={}"
REPORTS = {"rt": 13061, "dam": 13060, "as": 13091}
YEARS = range(2018, 2026)


def documents(report_type: int) -> list[dict]:
    r = requests.get(LIST.format(report_type), timeout=60)
    r.raise_for_status()
    return [d["Document"] for d in r.json()["ListDocsByRptTypeRes"]["DocumentList"]]


def raw_zip(kind: str, year: int, docs: list[dict]) -> tuple[Path, dict]:
    doc = next(d for d in docs if d["ConstructedName"].endswith(f"_{year}.zip"))
    path = RAW / f"{kind}_{year}.zip"
    if not path.exists() or path.stat().st_size != int(doc["ContentSize"]):
        r = requests.get(GET.format(doc["DocID"]), timeout=600)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path, doc


def read_zip(path: Path) -> pd.DataFrame:
    z = zipfile.ZipFile(path)
    name = z.namelist()[0]
    blob = io.BytesIO(z.read(name))
    if name.endswith(".csv"):
        df = pd.read_csv(blob)
    else:
        df = pd.concat(pd.read_excel(blob, sheet_name=None, engine="calamine").values(), ignore_index=True)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def starts(days: pd.Series, per_hour: int) -> list[str]:
    """Sequential interval starts per delivery day, stepped in UTC so DST days get 23 or 25 hours right.

    Rows must already be in delivery order within each day (hour, repeated-hour flag, interval).
    """
    out, prev, k = [], None, 0
    step = timedelta(minutes=60 // per_hour)
    for d in days:
        if d != prev:
            m = datetime.strptime(d, "%m/%d/%Y")
            midnight = datetime(m.year, m.month, m.day, tzinfo=CT).astimezone(timezone.utc)
            prev, k = d, 0
        out.append((midnight + k * step).astimezone(CT).isoformat())
        k += 1
    return out


def ordered(df: pd.DataFrame, day: str, keys: list[str]) -> pd.DataFrame:
    df = df.copy()
    df["_d"] = pd.to_datetime(df[day], format="%m/%d/%Y")
    df["_rep"] = (df["Repeated Hour Flag"].astype(str).str.strip() == "Y").astype(int)
    return df.sort_values(["_d", *keys])


def rt_year(path: Path) -> pd.DataFrame:
    df = read_zip(path)
    df = df[df["Settlement Point Type"].astype(str).str.strip() != "LZEW"]  # keep LZ, drop energy-weighted variant
    df = ordered(df, "Delivery Date", ["Delivery Hour", "_rep", "Delivery Interval"])
    wide = df.pivot_table(index=["_d", "Delivery Hour", "_rep", "Delivery Interval", "Delivery Date"],
                          columns="Settlement Point Name", values="Settlement Point Price", aggfunc="first")
    wide = wide.reset_index().sort_values(["_d", "Delivery Hour", "_rep", "Delivery Interval"])
    wide.insert(0, "interval_start_ct", starts(wide["Delivery Date"], 4))
    return wide.drop(columns=["_d", "Delivery Hour", "_rep", "Delivery Interval", "Delivery Date"]).set_index("interval_start_ct")


def hour_ending(s: pd.Series) -> pd.Series:
    return s.astype(str).str.slice(0, 2).astype(int)


def dam_year(path: Path) -> pd.DataFrame:
    df = read_zip(path)
    df["_he"] = hour_ending(df["Hour Ending"])
    df = ordered(df, "Delivery Date", ["_he", "_rep"])
    wide = df.pivot_table(index=["_d", "_he", "_rep", "Delivery Date"], columns="Settlement Point",
                          values="Settlement Point Price", aggfunc="first").reset_index().sort_values(["_d", "_he", "_rep"])
    wide.insert(0, "hour_start_ct", starts(wide["Delivery Date"], 1))
    return wide.drop(columns=["_d", "_he", "_rep", "Delivery Date"]).set_index("hour_start_ct")


def as_year(path: Path) -> pd.DataFrame:
    df = read_zip(path)
    df["_he"] = hour_ending(df["Hour Ending"])
    df = ordered(df, "Delivery Date", ["_he", "_rep"])
    df.insert(0, "hour_start_ct", starts(df["Delivery Date"], 1))
    keep = [c for c in ("REGDN", "REGUP", "RRS", "NSPIN", "ECRS") if c in df.columns]
    return df.set_index("hour_start_ct")[keep]


def main(years) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    log = json.loads((OUT / "retrieved_at.json").read_text()) if (OUT / "retrieved_at.json").exists() else {}
    build = {"rt": rt_year, "dam": dam_year, "as": as_year}
    for kind, rid in REPORTS.items():
        docs = documents(rid)
        for y in years:
            path, doc = raw_zip(kind, y, docs)
            df = build[kind](path).round(2)
            name = f"{kind}_{y}.csv.gz"
            df.to_csv(OUT / name)
            log[name] = {"source_file": doc["ConstructedName"], "report_type_id": rid, "rows": len(df),
                         "published": doc["PublishDate"], "retrieved": datetime.now(CT).isoformat(timespec="minutes")}
            print(name, len(df), "rows,", df.shape[1], "columns", flush=True)
    (OUT / "retrieved_at.json").write_text(json.dumps(log, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(range(int(a[0]), int(a[1]) + 1) if a else YEARS)
