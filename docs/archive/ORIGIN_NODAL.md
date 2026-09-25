> **Archived, pre-event planning (Sep 23, 2026). Not a description of the shipped code.** Dollar figures, uplift percentages and claims about Base here were never computed or verified. See [README](../../README.md) and [PROJECT.md](../../PROJECT.md) for what is real.

# NODAL — the one idea

**Tagline:** The dispatcher that tells a backyard battery fleet when to fire — and tells the homeowner why.

**Tracks:** Open Grid Data + Orchestration + Most Commercializable (one demo, three boxes checked).

---

## Why this one

Base Power’s company *is* a virtual power plant made of ~40 kWh home batteries. ERCOT reprices **every 5 minutes** (SCED). A battery that charges through a $2,000/MWh spike or sits idle through a negative-price wind dump is leaving money and reliability on the table. Public data exists. Almost nobody turns it into **orders** plus a **receipt**.

Generic energy dashboards will flood **Open Grid Data**. Kubernetes-for-fun will flood **Orchestration**. Random SaaS will flood **Commercializable**. Nodal is the thing in the middle that looks like **Monday morning at Base**.

---

## Who it is for (say this in the first 20 seconds)

| User | Job | Why they pay / care |
|---|---|---|
| **VPP operator (Base)** | Hit a MW target this interval without cooking batteries or the home | Fleet that survives dead nodes and stale prices |
| **Homeowner (Base customer)** | “Why did my battery dump at 4:12pm?” | Trust. VPPs die on “the battery did something weird.” |
| **Markets / intern** | Replay yesterday’s spike | Training + post-mortem |

Hackathon buyer is **Base**. Homeowner view is why **Commercializable** is not fake.

---

## What it does

1. **Ingest** public ERCOT: real-time (or delayed) settlement point prices by hub/zone, system load, fuel mix, outage capacity. Refresh on a timer.
2. **Simulate** a fleet of N Base-like batteries (start N=50) pinned to weather zones / load zones (Houston, North, South, West, Austin-ish). Each unit: 40 kWh, 20 kW, SOC, online/offline, last heartbeat.
3. **Decide** every interval: `CHARGE` | `HOLD` | `DISCHARGE` per unit, under a fleet MW target (e.g. “discharge 2 MW for 15 min”).
4. **Fail:** randomly or on a big red button — drop comms, freeze SOC telemetry, stale price feed (>2 intervals old → HOLD). Remaining online units **rebalance** to still hit the target if possible, else **degrade** (partial MW + alarm).
5. **Show two screens:**
   - **Operator:** map/list of units, target vs actual MW, failures, $ this hour vs naive “charge 11pm–7am.”
   - **Homeowner receipt:** “Your Core in Houston discharged 8.2 kWh from 16:10–16:25 because LZ_HOUSTON hit $412/MWh and West Texas wind dropped 3 GW. Estimated bill credit: $X.”

That receipt is the product. The dispatcher is the engineering.

---

## Policy (keep it dumb enough to finish)

Weekend v1 — no ML:

```
if price_feed_stale or unit.offline:
    HOLD
elif price <= p20(last_24h_zone) and SOC < 0.9:
    CHARGE  (up to 20 kW)
elif price >= p80(last_24h_zone) and SOC > 0.2 and grid_tight:
    DISCHARGE
else:
    HOLD
```

`grid_tight` = load > 90% of 7-day max **or** fuel mix wind+solar collapsing vs load **or** reserves proxy from public dashboards.

Naive baseline: charge nights, ignore prices. Show **$ delta** on the operator screen. That is the Open Grid Data “useful.”

---

## Orchestration (the part they grade)

Each battery is a **worker** with:

- heartbeat (miss 2 → offline)
- command inbox
- SOC that only updates if online
- max cycles/day (refuse discharge if already dumped twice)

**Supervisor:**

- publishes interval tick (wall clock or replay clock)
- assigns commands
- if online_capacity < target: scale remaining units to max kW, then ALARM
- if price feed fails: freeze last good, HOLD, banner “degraded: stale SCED”

**Demo kill switch:** “Kill West Texas LTE.” 30% of West units drop. Chart shows target still met from Houston/North **or** honest miss + alarm. Do **not** fake a perfect recover if physics says no.

---

## 48-hour plan

### Before Friday (now)

- [ ] Apply on Luma if you might attend.
- [ ] Register ERCOT public API key **or** download 48h of GridStatus/ERCOT CSVs (one boring day + one spike day). **Do not depend on live API for the demo.** Replay is more reliable on a projector.
- [ ] Pick stack: Next.js + Python worker, or single FastAPI + HTMX. One language if solo.

### Hours 0–4

- Replay clock over CSV: 5-min ticks.
- 50 units, random SOC, zone assignment.
- Policy v0 running, log actions.

### Hours 4–12

- Operator UI: table + 3 charts (price, fleet MW, online %).
- Failure injection button.
- Naive vs Nodal $ counter.

### Hours 12–24

- Homeowner receipt for **one** unit (the story).
- Fuel mix + load as the “why” sentence.
- Degraded-mode banner.

### Hours 24–36

- Polish demo script. Record 90s backup video.
- One-pager: ICP, problem, what Base would do with this Monday.

### Hours 36–48

- Freeze. Practice kill-switch live. Sleep.

**Cut if behind:** map, ML, real-time API, Discord bot, mobile. Keep replay + kill + receipt.

---

## Demo script (3 minutes)

1. “ERCOT prices every 5 minutes. Base’s product is a fleet of 40 kWh Cores. Public data is unused. We turn it into orders.”
2. Replay **heat-day** prices. Fleet discharges into the spike. $ vs naive.
3. **Kill 30%.** Watch rebalance or alarm. “This is the job: not the happy path.”
4. Click one house. **Receipt.** “That’s why the customer doesn’t churn.”
5. “Tracks: real ERCOT data, workers that fail, product for operator + homeowner.”

---

## Stack (suggested)

```
data/          spike-day + quiet-day CSVs (prices, load, mix)
sim/           units, ticks, policy, supervisor
web/           operator + receipt
README         how to run replay
```

No GPU. No Base private API. Optional: ERCOT live if the key works; always have replay.

---

## What not to call it

Not “AI VPP.” Policy is rules. An LLM can **write the receipt sentence** from structured facts — that’s fine. Do not let an LLM **dispatch MW**. Base already said they don’t trust probabilistic models to send a truck to the wrong house; they will not want GPT choosing discharge.

---

## Stretch (only if core is done)

- Bind to **named constraints** / congestion (West vs Houston spread).
- Install-ops cousin: “don’t dispatch a unit that’s mid-install” (fake work-order flag).
- PJM overlay for Illinois story (they just entered). Weekend: Texas only.

---

## Why this hires you

You demonstrated: public market data, distributed systems failure, and a customer-trust surface. That is Base’s software org in miniature.
