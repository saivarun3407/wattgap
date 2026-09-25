# Data provenance

Every price WattGap replays is **real ERCOT data**. Nothing in `data/` is synthetic.

| File | What | ERCOT source | Dates (Central time) | Retrieved |
|---|---|---|---|---|
| `ercot_rtm_spp_2023-09.csv` | Real-time 15-min Settlement Point Prices, $/MWh | **NP6-785-ER** "Historical RTM Load Zone and Hub Prices", MIS reportTypeId **13061**, 2023 annual file. Product page: https://www.ercot.com/mp/data-products/data-product-details?id=NP6-785-ER | 2023-08-31 00:00 through 2023-09-30 23:45 (31 days × 96 intervals) | see `retrieved_at.json` |
| `ercot_rtm_spp_2026-09-20_21.csv` | Real-time 15-min Settlement Point Prices, $/MWh | **NP6-905-CD** "Settlement Point Prices at Resource Nodes, Hubs and Load Zones", MIS reportTypeId **12301**. Product page: https://www.ercot.com/mp/data-products/data-product-details?id=NP6-905-CD | 2026-09-20 00:00 through 2026-09-21 23:45 (2 days × 96 intervals) | see `retrieved_at.json` |

- **Zones:** `LZ_HOUSTON`, `LZ_NORTH`, `LZ_SOUTH`, `LZ_WEST` (the four competitive load zones).
- **Time:** the `interval_start_ct` column is the interval start in America/Chicago with its UTC offset (all rows here are CDT, `-05:00`).
- **How it was fetched:** `python3 scripts/fetch_ercot.py`. It downloads straight from ERCOT's public MIS: it lists documents at `https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=<id>` and fetches them from `https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId=<DocID>`. No API key is needed.
  - The 2023 source file is `rpt.00013061.0000000000000000.20240101.081911295.RTMLZHBSPP_2023.zip`.
  - The 2026 days come from the 96 per-interval NP6-905-CD CSV files for each day. These match the open-source `gridstatus` library's output for the same days.
- **Settlement point type:** only rows with Settlement Point Type **`LZ`** are kept. ERCOT's historical file also carries `LZEW` (energy-weighted) rows for the same zones, and those are dropped. ERCOT hour-ending 1–24 / interval 1–4 are converted to interval-start times in Central time. Values are rounded to cents; nothing else is changed.
- **Why these days:**
  - **2023-09-06, the spike day.** It has the highest price in the September 2023 file ($5,339.52/MWh, LZ_WEST, 19:30 CT) and 21 fifteen-minute intervals where the four-zone average was at or above $1,000/MWh.
  - **2026-09-21, the quiet day.** An ordinary day from this week, the most recent full day ERCOT still published when we fetched.
  - **September 2023.** Replayed as a whole month, so the result doesn't rest on one hand-picked day. The prior day (Aug 31 / Sep 20) is included only as the trailing 24-hour window the policy looks back on.
- **Not included:** load, generation mix and congestion shadow prices. "System-wide" in WattGap's reason text means the simple average of the four load-zone prices. "Zone congestion" means one zone's price is far from that average. Both are derived from the prices above.

The synthetic `sample_prices.csv` from the pre-event commits was removed. It is still in git history (`git show 6ab7d19:data/sample_prices.csv`).
