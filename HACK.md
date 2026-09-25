# Remaining on-site plan (Sep 25–27, 2026)

**Hard deadline:** submissions due **Sunday Sep 27, 11:00 AM CT** (Airtable). Aim to submit by 10:30 AM.
**Office open:** Fri until 12:00 AM · Sat 8:00 AM–12:00 AM · Sun from 8:00 AM.

## Already done (branch `hackathon-build`)

- [x] Real ERCOT data with provenance, fair baselines, zone finding (`make report`)
- [x] Supervisor, heartbeats, reallocation, ALARM/degraded, chaos (kill, partition, stale feed, rogue, forged, replayed)
- [x] Desk: TTL, approve/reject/protect, auto-apply cap, fails closed on desk death
- [x] Signed commands with anti-replay; rogue SoC quarantine
- [x] Evidence export, one-command demo (`make demo`), benchmark (`make bench`)
- [x] Web UI with economics, live fleet, desk, member view (`make serve`)
- [x] README to the submission checklist; 31 tests

## Still to do

| When | Item | Why |
|---|---|---|
| Fri 7 PM–12 AM | Run `make setup test demo serve` on the demo laptop; fix anything environment-specific | Completeness |
| Sat 11 AM–1 PM | Base Office Hours: ask the questions in PROJECT.md | Track "Why", avoids invented claims |
| Sat PM | Apply office-hours feedback to the receipt wording and baseline; re-run `make report` and update the README numbers from its output | Fit, honesty |
| Sat evening | Rehearse the Loom script (`loom-script.md`, kept outside the repo) against the live UI | Everything is judged off the video |
| Sat ~11 PM | **Record the Loom** (camera on, 4:00–4:30) | Hard requirement |
| Sun 8–10 AM | Re-record if needed; fill in Airtable: title, video, repo link, screen capture, team roster, 150–300 word write-up; pick 2 tracks | Hard requirement |
| Sun ≤ 10:30 AM | **Submit** | Deadline 11:00 AM |

**Cut if behind:** UI polish, then extra chaos buttons. Never cut the tests, demo, README or Loom.
