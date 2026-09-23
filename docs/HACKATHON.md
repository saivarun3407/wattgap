# Hackathon review

## Event

| | |
|---|---|
| Name | **Base Power × AITX Talent Hackathon** |
| When | **Sep 25–27, 2026** (this weekend) · 48 hours |
| Where | Base Power HQ, **Austin, TX** (in person) |
| Hosts | Base Power + [AITX Community](https://www.aitxcommunity.com) |
| Backers | Thrive Capital, a16z |
| Apply | https://luma.com/aitx-94j6 |
| Judges | Base **engineering** team |
| Point | **Hiring.** They want Texas software engineers. Food covered. Laptop. |

Part of Austin **Deep Tech Week**. Not a crypto Base (Coinbase L2) hackathon. This is **Base Power Company** — home batteries + virtual power plant.

If you are not in Austin this weekend, you cannot walk in. Still useful to spec; they hire off what you build.

---

## Who Base Power is (why the tracks look like this)

Austin company. ~$13B post Series D (Aug 2026). Makes **Base Core** (~39–40 kWh home battery, 20 kW inverter; two units ≈ 78 kWh). Installs in under an hour. **Does not just sell hardware:** customer buys **electricity from Base**; the battery is the plant.

- Charge when ERCOT is cheap (wind/solar dump).
- Discharge when the grid is tight / prices spike.
- Whole-home backup when the grid dies.
- Fleet: **500+ MWh** in Texas; expanding to **PJM / Illinois**. **100+ installs/day**. Factory in the old Austin American-Statesman building.

Software they have said is hard (AITX podcast + factory interviews):

- Markets + comms to a **distributed fleet**
- Firmware on inverter/battery/gateway
- **Install ops** — send a crew to the wrong house and you cannot Ctrl-Z
- Factory software
- Decision at the edge, then dispatch

Tracks are not random. They are **job interviews in disguise**.

---

## Tracks (verbatim from Luma, then decoded)

### 1. Open Grid Data

> The Texas grid publishes a huge amount of real time and historical data and almost nobody does anything with it. Prices, load, generation mix, outages. Find something in it and make it useful.

**Decoded:** ERCOT is a gold mine and most dashboards are toys. They want someone who **pulls real public data** and **turns it into a decision**, not a Chart.js graveyard.

Public sources (weekend-viable):

- ERCOT Public API / Data Access Portal — [ercot.com data portal](https://www.ercot.com/services/mdt/data-portal), [developer.ercot.com](https://developer.ercot.com)
- 5-minute **SCED** real-time settlement point prices (`/rt/spp`, NP6-905, etc.)
- Load by **weather zone**, 7-day load forecast
- Fuel mix (wind/solar/gas/storage)
- Resource outages
- Fallback if API key/delay is painful: [GridStatus ERCOT](https://gridstatus.io/ercot), cached CSVs, or a pre-downloaded spike day (Uri / 2023 heat / 2026 event)

**Win this track:** one *insight* a Base operator or a homeowner would act on. “Houston LMP just 8× West because this constraint bound” > “here is a map.”

### 2. Orchestration

> Build a system that coordinates many independent things. Agents, jobs, workers, whatever you want. **What matters is how it holds up when pieces fail.**

**Decoded:** This *is* their product. Thousands of backyard batteries, flaky LTE, a house that unplugs, a price feed that goes stale. They are not grading your Kubernetes YAML. They are grading: **heartbeat, timeout, rebalance, degraded mode.**

**Win this track:** kill 30% of the fleet **live in the demo** and show the remaining units pick up the dispatch target. Log the failure. Do not pretend the happy path is orchestration.

### 3. Most Commercializable

> Build something that could actually be a product. Name who it is for and what problem it solves.

**Decoded:** Not a science fair. **ICP + problem + why they pay.** Two buyers that matter to Base:

1. **Base themselves** (operator / installer / markets desk) — they hire you.
2. **Their homeowner** — trust + bill transparency (“why did my AC just die / why did the battery dump”).

**Win this track:** one sentence a VP of software would steal. “Homeowners don’t trust VPPs because the battery looks random. We print the receipt.”

---

## How they will score you (unofficial)

Judges are **Base engineers**, not VCs in the room as judges. They will ask:

1. Did you touch **real ERCOT data** or mock JSON?
2. Did anything **fail** on purpose?
3. Would I **use this Monday** (even as a prototype)?
4. Do you understand **nodal prices, 5-minute SCED, weather zones**, not just “batteries good”?

Generic LLM chatbot over a PDF of ERCOT’s about-page **loses**.

---

## Constraints for a 48h build

- No Base private API. Public ERCOT + simulated fleet.
- In-person. Demo on a projector. One laptop, one URL.
- Hiring > prize (no public prize pool on the Luma page). Build something that **looks like their stack**.
