# WattGap: project spec

This is the single source of truth for what WattGap is and why. [README.md](README.md) has the measured numbers and the run commands. This file merges the useful parts of the pre-event PRODUCT, PLAN and PRD 01–03 docs, which now live in [docs/archive](docs/archive).

## One sentence

WattGap plans a home-battery fleet on ERCOT's day-ahead prices, adjusts to real time, and **keeps its per-zone commitments when units fail, never discharges without a live approval, never breaks a member's reserve, and can prove all of it**. Then it tells each member, in plain words, what their battery did.

## Tracks

Two, per the rules: **Orchestration** and **Most Commercializable**. **Open Grid Data** is the engine underneath (real ERCOT prices, fair-baseline economics, the zone-congestion finding), but we don't enter it.

| Track | What a judge sees |
|---|---|
| Orchestration | 400 devices, each with its own ed25519 key, in-process or as 40 OS processes over localhost TCP (`make demo-net`, real `kill -9`). Per-zone commitments with 30% headroom: kill 30% of a zone and the MW is re-spread; if a zone can't cover, ALARM plus an audited re-commit. Partitions, stale feeds, rogue telemetry, forged, replayed or redirected commands, revoked keys and a dead desk all fail safe. Vectorized fleet math benchmarked to 1M units (5.2 ms median tick), the signed path to 100k in 8 shards. |
| Most Commercializable | A member app for a power company, not a battery company: first-run onboarding, a per-home receipt from the audited ledger, a monthly statement on real prices with home use netted out, a bill view with a flat / credit / none toggle clearly marked as an assumption, and **Protect** for storms as a one-tap guarantee enforced on the unit. An operator desk and evidence pack for Base ops. |

## Who it's for

| User | Job | What WattGap gives them |
|---|---|---|
| Base fleet operator | Hit a MW commitment through flaky LTE and a changing fleet | Allocation with headroom, heartbeats, ALARM/degraded, desk approvals with TTL, evidence pack |
| Base member (homeowner) | "Did my battery keep my backup? What did it do and why?" | Receipt, reserve guarantee, Protect, monthly statement |
| Markets / analytics | "Where is the value by zone? What would a fixed schedule have made?" | Fair-baseline backtests on real days, zone spread during scarcity |

## Honest framing

We don't claim to beat Base's real dispatcher or to know how Base operates today. The fair baseline is a reasonable fixed schedule (charge overnight, discharge evenly 5–9 PM CT), not Base's policy. The first WattGap rule (v1, trailing 24 h) **lost** $23.88/home on the biggest scarcity day because it sold too early. The day-ahead planner that replaced it wins that day by $47.28 and September 2023 by $195.49/home (29 of 30 days), with parameters chosen on July–August only. It still loses Sep 5 (−$4.31) and is flat on the quiet 2026 day (+$0.01, where v1 made +$0.78). One design change was informed by September, and [docs/PARAMS.md](docs/PARAMS.md) discloses it. What we're showing is the *shape* of the hard problems (partial fleets, human gates, command integrity, member trust, proof) with working code, not a production control plane.

## Economics (econ.py)

- **Battery (assumed):** 40 kWh, 20 kW, 90% round trip (√0.9 per leg), $0.02/kWh wear on discharged energy, 20% member reserve never discharged, 15-minute intervals.
- **Policies:**
  - `naive_overnight` (reference only): charge 23:00–07:00 CT, never discharge.
  - `scheduled` (**fair baseline**): charge 00:00–06:00 CT, discharge evenly over 17:00–21:00 CT.
  - `trailing` (**v1**, comparison row): charge in the cheapest 25% of the trailing 24 h, discharge in the top 10% when above breakeven.
  - `wattgap` (**day-ahead planner**): from that day's DAM prices (published ~13:00 CT the day before), discharge in the top `window_h` hours and charge in the cheapest 2 (refill time). Inside the discharge window, sell only while real time ≥ breakeven. Inside the charge window, buy only when real time ≤ planned sell × efficiency − wear. Outside the windows, sell at full power if real time ≥ `spike_mult` × max(top DAM, breakeven). Plan nothing if the DAM spread doesn't pay. `window_h=1`, `spike_mult=1.25`, chosen on 2023-07-02..08-31 (`make params`).
- **Home load:** ERCOT backcasted residential profile RESHIWR, average premise, by weather zone. Discharge is split into kWh to the home and kWh exported.
- **Scoring:** energy cash minus wear, plus leftover energy valued at the day's median zone price, so no policy wins by selling its starting charge.
- **Reason text:** "system-wide" when the four-zone average is in its own top 10% (or cheapest 25%). "Zone congestion" when one zone sits at least max($20, 10%) away from that average.

## Orchestration (fleet.py, desk.py, security.py)

