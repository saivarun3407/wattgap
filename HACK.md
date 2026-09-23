Canonical scope: [PROJECT.md](./PROJECT.md).

# 48h plan

Full product + track merge: see [PLAN.md](./PLAN.md) (FleetPulse Desk extends WattGap).

**Before Friday**

- [ ] Dump one **quiet day** + one **spike day** of ERCOT settlement prices (or GridStatus). Drop into `data/`. Keep `sample_prices.csv` as backup.
- [ ] Fix sample/replay so **naive overnight hours exist** in the series (today’s sample starts at noon → naive $ = 0).
- [ ] Optional: ERCOT public API key. Do not bet the demo on it.
- [ ] `python3 sim/run.py` works on a clean laptop.

**Hours 0–6** — scanner + $ gap  
Wire real CSV columns. Print top 10 opportunities. Naive vs aware $. **Sanity-check naive ≠ 0 on a full day.**

**Hours 6–14** — fleet MW target + failure  
Supervisor target MW; `kill_west`; rebalance remaining or ALARM. Log.

**Hours 14–22** — desk + TTL  
Pending batch → Approve / Reject / Protect. Kill desk → expire pending (no execute).

**Hours 22–30** — signed commands + rogue  
Per-device identity, nonce/replay guard, false SoC spoof → quarantine.

**Hours 30–38** — UI  
One page: price chart, WattGap $, opportunity list, fleet MW, kill + desk buttons, receipt panel.

**Hours 38–44** — export + ROI tab  
Compliance JSON/HTML from logs. One-zone replay $ for sales story.

**Hours 44–48** — freeze, 4-min script, sleep.

**Cut first:** map, PJM, live-only API, ML spike model, extra agents, second pages.
