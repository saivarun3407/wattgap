#!/usr/bin/env python3
"""Download every file ERCOT's free MIS still holds for the short-retention real-time feeds.

MIS keeps these only ~5-7 days, so this is all the history there is without the Public API key.
  * NP6-970-CD  RTD Indicative LMPs (reportTypeId 13073): every ~5 min, prices for the next ~hour
  * NP6-323-CD  Real-Time Price Adders by SCED interval (reportTypeId 13221)
  * NP6-322-CD  SCED System Lambda (reportTypeId 13114)
  * NP6-905-CD  Settlement Point Prices, 15-min (reportTypeId 12301): what actually settled
Writes data/feeds/{rtd,adders,lambda,spp}.csv (git-ignored; re-run to extend). Load zones only.
Usage:  pip install requests && python3 scripts/fetch_feeds.py
"""

from __future__ import annotations

import csv
import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "data" / "feeds"
LIST = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId={}"
GET = "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={}"
FEEDS = {"rtd": 13073, "adders": 13221, "lambda": 13114, "spp": 12301}
ZONES = {"LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST"}


def rows(doc_id: str, kind: str) -> list[list[str]]:
    blob = requests.get(GET.format(doc_id), timeout=120).content
    z = zipfile.ZipFile(io.BytesIO(blob))
    r = list(csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())))
    head, body = r[0], r[1:]
    if kind == "rtd":
        body = [x for x in body if x[5] in ZONES]
    elif kind == "spp":
        body = [x for x in body if x[3] in ZONES and x[4] == "LZ"]
    return [head, *body]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for kind, rid in FEEDS.items():
        docs = [d["Document"] for d in requests.get(LIST.format(rid), timeout=60).json()["ListDocsByRptTypeRes"]["DocumentList"]]
        docs = [d for d in docs if "_csv" in d["FriendlyName"]]
        path = OUT / f"{kind}.csv"
        seen, keep = set(), []
        if path.exists():
            with path.open() as f:
                old = list(csv.reader(f))
            keep = old[1:]
            seen = {x[0] for x in keep}
        head = None
        with ThreadPoolExecutor(8) as ex:
            for got in ex.map(rows, [d["DocID"] for d in docs], [kind] * len(docs)):
                head = got[0]
                keep += [x for x in got[1:] if x[0] not in seen]
        with path.open("w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(head)
            w.writerows(sorted({tuple(x) for x in keep}))
        print(kind, len(docs), "files,", len(keep), "rows", flush=True)


if __name__ == "__main__":
    main()