- **Devices (`device.py`):** each holds its own ed25519 key, verifies the signed command (signature, time window, nonce, addressee), applies it to its own battery (enforcing the reserve carried in the command), and replies with signed telemetry including its home's load.
- **Transport (`transport.py`):** `LocalTransport` runs devices as asyncio tasks (tests, UI, `make demo`). `TcpTransport` starts `python -m wattgap.unithost` host processes, and each device opens its own localhost TCP connection (`make demo-net`). Killing a zone sends a real SIGKILL to the host processes.
- **Fleet math (`fleetmath.py`):** numpy arrays for SoC, reserve, state and zone. Headroom, per-zone proportional allocation, the physics check and heartbeat transitions have no per-unit Python loop.
- **Supervisor, every tick:**
  1. Zone decisions from the policy.
  2. The stale feed check: HOLD everything if prices are stale.
  3. Submit an earn batch with a **per-zone MW commitment**: 70% of what each zone's healthy units can sustain for the batch hour (30% headroom).
  4. Allocate each zone's MW across its healthy units in proportion to 15-minute headroom. If a zone is short, raise ALARM and **re-commit** that zone lower (audited, never raised).
  5. Charge cheap zones.
  6. Send signed commands to healthy, suspect and dead units (so dead units can prove they're back).
  7. Collect replies until everyone answers or the wire is idle for 0.25 s.
  8. Verify signatures, check SoC against physics (quarantine on a > 2-point mismatch), update heartbeats (suspect, then dead after 2 misses, then recovered), and write one audit line.
- **ALARM** when a zone's healthy capacity can't cover its commitment, or when delivery fell short because units went silent or failed checks.
- **Desk:**
  - Batch states: pending, auto, approved, rejected, expired, cancelled, done.
  - Earn commitments at or under 0.25 MW auto-apply, only while the desk is alive.
  - Pending batches expire on TTL. If the desk heartbeat is older than its timeout, every pending batch expires, and an expired batch can't be approved.
  - Protect cancels every pending or live earn batch and locks reserves at the current charge.
- **Security (`security.py`, ed25519 via `cryptography`):**
  - Each device generates its own keypair. The `Registry` enrolls a device only if it's on the roster, not revoked, and proves possession. It pins the first key, and a different key for a known ID is rejected.
  - Messages carry `[device_id, body, nonce, ts]` plus an ed25519 signature. They're rejected when outside ±30 s, on a reused nonce, on a bad signature, or when addressed to another device.
  - Revocation: the operator revokes a quarantined unit's key, and its telemetry is refused from then on.
  - `WATTGAP_SUPERVISOR_KEY` (a 64-hex ed25519 seed) comes from the environment. If it's missing, an ephemeral dev key is generated with a warning.

## Member product

- **Onboarding** on first run: two jobs (backup and grid), the 20% floor in hours of the home's average use, Protect, receipts.
- **Receipt**, per home per day, built from the ledger: value created, kWh to the home vs exported, events with times and peak prices, and "your backup reserve never dropped below X%".
- **Protect** is a guarantee, not a setting, and it's framed around storms and outages: one tap, earning cancelled, reserve locked at the current charge. The unit enforces it even if a bad command arrives. Operators have fleet-wide storm mode.
- **Monthly statement** on real prices: value, what the fixed schedule would have made, kWh in and out, home use, events, wear, lowest charge, backup hours.
- **Bill view.** A flat plan / bill credit / no bill link toggle under an "Assumption: we don't know Base's tariff" banner. The credit share is a slider the viewer moves.
- **Wording.** We say "grid value your battery created", not "your bill credit". How value reaches a member is Base's plan, and we don't know it.

## Evidence (audit.py, export.py)

Append-only JSONL, one line per decision, approval, rejection, expiration, alarm, zone re-commit, quarantine, key revocation, enrollment rejection, security rejection, unit health change, chaos injection, and Protect. The export turns that into JSON plus a one-page HTML summary, including a `discharge_without_live_batch` count, which is 0 in every test and in the demo.

## Non-goals (this weekend)

Real Base API or hardware; ML or RL dispatch or a price forecaster beyond the published DAM; letting an LLM choose megawatts; ancillary services and settlement; PJM; maps.

## Open questions for Base (office hours Sat 11 AM–1 PM)

1. What does a *fair* baseline look like against Base's current dispatch? Is a fixed evening window a reasonable stand-in?
2. How does grid value reach a member: a bill credit, a flat plan, or none? What language is Base comfortable putting on a receipt?
3. Would members want Protect per home before storms, and how would it interact with Base's own storm pre-charge?
4. Is committing a fixed fraction of healthy capacity (70%) per zone, with failure headroom and re-commit on shortfall, close to how the fleet actually bids or commits?
5. Does Base plan against the DAM today, and at what granularity (zone, node, hub)?
