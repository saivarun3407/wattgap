# Ideas: one platform, three apps

This is a list of directions, not a list of things we built. Where we built one, it links to the README section with the measured result. Every number here was checked against `/workspace/ercot-catalog/catalog.json`, the ERCOT MIS document lists, `site/opportunities.html`, or a command in this repo. Where a number didn't check out, it's corrected and marked. Where we couldn't re-check one, it's marked **unverified**.

## The framework

- **Core:** a catalog-driven event log with point-in-time queries. Every ERCOT posting is stored with the time ERCOT published it, so "what did the market know at 10:00 yesterday?" is a query, not a reconstruction. The catalog (522 entries, covering all 427 public EMIL products) says where each product lives, its columns, how often it posts and how long MIS keeps it.
- **Three apps on top:**
  - **Radar predicts.** How likely is a price spike tomorrow, or in the next few hours?
  - **Replay explains.** What happened at 19:30 on a spike day, and who knew what when?
  - **Signals act.** A 5-minute HOLD / PRE-CHARGE / DISCHARGE-NOW input to the dispatch desk.
- **Weekend scope:** the core on 8–10 feeds, one app end to end (Radar), and evidence that the catalog design scales to all 427 public products. We don't ingest them all.
  - Feeds wired in this repo: NP6-785-ER, NP4-180-ER, NP4-181-ER (yearly archives), NP4-190-CD, NP4-188-CD, NP3-565-CD, NP4-737-CD, NP4-732-CD, NP6-970-CD, NP6-323-CD, NP6-322-CD, NP6-905-CD, and the `daily-prc` dashboard. The yearly archives and the per-posting feeds use the same two MIS calls: list the documents for a report type, then download one.

## Data facts that shape everything

- **Free MIS keeps most files only 5–31 days.** From the catalog: RTD indicative LMPs (NP6-970-CD) and SCED adders/lambda (NP6-323-CD, NP6-322-CD) about 5 days; load, wind and solar forecasts about 7 days; hourly outage capacity (NP3-233-CD) and DAM AS prices (NP4-188-CD) about 31 days.
- **Forecast-version history needs the free Public API key.** 15 catalog products keep every past posting (vintage) behind a `postedDatetime` filter on the Public API: NP3-565-CD, NP3-566-CD, NP4-732/733/737/738/742/743/745/746-CD, NP4-442-CD, NP3-233-CD, NP3-765-CD, NP4-159-CD, NP4-33-CD. Without a key, `api.ercot.com/.../archive/np3-565-cd` returns HTTP 401 (checked 2026-09-25). So no-key history starts at collection time.
- **The exception is the yearly price archives:** NP6-785-ER (RT load-zone and hub prices, yearly workbooks back to 2010; 2011+ are full years), NP4-180-ER (DAM, same span), NP4-181-ER (DAM AS clearing prices, 2010 on). This repo downloads 2018–2025 of all three (`make archive`).
- **Not all catalog entries are data.** *Corrected:* the brief said 214 of 522 entries are documents, forms or notices. The catalog's `posting_type` counts are Document 135, Form 41 and Alert/Notice 45, which is **221**. Another 79 entries are gridstatus Python methods, 9 are ercot.com web pages, 5 are URLs and 6 are API entries, which leaves 171 Reports, 25 Dashboards, 4 Extracts, 1 Table and 1 Application.

## Physics: the three channels

Every signal in this document matters to a battery through one of three physical channels. Each idea below is tagged with its channel.
- **Energy balance (MW).** Is there enough supply for demand, this interval and this afternoon? Reserves, outages, forecasts, gas and weather work through this channel, and scarcity pricing is how it shows up in prices.
- **Rate of change (MW/s: inertia, ramps, frequency).** How fast does the balance move, and can the grid follow it? Net-load ramps at sunset, wind drop-offs, frequency events, and fast-response ancillary services.
- **Location (voltage, congestion, losses).** Where is the power, and can the wires move it? Congestion between zones and nodes, local distribution limits, outages on specific feeders.

**How WattGap maps onto the channels:** location analytics = **location**; Scarcity Radar = **energy balance**; Signals = **rate of change**.

**Facts that correct common shortcuts:**
- **Home batteries sell fast response, not inertia.** In ERCOT they reach ancillary services through the ADER pilot, which caps aggregations at **100 MW of Non-Spin and 100 MW of ECRS system-wide**. Home-battery inverters are grid-following, so they give fast *frequency response* when told to, not synthetic inertia.
- **ERCOT's LMPs have no marginal-loss component.** A nodal price is energy plus congestion only. In ERCOT, "location" means congestion, not losses.
- **Uri (Feb 2021) was a generation shortfall, not a stability cascade.** ERCOT deliberately shed firm load to stop frequency falling, after it had dropped to about **59.3 Hz**.
- **ERCOT's first under-frequency load-shedding (UFLS) stage is 59.3 Hz.**

