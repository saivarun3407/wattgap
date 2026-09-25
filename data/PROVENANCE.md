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

## Grid analytics sources (location, Scarcity Radar, Signals)

All from ERCOT's public MIS with no API key. The large or reproducible downloads are **git-ignored** (`data/raw/`, `data/archive/`, `data/feeds/`). The analysis outputs in `data/derived/` are committed, and the UI and tests read those.

| Local path | What | ERCOT source | Dates (CT) | Fetch |
|---|---|---|---|---|
| `archive/rt_{2018..2025}.csv.gz` | RT 15-min settlement point prices, all load zones and hubs | **NP6-785-ER**, reportTypeId **13061**, yearly files | 2018-01-01 → 2025-12-31 | `make archive` |
| `archive/dam_{year}.csv.gz` | DAM hourly settlement point prices, all load zones and hubs | **NP4-180-ER**, reportTypeId **13060**, yearly files | same | `make archive` |
| `archive/as_{year}.csv.gz` | DAM ancillary-service clearing prices (RegUp, RegDown, RRS, NSPIN, ECRS from 2023) | **NP4-181-ER**, reportTypeId **13091**, yearly files | same | `make archive` |
| `feeds/rtd.csv` | RTD indicative LMPs, each run's next ~24 five-minute intervals, load zones | **NP6-970-CD**, reportTypeId **13073** | 2026-09-20 00:00 → 09-25 13:15 (1,600 runs) | `make feeds` |
| `feeds/adders.csv` | RT price adders per SCED run | **NP6-323-CD**, reportTypeId **13221** | 2026-09-20 → 09-25 13:20 | `make feeds` |
| `feeds/lambda.csv` | SCED system lambda per run | **NP6-322-CD**, reportTypeId **13114** | same | `make feeds` |
| `feeds/spp.csv` | settled RT 15-min prices, load zones | **NP6-905-CD**, reportTypeId **12301** | 2026-09-17 → 09-25 | `make feeds` |
| `derived/forecast_vintages.csv` | load forecast by model (peak, model spread), wind and solar at the net-load peak, as posted by 10:00 CT on D-1 | **NP3-565-CD** (14837), **NP4-732-CD** STWPF (13028), **NP4-737-CD** STPPF (13483) | operating days 2026-09-19 → 09-26 | `make vintages` |
| `derived/radar_live.json` | tomorrow's radar score | **NP4-190-CD** DAM SPPs (12331), **NP4-188-CD** DAM AS prices | posted 2026-09-25 for 09-26 | `make radar-live` |
| (live only) | physical responsive capability, MW | ERCOT dashboard `api/1/services/read/dashboards/daily-prc.json`, ~10 s updates, today only | not stored | `make warn-live` |
| `events/ut_home_games.csv` (committed) | Texas home games at DKR 2023–2025: kickoff (CT), opponent, attendance | ESPN public schedule endpoint `site.api.espn.com/apis/site/v2/sports/football/college-football/teams/251/schedule?season=YYYY` (not ERCOT, no key), retrieved 2026-09-25 | 2023-09-02 → 2025-11-28 | by hand (see `wattgap/events.py`) |

- **Retention.** The yearly archives are permanent. The 5-minute feeds and forecast postings stay on free MIS for only ~5–7 days, and their history needs the Public API key (the archive endpoint returns 401 without one). That's why Signals has six days of history and the vintages aren't in the radar model.
- **Archive processing (`scripts/fetch_archive.py`).** ERCOT hour-ending and interval numbers are converted to interval starts by stepping in UTC, so the DST days have 92 and 100 intervals. For the DAM, the repeated fall-back hour is averaged into one clock hour and the missing spring-forward hour copies the one before, so every day has 24 hours. Prices are unchanged otherwise. Check: the 2023 archive gives exactly the committed Jul–Sep 2023 files (0.00 difference). `HB_PAN` has gaps in 2019, so that point is skipped for 2019. Source file names and publish times are in `archive/retrieved_at.json` (retrieved 2026-09-25 ~13:12 CT).
- **Derived outputs:** `locations.csv` (`make locations`), `scarcity_model.json`, `scarcity_capture.csv` and `scarcity_days.csv` (`make scarcity`), `warn_backtest.json` (`make warn`), `forecast_vintages.csv`, `radar_live.json`.

The synthetic `sample_prices.csv` from the pre-event commits was removed. It is still in git history (`git show 6ab7d19:data/sample_prices.csv`). The earlier `ercot_rtm_spp_2023-09.csv` was replaced by the Jul–Sep file, which contains the same rows unchanged.
