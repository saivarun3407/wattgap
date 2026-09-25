# WattGap: project spec

This is the single source of truth for what WattGap is and why. [README.md](README.md) has the measured numbers and the run commands. This file merges the useful parts of the pre-event PRODUCT, PLAN and PRD 01–03 docs, which now live in [docs/archive](docs/archive).

## One sentence

WattGap turns real ERCOT prices into dispatch for a home-battery fleet that **keeps its commitments when units fail, never discharges without a live approval, never breaks a member's reserve, and can prove all of it**. Then it tells each member, in plain words, what their battery did.

## Tracks

Two, per the rules: **Orchestration** and **Most Commercializable**. **Open Grid Data** is the engine underneath (real ERCOT prices, fair-baseline economics, the zone-congestion finding), but we don't enter it.

| Track | What a judge sees |
|---|---|
| Orchestration | 400 (UI/demo) to 50,000 (benchmark) independent asyncio unit workers. Kill 30% of a zone and the MW is re-spread, or the supervisor raises ALARM and runs degraded. Partitions, stale feeds, rogue telemetry, forged or replayed commands, and a dead desk all fail safe. Everything is audited. |
| Most Commercializable | A member product for a power company: a per-home receipt built from the audited ledger, **Protect** as a one-tap guarantee enforced on the unit, and a monthly "what your battery did" statement on real prices. An operator desk and evidence pack for Base ops. |

## Who it's for

| User | Job | What WattGap gives them |
|---|---|---|
| Base fleet operator | Hit a MW commitment through flaky LTE and a changing fleet | Allocation with headroom, heartbeats, ALARM/degraded, desk approvals with TTL, evidence pack |
| Base member (homeowner) | "Did my battery keep my backup? What did it do and why?" | Receipt, reserve guarantee, Protect, monthly statement |
| Markets / analytics | "Where is the value by zone? What would a fixed schedule have made?" | Fair-baseline backtests on real days, zone spread during scarcity |

## Honest framing

We don't claim to beat Base's real dispatcher or to know how Base operates today. The fair baseline is a reasonable fixed schedule (charge overnight, discharge evenly 5–9 PM CT), not Base's policy. On the biggest scarcity day in our data the simple WattGap rule **loses** to that schedule (it sold too early). Over the 30 days of September 2023 it wins 25 days and $82.07/home. What we're showing is the *shape* of the hard problems (partial fleets, human gates, command integrity, member trust, proof) with working code, not a production control plane.

## Economics (econ.py)

- **Battery (assumed):** 40 kWh, 20 kW, 90% round trip (√0.9 per leg), $0.02/kWh wear on discharged energy, 20% member reserve never discharged, 15-minute intervals.
- **Policies:**
  - `naive_overnight` (reference only): charge 23:00–07:00 CT, never discharge.
  - `scheduled` (**fair baseline**): charge 00:00–06:00 CT, discharge evenly over 17:00–21:00 CT.
  - `wattgap`: charge when the zone price is in the cheapest 25% of the trailing 24 h. Discharge when it's in the top 10% and above breakeven. Causal; the prior day seeds the window.
- **Scoring:** energy cash minus wear, plus leftover energy valued at the day's median zone price, so no policy wins by selling its starting charge.
- **Reason text:** "system-wide" when the four-zone average is in its own top 10% (or cheapest 25%). "Zone congestion" when one zone sits at least max($20, 10%) away from that average.

## Orchestration (fleet.py, desk.py, security.py)

- **Workers:** one asyncio task per battery. Each verifies the signed command, applies it to its own battery (and enforces the reserve carried in the command), and replies with signed telemetry.
- **Supervisor, every tick:**
  1. Zone decisions from the policy.
  2. The stale feed check: HOLD everything if prices are stale.
  3. Submit an earn batch sized at 70% of healthy deliverable kW, if none is open.
  4. Allocate the live batch across healthy units in its zones, in proportion to headroom.
  5. Charge cheap zones.
  6. Send signed commands to healthy, suspect and dead units (so dead units can prove they're back).
  7. Collect replies until everyone answers or the wire is idle for 0.25 s.
  8. Verify signatures, check SoC against physics (quarantine on a > 2-point mismatch), update heartbeats (suspect, then dead after 2 misses, then recovered), and write one audit line.
- **ALARM** when healthy capacity can't cover the commitment, or when delivery fell short because units went silent.
- **Desk:**
  - Batch states: pending, auto, approved, rejected, expired, cancelled, done.
  - Earn commitments at or under 0.25 MW auto-apply, only while the desk is alive.
  - Pending batches expire on TTL. If the desk heartbeat is older than its timeout, every pending batch expires, and an expired batch can't be approved.
  - Protect cancels every pending or live earn batch and locks reserves at the current charge.
- **Security:**
  - Per-device key `HMAC-SHA256(fleet_secret, "device:<id>")`.
  - Messages carry `[device_id, body, nonce, ts]` plus a signature.
  - Rejected when outside ±30 s, on a reused nonce, or on a bad signature.
  - `WATTGAP_FLEET_SECRET` comes from the environment. If it's missing, an ephemeral dev secret is generated with a warning.

## Member product

- **Receipt**, per home per day, built from the ledger: value created, kWh sent, events with times and peak prices, and "your backup reserve never dropped below X%".
- **Protect** is a guarantee, not a setting: one tap, earning cancelled, reserve locked. The unit enforces it even if a bad command arrives.
- **Monthly statement** on real prices: value, what the fixed schedule would have made, kWh in and out, events, wear, lowest charge, best moment.
- **Wording.** We say "grid value your battery created", not "your bill credit". How value reaches a member is Base's plan, and we don't know it.

## Evidence (audit.py, export.py)

Append-only JSONL, one line per decision, approval, rejection, expiration, alarm, quarantine, security rejection, unit health change, chaos injection, and Protect. The export turns that into JSON plus a one-page HTML summary, including a `discharge_without_live_batch` count, which is 0 in every test and in the demo.

## Non-goals (this weekend)

Real Base API or hardware; ML or RL dispatch; letting an LLM choose megawatts; ancillary services and settlement; PJM; maps.

## Open questions for Base (office hours Sat 11 AM–1 PM)

1. What does a *fair* baseline look like against Base's current dispatch? Is a fixed evening window a reasonable stand-in?
2. How does grid value reach a member: a bill credit, a flat plan, or none? What language is Base comfortable putting on a receipt?
3. Would members want Protect per home before storms, and how would it interact with Base's own storm pre-charge?
4. Is committing a fixed fraction of healthy capacity (70%) with failure headroom close to how the fleet actually bids or commits?