| Idea | Channel |
|---|---|
| Ideas 1–2 (Terminal, Replay) | all three (infrastructure) |
| Idea 3, Scarcity Radar | energy balance |
| Idea 4, Who Moved the Market | location + energy balance |
| Idea 5, Notice-to-Signal | energy balance |
| Idea 6, Battery Alpha Map / locations | location |
| Idea 7, Signals | rate of change |
| Edges 1, 3 (RTD bias, feed lead-lag) | rate of change |
| Edges 2, 5, 6, 8, 10, 12 (model disagreement, outages, plan vs dispatch, DC ties, emergency pricing, notices) | energy balance |
| Edge 7 (load-distribution drift) | location |
| Edge 11 (AS-energy divergence) | rate of change + energy balance |
| Edges 4, 9 (price corrections, EIA cross-check) | none: data quality, not physics |
| GridGuard | location + energy balance |
| SpikeDesk | rate of change |
| Flexlet | energy balance (the site's own peak) |
| GridSense | rate of change + location |
| Events (UT games, ACL, F1) | location |
| Weather forecast error, cold snaps and gas supply, gas price, planned outages, school calendars, air quality, water/drought, conservation appeals | energy balance |
| Cloud/dust/haze, wind ramps | rate of change |
| Transmission maintenance, traffic/EV charging | location |
| Data centers and miners, hurricanes | energy balance + location |

## Ideas

### 1. ERCOT Terminal
*Channel: all three (infrastructure).*
Every public product in one queryable, point-in-time store, with alerts and plain-English questions. For traders, retailers, battery operators and Base.
- **Data review:** Most history without a key only starts when you start collecting (see above). The yearly price archives are the one deep no-key history. 221 of the 522 entries are documents, forms or notices, not tabular data.
- **Status:** not built. The catalog and the two MIS calls this repo uses are the skeleton.

### 2. Grid Replay
*Channel: all three (infrastructure).*
Reconstruct any moment on one timeline: prices, reserves, binding constraints (NP6-86-CD, MIS ~7 days), outage capacity (NP3-233-CD, ~31 days), forecast versions and notices. For Base post-mortems, regulators and journalists.
- **Data review:** This works for recent days and for price history. Older replays need the API key plus the archives. The brief says the notice archive had about 21 notices and 61 ops messages when checked. That's **unverified**: we didn't re-count. The catalog records only that the ops-messages page covered Sep 1–25, 2026 and is HTML only, with no bulk file.
- **Demo candidate:** 2024-05-08. It's the best single day of 2024 in every competitive zone's upper bound (12–13% of the year for Houston and North; see [Locations](../README.md#where-a-battery-earns-most-location-analytics)). Or 2023-09-06, already replayed in the fleet demo.

### 3. Scarcity Radar (built end to end, feature B)
*Channel: energy balance.*
The probability of a price spike, updated whenever ERCOT publishes. The brief's idea is 1–48 h ahead. What we built is day-ahead: a score at 13:30 CT for the next operating day.
- **Data review:** This is the best-supported idea for the future: those 15 forecast products keep every past version through `postedDatetime`. But that history needs the API key. With no key, the only full-history inputs are DAM prices and DAM AS prices, so that's what the backtested model uses. The value is concentrated. Recomputed here with a physical model (15-minute prices, charge before discharge, √0.9 per leg, $20/MWh wear), the top 10 days carried 47% (Houston) and 46% (North) of the 2024 upper bound. The catalog's hourly-average method gave 38% / 37%.
- **Result:** see [Scarcity Radar](../README.md#scarcity-radar-day-ahead-spike-score). In held-out 2024 it flagged one day, 2024-05-08, in all four zones, and all four spiked. It **didn't** add money over the day-ahead planner, because the planner already sold into that spike. The planner's larger gap to the upper bound is on ordinary days.

### 4. Who Moved the Market
*Channel: location + energy balance.*
An automatic explanation for each spike: the binding constraint, price-setting generators, a forecast miss or an outage.
- **Data review:** Generator-level disclosures (NP3-965-ER SCED, NP3-966-ER DAM, NP3-991-EX COP) arrive 60 days late, so any generator-level explanation is after the fact. Shadow prices and binding constraints (NP6-86-CD) post hourly, so a partial explanation right away is feasible: which constraint bound, and the zone spread. This repo already infers "zone congestion" from load-zone spreads only.

### 5. Notice-to-Signal
*Channel: energy balance.*
Parse ERCOT notices and ops messages into structured events (45 Alert/Notice products in the catalog).
- **Data review:** Cheap to build. Volume is low: the brief says about 2–3 ops messages a day, which is **unverified**. The main ops-message source is an HTML page with no bulk file. It's best as a Radar feature, not a product. We don't claim nobody else machine-reads them.

### 6. Battery Alpha Map (merged with feature A)
*Channel: location.*
Where storage earns most: volatility, congestion, AS prices under RTC, and data-center interconnection.
- **Data review:** Residential retail customers settle at the load-zone price, so for Base homes the zone level is what matters. Node level matters for utility-scale developers. RT AS clearing prices exist only since RTC+B went live on 2025-12-05 (NP6-331-CD live, NP6-796-ER history). The large-load page (WEB-LARGE-LOAD) has no location dataset, and the CDR page (WEB-CDR) has large-load totals by year only.
- **Result:** see [Where a battery earns most](../README.md#where-a-battery-earns-most-location-analytics). LZ_WEST had the highest upper bound of the four competitive zones in 5 of 7 years. Houston led in 2021 and 2022.

### 7. Real-time early warning = Signals (built, feature C)
*Channel: rate of change.*
- **Result:** see [Signals](../README.md#signals-real-time-early-warning). It uses all the RTD history the free MIS keeps: 1,600 runs over 5.5 days. No settled $1,000 spike happened in that window, so the hit rate at production thresholds is untestable. We say so.

## Edges and signals (hypotheses to test, not claims)

Each has a data review: does the product exist, what free MIS keeps, where history comes from, how often it posts, and whether it's doable this weekend.

1. **RTD look-ahead bias.** *[rate of change]* *Hypothesis:* RTD's indicative prices (NP6-970-CD) are biased in a predictable way by lead, hour and zone.
   - **Data:** NP6-970-CD exists (reportTypeId 13073, every 5 min, MIS ~5 days, 24 five-minute intervals ahead per run). **Correction:** NP6-788-CD is SCED *LMPs* per run, not the settled price. The settled 15-minute price is **NP6-905-CD**, so compare against that (or against NP6-788-CD, if the question is SCED-to-RTD). Longer history needs the API key.
   - **Weekend: tested, small sample.** Over 1,600 runs (Sep 20–25, 2026, four load zones), the indicative price was higher than the price the same interval got when it was next up. The mean error was +$16/MWh at 15 min, +$37 at 30 min, +$132 at 60 min and +$470 at 120 min. Of 513 indications of $500+ at a 60-minute lead, 26 held. Signals uses this: it ignores RTD beyond 30 minutes. That's 5.5 days of one season, and the look-ahead cutoff was picked after seeing this table.
2. **Model disagreement index.** *[energy balance]* *Hypothesis:* when ERCOT's forecast models disagree, uncertainty is high and spikes are likelier.
   - **Data:** NP4-442-CD (wind forecasts by model, reportTypeId 19385) and NP3-565-CD (load by model: A3, A6, E, E1, E2, E3, M, X) both exist. They post hourly, MIS keeps ~7 days, and vintages exist via the API key only.
   - **Weekend: collected, not testable.** `make vintages` records the 10:00 CT posting for 8 operating days (2026-09-19 to 09-26). The load-model spread at the forecast peak ranged from 1,203 to 6,062 MW. None of those days spiked, so there is nothing to fit, and it isn't in the Radar model.
3. **Feed lead-lag.** *[rate of change]* *Hypothesis:* the ~10-second grid-conditions dashboard (`daily-prc.json`, PRC in MW) falls before 5-minute prices move.
   - **Data:** the dashboard is live only (today's series). It's in the catalog as GEN-543-UI, with no archive.
   - **Weekend:** only if a poller runs for weeks. Signals reads PRC live (`make warn-live`), but there's no backtest.
4. **Price-correction fingerprints.** *[none (settlement data quality)]* *Hypothesis:* corrections cluster by interval type and zone, with a direction, and that's an exposure for anyone settling on first-published prices.
   - **Data:** **Correction:** the IDs are **NP4-196-M** (DAM Price Corrections, reportTypeId 13044) and **NP4-197-M** (RTM Price Corrections, reportTypeId 13045), not -CD. They're event-driven and MIS keeps ~180 days (488 RTM files posted, oldest 2026-07-10).
   - **Weekend:** feasible. Six months with no key.
5. **Outage revision velocity.** *[energy balance]* *Hypothesis:* sudden jumps in forced-outage capacity come before spikes.
   - **Data:** NP3-233-CD (Hourly Resource Outage Capacity, reportTypeId 13103) posts hourly. MIS keeps ~31 days (1,510 files, oldest 2026-08-25), and vintages exist via the API key.
   - **Weekend:** feasible on one month, though that month may have no spikes.
6. **Plan vs dispatch.** *[energy balance]* *Hypothesis:* some resources systematically under-deliver against their Current Operating Plan.
   - **Data:** NP3-991-EX (60-Day COP All Updates) and NP3-965-ER (60-Day SCED Disclosure) are daily, published 60 days late. MIS keeps ~4 years (916 and 923 files, oldest 2024-03-24).
   - **Weekend:** feasible but the files are large, and it's after the fact only.
7. **Load-distribution drift.** *[location]* *Hypothesis:* load distribution factors shifting at specific buses reveal new large loads (data centers) early.
   - **Data:** NP4-159-CD (reportTypeId 12324) is posted as needed. MIS keeps ~365 days, but only 12 files are posted (oldest 2025-10-29). Vintages exist via the API key.
   - **Weekend:** feasible to diff 12 files. The resolution is coarse, and a shift doesn't identify the load.
8. **DC tie schedule vs flow.** *[energy balance]* *Hypothesis:* ties flowing below their approved schedule is a scarcity sign.
   - **Data:** NP3-765-CD (Approved DC Tie Schedules, reportTypeId 24347) posts hourly, has existed since 2024-06-27, and MIS keeps ~7 days. Flows come from the `dc-tie-flows.json` dashboard, which is live only.
   - **Weekend:** live comparison only.
9. **Cross-agency check.** *[none (reporting quality)]* *Hypothesis:* gaps between EIA-930 and ERCOT load/generation expose reporting errors.
   - **Data:** EIA-930-ER (Daily Balancing Authority Operations Report) is on ERCOT's MIS, with ~1 year kept (364 files, oldest 2025-09-25). EIA's own API needs a free EIA key.
   - **Weekend:** feasible for one year.
10. **Emergency-pricing countdown.** *[energy balance]* *Hypothesis:* as cumulative emergency-pricing hours approach the program's limit, price behavior changes.
    - **Data:** NP4-412-CD (Emergency Pricing Program Cumulative Hours Tracking, reportTypeId 24885) posts every 15 min. It has existed since 2025-12-05, and MIS keeps ~7 days. No archive is listed.
    - **Weekend:** a live poller only. The regime-change test needs an event that may not happen.
11. **AS-energy divergence.** *[rate of change + energy balance]* *Hypothesis:* under RTC, AS prices should track the energy opportunity cost, so divergence means mispricing.
    - **Data:** NP6-331-CD (RT clearing prices for capacity, every 15 min, since 2025-12-05, MIS ~7 days) and NP6-796-ER (the weekly historical file). Pair them with RT energy prices from NP6-785-ER.
    - **Weekend:** feasible from 2025-12-05 on. `opportunities.html` shows RT AS means below DA for every product over that window.
12. **Notice timing.** *[energy balance]* *Hypothesis:* ERCOT advisories and watches (e.g. NP6-593-AN Advance Action Notice, NP4-51-AN Emergency Notice) lead spikes by a measurable time.
    - **Data:** 45 Alert/Notice products exist. The ops-message source is HTML only, and history is short.
    - **Weekend:** too little history to score honestly. It's a candidate Radar feature once collected.

## Supporting measured facts

| Claim in the brief | Checked against | Verdict |
|---|---|---|
| Perfect-foresight arbitrage ~$40k–55k/MW-yr | `opportunities.html` (hourly-average method) and this repo's LP (`make locations`) | **True for 2024–2025 only, and depends on method.** The hourly method reproduces exactly: North 2024 $54,338, Houston 2024 $51,720, North 2025 $45,701, Houston 2025 $39,869. With the 15-minute LP (charge before discharge, $20/MWh wear), 2024–2025 is $33.9k–$78.4k across the four zones, and 2019–2023 runs $32.7k–$221.7k. |
| North above Houston every year | the same two methods | **Only 2024 and 2025.** Houston was above North in 2019–2023 on the LP (e.g. 2022: $137.7k vs $105.9k), and in 2020–2022 on the hourly method. |
| DAM ancillary prices down 50–70% from 2024 to 2025 | NP4-181-ER archive, recomputed | **True.** RegUp −50%, RegDown −53%, RRS −51%, ECRS −70%, Non-Spin −51% (mean hourly MCPC). |
| 4CP intervals in 2024 and 2025 fell at ordinary prices ($23–65) | NP9-83-M intervals (from `opportunities.html`) and RT prices from the archive, recomputed | **True:** $22.78–$65.44/MWh at Houston and North in the interval ending at each 4CP label. The 2024-08-20 4CP day still had a $4,856/MWh interval at Houston, just not at the 4CP interval. |
| 2024 top 10 days = 37–38% of value | `opportunities.html` | **Method-dependent:** 37–38% with hourly averages, 46–47% with the 15-minute LP. |
| 2024-05-08 alone ~10% | both | **True:** 10% on the hourly method (Houston), 12–13% on the LP (Houston and North). |

## Product concepts

Four ways to package the platform as a product. For each: the pitch as written, the claims in it checked, then a data review (catalog.json, the MIS lists and public sources, checked 2026-09-25), then what WattGap already has and what's missing. Where the original pitch had a shaky fact, it's corrected here.

### GridGuard: outage-ahead reserve manager for utilities and co-ops
*Channel: location + energy balance.*

- **Customer:** Texas co-ops and retail providers, the kind of partners Base works with.
- **Problem:** they don't know which neighborhoods to pre-charge before a storm or a transmission fault.
- **Open Grid Data:** the ERCOT outage feed, NWS alerts and the load forecast combine into a per-zone outage risk score, updated every 5 minutes.
- **Orchestration:** one coordinator per zone and an agent per home battery. If a zone coordinator dies, the others elect a replacement. Stale agents get quarantined, and the fleet still reaches its reserve target. Kill it live in the demo.
- **Commercializable:** a "reserve-as-a-service" dashboard a co-op ops manager opens at 6 AM, sold per battery-month.

**Claims in the pitch, checked:**
- "Base's actual partners": **supported.** GVEC (a co-op) runs a Base battery program that grew from a 2 MW pilot to 50 MW in April 2026, and it qualified that aggregation in ERCOT's ADER pilot.
- "ERCOT outage feed": **wrong source for this job.** ERCOT's outage data is generation-side (see the data review).
- "Transmission fault": ERCOT only posts transmission status changes as event notices (NP6-661-AN). There's no real-time public fault feed.
- "Peer election" and "kill it live": the per-home kill, quarantine and zone re-commit exist and are tested. Coordinator peer election **isn't built**; the supervisor is one process.

**Data review.**
- **ERCOT doesn't publish neighborhood outages.** NP3-233-CD (Hourly Resource Outage Capacity) is *generation* outage MW by load zone (hourly; MIS keeps ~31 days; the API key gets history). The same goes for NP1-346-ER (Unplanned Resource Outages, daily, ~31 days) and the generation-outages dashboard. All of them measure supply-side stress. None tells you whether a street has lost power. The only ERCOT signal that touches customers is NP6-87-AN (EEA3 controlled outages, event notices), which is rare and system-wide.
- **Distribution outages come from the utilities.**
  - CenterPoint publishes an ArcGIS feature layer, "Unplanned Electric Outages": points with customers affected, circuit ID and estimated restoration time. JSON/GeoJSON, no key.
  - Oncor's Storm Center map updates every 10 minutes, but there's no documented data API. Scraping the map's backing data is fragile and its reuse terms are unclear.
  - Co-ops each run their own map, often on third-party platforms.
  - For history there's DOE/ORNL **EAGLE-I**: county-level customers out, every 15 minutes, 2014–2025, a free download scraped from those same maps. It's county-level, so it can't show one neighborhood, but it's enough to backtest "did this zone's homes lose power".
- **Weather:** the NWS alerts API (`api.weather.gov/alerts/active?area=TX`) is free and needs no key, but it does require a User-Agent header. We got HTTP 200 with one and 403 without. ERCOT's own NP6-18-AN (Adverse Weather notices) is event-driven.
- **Shaky claim:** "peer election when a zone coordinator dies" isn't built. WattGap's supervisor is **one process**. Sharding is only benchmarked, and nothing fails over if the supervisor dies.

**Reuse vs missing.**
- **Reuses:**
  - Heartbeats (suspect / dead / recovered), so a home that stops reporting in a storm is noticed.
  - Per-zone commitments that re-commit lower with an alarm when a zone breaks.
  - The fleet **Storm mode** and per-home **Protect** switch, which the battery enforces even against a bad command.
  - The fail-closed desk, ed25519 per-device signing with revocation, the audit/evidence pack, and the member receipts.
  - Signals' stale-feed HOLD is the same pattern a lost outage feed needs.
- **Missing:**
  - Ingest for NWS alerts and the CenterPoint layer, and an EAGLE-I backtest.
  - Mapping homes to counties or circuits.
  - Automatic Protect triggered by alerts (today it's manual).
  - Coordinator failover or peer election.
  - Anything on the device side: islanding and backup switching are hardware and firmware we don't have.

### SpikeDesk: real-time ancillary-services bidder for VPPs
*Channel: rate of change.*

- **Customer:** any VPP or aggregator (the pitch names Base, Tesla and Sunrun) bidding into ERCOT's ECRS, RRS and regulation.
- **Problem:** bids are made by humans in spreadsheets.
- **Open Grid Data:** ERCOT DAM and RTM prices, AS clearing prices, and load and renewables forecasts, turned into a next-hour price and an AS-award probability.
- **Orchestration:** the bid engine, price ingestors, telemetry aggregator and dispatch executor run as independent workers on a message bus.
  - If a feed goes stale, the engine falls back to the last known good data and shrinks bid size.
  - If the dispatch executor crashes, bids auto-cancel before gate closure.
- **Commercializable:** SaaS taking a percentage of captured revenue. Show $/battery/year captured vs a naive strategy.

**Claims in the pitch, checked:**
- **Base, Tesla and Sunrun are competitors or examples, not validated customers.** Base and Tesla are ADER pilot participants with their own dispatch software. Sunrun's large VPP footprint is mostly outside ERCOT.
- **ECRS, RRS and regulation aren't all open to home fleets.** Home fleets reach AS through the ADER pilot, which limits aggregations to **Non-Spin and ECRS, 100 MW each system-wide**. RRS and regulation aren't open to them there.
- "Bids made by humans in spreadsheets" is **unverified.** The large aggregators run automated platforms.
- "AS-award probability": no public data states it directly. It has to be modelled from delayed award data (see the data review).

**Data review.**
- **Prices:**
  - DAM AS clearing prices, **NP4-181-ER**: yearly archive back to 2012, no key. WattGap already downloads 2018–2025.
  - Real-time AS prices only exist since **RTC go-live on 2025-12-05**: NP6-331-CD (15-minute, MIS ~7 days) and the weekly archive NP6-796-ER. That's under 10 months of real-time AS history.
- **Awards are public, with delays:**
  - **NP3-911-ER** (2-Day DAM AS Reports): aggregate AS offer curves (price and MW per product) and cleared quantities, 48 hours late. MIS keeps ~31 days; the API key gets history.
  - **NP3-966-ER** (60-Day DAM Disclosure): resource-level AS offers and awards, 60 days late. MIS keeps ~4 years, no key.
  - **NP3-906-EX** (2-Day SCED AS Disclosure): since 2025-12-05, MIS ~31 days.
  - So you can estimate the chance an offer at price p gets awarded by replaying the aggregate offer stack against the cleared quantity. That's a model, not a published probability.
- **The revenue pitch is weaker than it sounds.** Mean DAM AS prices fell **50–70% from 2024 to 2025** (RegUp −50%, RegDown −53%, RRS −51%, ECRS −70%, Non-Spin −51%; see above).
- **Home batteries can only sell AS through ERCOT's ADER pilot.** It caps AS at **100 MW of Non-Spin and 100 MW of ECRS system-wide**, with 500 MW registered in total and no QSE above 90% (market notice M-A030226-01, March 2026). The addressable AS volume for home fleets is small.
- **Shaky claim:** Base, Tesla and Sunrun aren't validated customers. Tesla and Base are ADER participants with their own dispatch software, so they're **competitors or examples**, not buyers. Sunrun's big VPP footprint is mostly outside ERCOT. Realistic buyers are smaller aggregators, co-ops and REPs entering ADER.

**Reuse vs missing.**
- **Reuses:**
  - The desk (human approval, a cap, batches that expire).
  - Per-zone commitments with failure headroom, which is what an AS obligation needs.
  - Scarcity Radar (day-ahead spike score) and Signals (real-time warnings).
  - The DAM AS archive, and the audit trail as evidence for performance disputes.
- **Be honest that Radar added no money on held-out 2024–2025.**
- **Missing:**
  - Any AS offer model or award-probability model.
  - Co-optimizing energy against AS, and reserving state of charge for awarded AS.
  - Qualification and telemetry requirements, settlement, and a QSE relationship.

### Flexlet: demand-charge shaving for small commercial sites (HVAC + battery)
*Channel: energy balance.*

- **Customer:** gyms, restaurants and small data rooms on 4CP or demand-charge tariffs in Texas.
- **Problem:** 4CP peaks cost them thousands, and they have no way to predict or respond.
- **Open Grid Data:** ERCOT system load and its forecast feed a 4CP-probability alert. The pitch calls this the classic Texas money problem with almost no tooling.
- **Orchestration:** per-site agents (battery, thermostat, EV charger) coordinate to shed load in the 15-minute window. If a site agent goes offline, its share is redistributed. If the coordinator is lost, sites hold the last plan.
- **Commercializable:** a dead simple pitch, "we cut your 4CP bill." It's framed as the commercial version of what Base sells homes today.

**Claims in the pitch, checked:**
- **Small sites mostly aren't on 4CP.** 4CP only applies to premises that have hit at least 700 kW NCP. Gyms and restaurants are billed on their own monthly peak (NCP), so the honest pitch is "we cut your demand charge."
- **"Almost no tooling exists" is contradicted.** ERCOT reported 4,000+ premises responding to 4CP in 2024, and 4CP-alert services are an established market for large loads.
- **"Base sells this today to homes" is likely wrong.** Residential customers aren't billed on 4CP; residential transmission cost is recovered per kWh. Base's public offer is whole-home backup plus an electricity plan, with grid value from the fleet, not a 4CP-reduction product. We found no Base 4CP product for homes.

**Data review, and the pitch needs reframing.**
- **4CP mostly doesn't apply to these customers.** TDSP tariffs bill transmission on 4CP only for premises that have set an NCP demand of at least **700 kW** in any earlier billing month. Oncor's rider says this; CenterPoint uses 700 kVA. It matches ERCOT's rule that loads above 700 kW need an IDR meter (Protocols §18.6.1).
- **Small sites pay on their own monthly peak.** A gym or restaurant is usually well under 700 kW, so it's billed on its **monthly NCP demand**: its own highest 15-minute kW, whenever it happens. Some tariffs also have a ratchet; check the specific one. So Flexlet for small businesses is **site peak shaving**, which runs on the site's own load, not on grid prices.
- **For large sites that are on 4CP, price spikes are the wrong signal.** In 2024 and 2025 the 4CP intervals settled at ordinary prices, **$22.78–$65.44/MWh** (NP9-83-M plus the RT archive, checked above). A 4CP predictor needs a **system-load** forecast: NP3-565-CD / NP3-560-CD / NP3-561-CD (hourly, MIS ~7 days), and actuals from NP6-345-CD and the hourly load archive. It's also crowded: ERCOT reported 4,000+ premises responding to 4CP in 2024, and the PUCT is reviewing 4CP allocation.
- **Site data:** 15-minute interval data for smart meters is available from Smart Meter Texas with the customer's authorization. That's the only practical data source, and it's per customer, not public.

**Reuse vs missing.**
- **Reuses:** the orchestration shell (fleet of sites, heartbeats, quarantine for implausible telemetry, the desk as an owner override, audit, statements and bill-view UI), and a planner that already respects reserves and wear.
- **Doesn't apply:** Radar and Signals for small sites.
- **Missing:**
  - Real-time site-load telemetry.
  - A tariff engine (NCP, ratchets, TDSP rates).
  - A peak-shaving controller that forecasts the site's own peak.
  - Smart Meter Texas onboarding.
  - For the >700 kW tier, a system-load 4CP forecaster.

### GridSense: anomaly detection across the fleet and the grid
*Channel: rate of change + location.*

- **Customer:** Base ops.
- **Problem:** detecting a bad firmware rollout, a failing inverter batch, or a grid frequency event among 10,000 noisy batteries.
- **Open Grid Data:** ERCOT frequency, prices and outages as the "ground truth" that explains fleet anomalies.
- **Orchestration:** streaming telemetry workers, per-region detectors, and a supervisor that restarts and reschedules detectors. Demo it with partial data loss.
- **Commercializable:** weaker, since it's an internal tool. Only pick it if the other three feel too hard.

**Claims in the pitch, checked:**
- "ERCOT frequency as ground truth" works **live only.** The dashboard keeps about 2 hours of 10-second frequency samples, with no archive.
- "Outages" has the same generation-vs-distribution caveat as GridGuard.

**Data review.**
- **No public fleet telemetry.** ERCOT doesn't publish DER or home-battery telemetry. The closest is **RPTESR-M** (four-second ESR charging MW and system demand), which needs a free ERCOT API key and covers grid-scale storage only.
- **Frequency is public only live and in summaries.**
  - The ancillary-services dashboard JSON (`dashboards/ancillary-services.json`) carries `currentFrequency` every **10 seconds for the trailing ~2 hours**, plus AS capacity. We fetched it today, and it's live only, with no archive.
  - NP12-261-M (Frequency Measurable Events, weekly, MIS ~2 years) and NP12-265-M (frequency response performance, monthly) give event summaries.
  - A backtest would need weeks of polling.
- **Voltage and local outages have no public ERCOT source.** See GridGuard for utility maps and EAGLE-I.

**Reuse vs missing.**
- **Reuses:**
  - The signed telemetry path (ed25519, replay protection).
  - The physics check that quarantines implausible readings: a sensor-integrity layer is the core of GridSense.
  - Heartbeats, and the sharded telemetry benchmarks.
- **Missing:**
  - Actual measurements. The simulated devices report state of charge and power, not frequency or voltage.
  - Time sync, and a poller that archives the frequency dashboard.
  - Any external buyer.

### Which concept fits the two tracks best

**GridGuard fits Orchestration + Most Commercializable best**, with SpikeDesk second, Flexlet third and GridSense last.
- **Why GridGuard:** it reuses the most of what's already built and tested. It's what the heartbeats, zone re-commit, Storm mode and Protect, fail-closed desk and signed devices are for, so the story is failure handling rather than trading. Its data is free with no key (NWS alerts, CenterPoint's layer, EAGLE-I history). There's a real buyer pattern: co-ops already buy resilience from home-battery fleets, as in GVEC's program with Base.
- **Its risks are fixable and must be stated:** ERCOT outage data is generation, not distribution; Oncor has no documented feed; coordinator failover isn't built.
- **SpikeDesk** shows off Radar, Signals and the desk. But its revenue base shrank 50–70% in a year, ADER caps home-fleet AS at 100 MW per product, and the named "customers" are competitors.
- **Flexlet** has a clear buyer. But the honest version is site peak shaving on NCP demand, which needs site telemetry and a tariff engine we don't have. The 4CP angle only fits >700 kW sites and needs a load forecast, not our price signals.
- **GridSense** has no public data to prove it and no external buyer.

## Events and outside signals

The pitch text below is kept word for word; only the formatting is tidied. A **data review** after each part says whether the source is real, whether it's free and needs a key, whether there's history to backtest on, and corrects anything shaky. Sources were checked 2026-09-25.

### Events
*Channel: location.*

> Be honest about the physics first: a stadium is ~10–20 MW; a load zone is ~10,000+ MW. Events barely move zonal price. Where they matter:
>
> - Nodal prices/congestion at settlement points near the venue (Austin: DTFT, Moody Center area feeders).
> - Local distribution stress — EV charging surge, hotels, restaurants, traffic → this is where a home-battery fleet in nearby ZIPs is valuable to the utility (Austin Energy) — reserve/backup, not arbitrage.
> - Timing coincidence: 7pm kickoff + summer evening ramp = the worst hour anyway. Events sharpen an existing peak.

**Data review.**
- **Scale.** The ~10–20 MW stadium figure is a plausible order of magnitude, but it's **unverified**. Austin is its own load zone, **LZ_AEN** (Austin Energy), and it's much smaller than "10,000+ MW": a few thousand MW at peak (not re-checked here). LZ_NORTH and LZ_HOUSTON are the ones in the tens of GW. The conclusion still stands: one stadium is under 1% of the zone.
- **"DTFT" isn't an ERCOT settlement point.** We searched every name in a current NP6-905-CD file (2026-09-25 14:30, 1,136 rows) and found nothing like it.
  - The Austin-area price points that do exist are the zone **LZ_AEN**, the surrounding **LZ_LCRA**, and Austin Energy's generator resource nodes: **DECKER_GT** (Decker Creek, northeast Austin) and **SANDHSYD1_2, SANDHSYD3_4, SANDHSYD6_7, SANDHSYD_5AC, SANDHSYD_CC1** (Sand Hill Energy Center, southeast Austin). Both plants are roughly 10–20 km from DKR.
  - Resource nodes are generator buses, not the feeders that serve downtown or the Moody Center. ERCOT doesn't publish prices at "feeders"; distribution isn't in the nodal market.
- **Nodal history needs a key.** NP6-905-CD has resource-node prices, but free MIS keeps only ~7 days. The yearly archive WattGap uses (NP6-785-ER) has **only load zones and hubs**. Resource-node history needs the ERCOT Public API key, so the backtest below is zonal.
- **Timing.** Evening kickoffs do overlap the net-load ramp in September. Many games start at 11:00 or 14:30 CT, though: 9 of the 17 Saturday home games in 2023–2025 kicked off before 16:00.

> Data you can pull today
>
> - Ticketmaster Discovery API / SeatGeek API — venue, date, capacity, lat/lon.
> - Static calendars: UT football (DKR ~100k), Moody Center, COTA (F1 US GP is typically October, ~400k over the weekend), ACL Fest (early Oct, Zilker), Cowboys/Texans/Rangers/Astros/Mavs/Spurs for the other zones.
> - Map venue → nearest ERCOT settlement point / load zone → nearby ZIP cluster.

**Data review.**
- **Both APIs need keys.** Ticketmaster Discovery needs a free developer `apikey` (default quota 5,000 calls a day). SeatGeek needs a free `client_id`. Neither reliably gives venue capacity or actual attendance. For history, ESPN's public schedule endpoint gives kickoff times and attendance with no key; that's what the backtest uses.
- **Dates and sizes:**
  - DKR's official capacity is **100,119**; recorded crowds reached 105,215 (Georgia, 2024).
  - F1 US GP at COTA: **Oct 20–22 2023, Oct 18–20 2024, Oct 17–19 2025, Oct 23–25 2026**. So it's "typically October", as the pitch says. The ~400k weekend attendance is as reported by promoters; not re-checked.
  - ACL Fest at Zilker runs two weekends: **Oct 6–8 and 13–15 2023; Oct 4–6 and 11–13 2024; Oct 3–5 and 10–12 2025; Oct 2–4 and 9–11 2026**. That's early-to-mid October, with ~75k a day.
  - The Moody Center size wasn't checked.
- **Mapping venue → settlement point:** there's no official venue-to-node map. Resource nodes have no public coordinates in the price files, so "nearest" has to come from plant locations.

> Feature design (fits any of the 4 ideas)
>
> - event_load_uplift(zone, hour) = Σ attendance × per-capita kW × proximity weight
> - Local congestion risk score = ERCOT nodal price deviation from zonal + event uplift + weather.
> - Backtest: pull last 2 years of nodal prices for the Austin nodes on UT home-game Saturdays vs non-game Saturdays. If there's a measurable delta, that's your headline chart. If not, say so — judges respect it.

**Data review.** Per-capita kW isn't published; it would be an assumption. The nodal-minus-zonal part needs resource-node history, and that needs the API key. We ran the backtest at zone level on three seasons (below).

**Backtest: UT home-game Saturdays (`make events`, `wattgap/events.py`).**
- **Game days:** all 17 Saturday home games at DKR in 2023–2025. The two Friday games (2023-11-24 and 2025-11-28) are excluded.
- **Kickoff times:** from ESPN's public schedule endpoint (`site.api.espn.com/apis/site/v2/sports/football/college-football/teams/251/schedule?season=YYYY`, retrieved 2026-09-25), saved in `data/events/ut_home_games.csv`. The Georgia 2024 game is listed at 18:49 CT, the actual start after delays.
- **Controls:** every other Saturday from Aug 26 to Nov 30 of the same season (25 days). A second variant also drops ACL and F1 Saturdays (17 days).
- **Window:** kickoff −2 h to +4 h in 15-minute RT prices (NP6-785-ER). Each control Saturday is read over the same clock window as the game it's compared with.
- **Delta:** game-day value minus the mean (or median) of that season's control days.
- **Uncertainty:** a 95% bootstrap CI that resamples games and control days, plus a permutation test that shuffles which Saturdays are "game days" within each season. The metrics are LZ_AEN, LZ_AEN − HB_HUBAVG and LZ_AEN − LZ_LCRA.

| Controls | Baseline | Metric | n games / controls | Mean delta $/MWh | Median delta | 95% CI | Permutation p |
|---|---|---|---:|---:|---:|---|---:|
| all other Saturdays | mean | LZ_AEN | 17 / 25 | −36.13 | −11.16 | [−107.85, −1.00] | 0.30 |
| all other Saturdays | mean | LZ_AEN − HB_HUBAVG | 17 / 25 | −6.76 | −1.63 | [−18.02, +0.23] | 0.29 |
| all other Saturdays | mean | LZ_AEN − LZ_LCRA | 17 / 25 | −0.05 | −0.17 | [−10.55, +10.09] | 0.98 |
| all other Saturdays | median | LZ_AEN | 17 / 25 | −1.48 | −4.65 | [−39.48, +9.03] | 0.92 |
| all other Saturdays | median | LZ_AEN − HB_HUBAVG | 17 / 25 | −0.67 | −0.47 | [−8.52, +2.34] | 0.84 |
| all other Saturdays | median | LZ_AEN − LZ_LCRA | 17 / 25 | +0.05 | −0.13 | [−1.61, +0.83] | 0.98 |
| excl. ACL and F1 | mean | LZ_AEN | 17 / 17 | −54.19 | −11.58 | [−153.69, −4.26] | 0.15 |
| excl. ACL and F1 | median | LZ_AEN − LZ_LCRA | 17 / 17 | +0.05 | −0.14 | [−15.58, +23.74] | 0.98 |

The full 12-row table is in `data/derived/events_backtest.json`.

- **No measurable game-day effect.** Austin's price relative to the surrounding zone (LZ_AEN − LZ_LCRA) moved **+$0.05/MWh**, with a 95% CI of **[−$1.61, +$0.83]** and p = 0.98. Relative to the hub average the result is also null.
- **The raw price shows game days *cheaper*, and that's an artifact.** The negative mean delta comes from one scarcity Saturday among the controls: **2023-08-26**, when LZ_AEN hit $4,913/MWh. Against the median control day the raw difference is −$1.48 (CI [−$39.48, +$9.03], p = 0.92). None of the permutation p-values is below 0.1.
- **Verdict: events are a footnote, not the headline.** At zone level, 100k people at DKR don't show up in the price. That's consistent with the physics note above. A nodal test (DECKER_GT / SANDHSYD_*) would need the API key. A local-distribution effect, if there is one, isn't visible in ERCOT prices at all.
- **Limits:** 17 games, fall only, and zone and hub prices only. The windows differ by kickoff time, which the same-clock controls handle, but weather differences between Saturdays aren't controlled.

> Where it slots
>
> - #3 Flexlet: bars/restaurants near the venue are exactly your customer — "game night = your demand peak, shave it."
> - #1 GridGuard: pre-position reserves in ZIPs around the venue before mega-events (F1 weekend, ACL) → utility-facing story.
> - #2 SpikeDesk: event uplift as one more feature in the nodal price model.
>
> Tonight's move: run the UT-game-Saturday backtest first (2 hours). It decides whether events are your headline or a footnote.

**Data review.**
- **Flexlet:** "game night = your demand peak" is about the business's *own* NCP peak, which fits the reframed Flexlet (monthly-peak shaving, not 4CP). It needs the site's meter data, not ERCOT data.
- **GridGuard:** pre-positioning is a reasonable resilience story. ERCOT prices give no evidence that the grid is stressed on those days (see the backtest).
- **SpikeDesk:** the backtest found no zonal uplift to use as a feature.
- **The backtest has been run**, with the result above.

### Other exogenous signals ERCOT doesn't publish

Roughly ordered by impact.

#### Big impact

> - Weather forecast error — ERCOT's load forecast uses one weather model; compare NWS/HRRR/ECMWF against it. Forecast miss = price spike. This is the single strongest signal in Texas.

**Data review: the premise is wrong.**
- ERCOT's mid-term load forecast runs several models (E, E1, E2, E3, M, A3, A6, and others). They differ mainly in which weather forecast they use. ERCOT's 2024 board education deck lists **4 global weather models (GFS, GFS Ensemble, Euro, NAM) plus 3 vendor forecasts**, with more contracted, **14 weather forecasts in total**.
- NP3-565-CD publishes every model's load forecast hourly, with an in-use flag. MIS keeps ~7 days; the API key gets history.
- So the signal worth testing is **model disagreement and forecast error versus actuals** (idea 2 in "Edges and signals"), not "one model versus NWS".
- NWS forecasts (`api.weather.gov`, no key), HRRR and GFS (NOAA open data on AWS/NODD, no key), and ECMWF open data (free, a subset of fields) are all available.
- "Single strongest signal" is **unverified**.

> - Cloud cover / dust / haze forecasts — solar ramp surprises (Saharan dust events, wildfire smoke). NOAA + Copernicus data.

**Data review:**
- NOAA HRRR smoke and cloud fields are free with no key.
- Copernicus CAMS dust and aerosol forecasts are free but need a registered account.
- ERCOT's solar forecasts (NP4-737-CD STPPF, hourly, MIS ~7 days) can serve as the baseline, so "surprise" = actual minus STPPF.
- History for both needs archive downloads. Doable, but not this weekend.

> - Wind ramp forecasts — West Texas wind dropping at sunset while load is peaking ("dunkelflaute"). HRRR wind at 80m.

**Data review:**
- HRRR does output 80 m wind, free and without a key.
- ERCOT posts its own wind forecasts (NP4-732-CD STWPF, and NP4-442-CD by model), so the test is whether HRRR beats them at ramp times.
- "Dunkelflaute" normally means multi-day low wind and solar. A sunset wind drop is a ramp, a different thing.

> - Cold snaps + gas supply — well freeze-offs, pipeline notices (critical notices on pipeline EBBs are public). Uri-style risk.

**Data review:** interstate pipelines must post critical notices on their EBBs, and those are free to read. Formats differ by pipeline and there's no single feed. Texas intrastate pipelines aren't FERC-regulated, so coverage is partial. History depends on each EBB. Rare events make this hard to backtest.

> - Natural gas spot price (Waha, Houston Ship Channel) — sets marginal cost for most ERCOT hours. Waha goes negative regularly → cheap power in West Texas.

**Data review:**
- **True for 2024.** Waha daily prices were negative **49 times in 2024**, a record then, against once in 2023. There were 39 in 2025 and 99 so far in 2026 (LSEG data as reported by Reuters).
- Daily Henry Hub is free from EIA with a free key. Waha and Houston Ship Channel daily prices are mostly paywalled (ICE, Platts, LSEG).
- "Sets marginal cost for most hours" is plausible but not measured here.
- Consistent with this, LZ_WEST has by far the most negative 15-minute RT prices every year in the archive (e.g. 3,533 intervals in 2022).

#### Medium impact

> - Data center commissioning / crypto miner curtailment — miners (Riot, Marathon) curtail at high prices; announced load additions shift the baseline. Their public filings and ERCOT's large-load interconnection queue.

**Data review:**
- Riot and MARA file 10-Q/10-K reports on EDGAR (free), and Riot reports power-curtailment credits. These are monthly or quarterly, not dispatch-level.
- **ERCOT's large-load queue has changed.**
  - Large loads of 75 MW and up now go through the batch process, **Batch Zero** (effective 2026-07-11).
  - ERCOT's Sep 2026 board update gives aggregates: 204 projects / 66.4 GW conditionally base load, and 158 / 127.9 GW conditionally studied load.
  - ERCOT has paused energizing new large data-center and crypto loads pending a verification audit.
- Project-level detail isn't a public data product; the catalog lists only the Large Load Integration web page.
- Load distribution factors (NP4-159-CD) are the only bus-level public trace (idea 7 in "Edges and signals").

> - Planned generator outages — ERCOT publishes; combine with unplanned outage rate to get "thin reserve" days.

**Data review:**
- True. NP3-233-CD (hourly outage capacity by zone, MIS ~31 days, history via key), NP3-162-CD / NP3-161-CD (planned outage capacity margin) and NP1-346-ER (unplanned outages, daily, ~31 days).
- Note these *are* published by ERCOT, although the heading says "ERCOT doesn't publish".

> - Transmission maintenance / congestion — outage scheduler data; explains nodal divergences.

**Data review:** the public catalog has no transmission outage-schedule product; there are only NP6-661-AN notices. Constraint shadow prices are published (SCED and DAM binding constraints), and they explain congestion after the fact. **Detailed outage-scheduler data isn't a free public feed as far as we found.**

> - School calendars + holidays — load shape shifts (ERCOT models these, but roughly).

**Data review:** district calendars are public but scattered. ERCOT's load models include holidays and day-of-week. "Roughly" is unverified.

> - Hurricanes / tropical storms — NHC cone → Houston zone load drop + outage surge.

**Data review:** NHC GIS cone and track products are free with no key. EAGLE-I county outages (2014–2025, free) give history, for example Beryl in July 2024. It's a good GridGuard input.

#### Small but novel

> - Events (already covered).
> - Traffic / EV charging — TxDOT traffic data + EV registrations by county → evening charging peak by ZIP. Growing fast.
> - Air quality alerts — Ozone Action Days → AC use, industrial curtailment.
> - Water/drought — thermal plants derate on high cooling-water temps; TWDB reservoir data.
> - Social/news sentiment — "conserve energy" ERCOT appeals on X trend → measurable load drop.

**Data review:**
- **Events:** tested above, and null at zone level.
- **TxDOT:** traffic counts are public. EV registrations by county are available from TxDMV/DOE AFDC at a coarse level. Neither is a load measurement.
- **Ozone Action Days:** TCEQ posts them publicly.
- **TWDB:** reservoir levels are public (Water Data for Texas). Plant derates show up in ERCOT outage data rather than in reservoir levels.
- **"Conserve" appeals:** ERCOT's conservation appeals are posted as notices (the Alert/Notice products), which are better than X trends for timing. A measurable load drop is **unverified**; it's testable against NP6-345-CD actual load on appeal days.
