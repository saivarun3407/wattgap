# Data provenance

Everything WattGap replays is **real ERCOT data**. Nothing in `data/` is synthetic. `python3 scripts/fetch_ercot.py` (or `make data`) re-downloads all of it from ERCOT's public MIS and website with no API key. Exact source file names and retrieval times are in `retrieved_at.json`.

| File | What | ERCOT source | Dates (Central time) |
|---|---|---|---|
| `ercot_rtm_spp_2023-07_09.csv` | Real-time 15-min Settlement Point Prices, $/MWh | **NP6-785-ER** "Historical RTM Load Zone and Hub Prices", reportTypeId **13061**, 2023 annual file | 2023-07-01 00:00 to 2023-09-30 23:45 (92 days × 96) |
| `ercot_rtm_spp_2026-09-20_21.csv` | Real-time 15-min Settlement Point Prices, $/MWh | **NP6-905-CD** "Settlement Point Prices at Resource Nodes, Hubs and Load Zones", reportTypeId **12301**, 96 files per day | 2026-09-20 and 09-21 |
| `ercot_dam_spp_2023-07_09.csv` | **Day-Ahead Market** hourly Settlement Point Prices, $/MWh | **NP4-180-ER** "Historical DAM Load Zone and Hub Prices", reportTypeId **13060**, 2023 annual file | 2023-07-01 to 2023-09-30 (hourly) |
| `ercot_dam_spp_2026-09-20_21.csv` | Day-Ahead Market hourly Settlement Point Prices, $/MWh | **NP4-190-CD** "DAM Settlement Point Prices", reportTypeId **12331**, published 2026-09-19 and 09-20 (~13:00 CT, the day before delivery) | 2026-09-20 and 09-21 |
| `ercot_load_profile_reshiwr.csv` | Residential load shape: kWh per 15 min for the **average premise** of profile class `RESHIWR` | ERCOT **Backcasted (Actual) Load Profiles**: the 2023 annual workbook (`ERCOT-Backcasted-Load-Profiles-2023.zip`) and daily extract **ZP18-68-M** (reportTypeId **4**) for 2026 | same days as the RT files |

- **Zones:** `LZ_HOUSTON`, `LZ_NORTH`, `LZ_SOUTH`, `LZ_WEST` (the four competitive load zones). Only Settlement Point Type **`LZ`** is kept. The `LZEW` (energy-weighted) rows are dropped.
- **Time:** `interval_start_ct` and `hour_start_ct` are interval starts in America/Chicago with their UTC offset. ERCOT hour-ending 1–24 and interval 1–4 are converted to start times. Prices are rounded to cents and kWh to 0.001. Nothing else is changed.
- **Day-ahead is not hindsight.** ERCOT clears and publishes the DAM around 13:00 CT the day before delivery. The planner reads only the DAM prices for the day it is operating, which a real operator would have had the afternoon before. Real-time prices are only used up to the current interval (there is a test for this).
- **Load profile, stated assumptions:**
  - ERCOT profiles are by *weather* zone, and WattGap maps them to load zones: COAST→Houston, NCENT→North, SCENT→South, WEST→West.
  - `RESHIWR` (residential, high winter ratio, which means electric heat) is ERCOT's profile for all-electric homes. We assume that is the kind of home that buys a battery.
  - The profile is an average premise, not a metered home. In the live fleet, each simulated home scales it by a random factor between 0.7 and 1.3. The economics use the average premise as is.
- **Why these days:**
  - **Selection, 2023-07-02 to 08-31.** The only days used to choose planner parameters (`scripts/select_params.py`, see `docs/PARAMS.md`). July 1 is only the trailing window for the v1 policy.
  - **Evaluation, 2023-09-01 to 09-30.** The reported month. No parameter was chosen on it.
  - **2023-09-06, the spike day.** The highest price in September 2023 ($5,339.52/MWh, LZ_WEST, 19:30 CT), with 21 fifteen-minute intervals where the four-zone average was ≥ $1,000/MWh.
  - **2026-09-21, the quiet day.** An ordinary recent day, the latest full day ERCOT had published when we fetched.
- **Not included:** generation mix and congestion shadow prices. "System-wide" in WattGap's reason text means the simple average of the four load-zone prices, and "zone congestion" means one zone's price is far from that average.

The synthetic `sample_prices.csv` from the pre-event commits was removed. It is still in git history (`git show 6ab7d19:data/sample_prices.csv`). The earlier `ercot_rtm_spp_2023-09.csv` was replaced by the Jul–Sep file, which contains the same rows unchanged.
