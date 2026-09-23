# WattGap

**Find the money Base’s fleet is leaving on the table — then dispatch into it.**

Hackathon: [Base Power × AITX](https://luma.com/aitx-94j6) · Austin · Sep 25–27, 2026  
Tracks hit: **Open Grid Data** · **Orchestration** · **Most Commercializable**

Base already has the batteries. ERCOT already publishes 5-minute prices, load, fuel mix, outages. The gap is **seeing the next window** and **moving the fleet without falling over when nodes die**.

WattGap is that layer:

1. **Identify opportunities** — next SCED intervals where charging is cheap or discharging is expensive, using public ERCOT-shaped data.
2. **Measure inefficiency** — $ and MWh a naive “charge overnight” policy leaves vs a price-aware policy.
3. **Dispatch under failure** — many independent batteries; kill 30%; remaining units rebalance or alarm.

```
naive overnight charge     ──►  $X
price-aware + tight grid   ──►  $Y
WattGap                    ──►  Y − X   ← the number you put on the projector
```

## Who it is for

| User | Problem |
|---|---|
| Base VPP operator | “Which 5-minute windows should the fleet hit, and what if Houston LTE dies?” |
| Base markets intern | “How much $ did we miss yesterday by idling through a spike?” |
| Homeowner (trust) | “Why did my Core dump at 4:12pm?” → receipt from the same facts |

## Weekend demo (3 min)

1. Replay a **spike day** (CSV, not live API).
2. Show **WattGap $** vs naive.
3. Hit **Kill 30% of West**. Target MW rebalances or alarms. That’s orchestration.
4. Click one house → **receipt**. That’s the product.

Do **not** let an LLM pick megawatts. Rules dispatch. LLM may write the receipt from structured fields.

## Repo

| Path | What |
|---|---|
| [PRODUCT.md](./PRODUCT.md) | Spec, policy, meters |
| [HACK.md](./HACK.md) | 48h plan |
| [PLAN.md](./PLAN.md) | FleetPulse Desk — full track merge + schemas + demo |
| `sim/` | Runnable opportunity + fleet sim |
| `data/sample_prices.csv` | Fake ERCOT-like 5-min series (replace with real dump before the weekend) |

```bash
python3 sim/run.py
```

Prints identified opportunities, naive vs aware $, and a failure rebalance.
