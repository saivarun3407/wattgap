"""Signals: a real-time early warning that says HOLD, PRE-CHARGE or DISCHARGE-NOW every 5 minutes.

Inputs, all public and free:
  * NP6-970-CD  RTD indicative LMPs: every ~5 minutes ERCOT's real-time dispatch publishes indicative
    prices for each load zone for the next two hours (24 five-minute intervals).
  * NP6-323-CD  real-time price adders (RTRDPA, the reliability deployment price adder) per SCED run.
  * NP6-322-CD  SCED system lambda per run.
  * dashboards/daily-prc.json  physical responsive capability (PRC), MW, every ~10 s, today only.

Rule (per load zone, evaluated on the latest RTD run):
  DISCHARGE-NOW  the indicative price for the next 5-minute interval is at or above `discharge_at`
  PRE-CHARGE     any indicative price in the next `lookahead_min` (30) reaches `precharge_at`, or the
                 reliability adder reaches `adder_at`, or PRC is under `prc_low`: be full before it arrives
  HOLD           otherwise, and always when the feed is older than `stale_s` (fail safe)

A signal never dispatches anything by itself. DISCHARGE-NOW only proposes an earn batch to the desk,
which applies its usual approval rules.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
FEEDS = Path(__file__).resolve().parents[1] / "data" / "feeds"
HOLD, PRECHARGE, DISCHARGE = "HOLD", "PRE-CHARGE", "DISCHARGE-NOW"


@dataclass(frozen=True)
class WarnParams:
    discharge_at: float = 1000.0  # $/MWh, next-interval indicative price
    precharge_at: float = 500.0  # $/MWh, any indicative price in the next hour
    prc_low: float = 3000.0  # MW; ERCOT's EEA 1 trigger is PRC under 2,500 MW
    stale_s: float = 600.0  # a feed older than 10 minutes means HOLD
    lookahead_min: float = 30.0  # only trust RTD this far ahead: its far intervals run high (see look_ahead_bias)
    adder_at: float = 1.0  # $/MWh reliability deployment adder worth a PRE-CHARGE


@dataclass(frozen=True)
class Snapshot:
    """One RTD run plus the latest adder, lambda and PRC known at that moment."""

    at: datetime  # RTD run time (the feed's own timestamp)
    forward: dict[str, tuple[tuple[datetime, float], ...]]  # zone -> (interval ending, indicative LMP)
    adder: float = 0.0  # RTRDPA, $/MWh
    system_lambda: float = 0.0
    prc: float | None = None  # MW, only when a live dashboard read is available


@dataclass
class Signal:
    zone: str
    action: str
    at: datetime
    why: str
    feed_age_s: float = 0.0
    peak: float = 0.0  # highest indicative price inside the look-ahead
    extra: dict = field(default_factory=dict)


DEFAULT = WarnParams()


def signal(snap: Snapshot, zone: str, now: datetime, p: WarnParams = DEFAULT) -> Signal:
    age = (now - snap.at).total_seconds()
    if age > p.stale_s:
        return Signal(zone, HOLD, now, f"feed stale: RTD run is {age / 60:.0f} min old (limit {p.stale_s / 60:.0f})", age)
    fwd = tuple(x for x in snap.forward.get(zone, ()) if x[0] <= snap.at + timedelta(minutes=p.lookahead_min))
    if not fwd:
        return Signal(zone, HOLD, now, f"no RTD prices for {zone}", age)
    nxt = fwd[0][1]
    peak_t, peak = max(fwd, key=lambda x: x[1])
    if nxt >= p.discharge_at:
        return Signal(zone, DISCHARGE, now, f"RTD next interval ${nxt:,.0f}/MWh >= ${p.discharge_at:,.0f}", age, peak)
    why = []
    if peak >= p.precharge_at:
        why.append(f"RTD shows ${peak:,.0f}/MWh at {peak_t:%H:%M} CT")
    if snap.adder >= p.adder_at:
        why.append(f"reliability adder ${snap.adder:,.2f}/MWh")
    if snap.prc is not None and snap.prc < p.prc_low:
        why.append(f"PRC {snap.prc:,.0f} MW < {p.prc_low:,.0f}")
    if why:
        return Signal(zone, PRECHARGE, now, "; ".join(why), age, peak)
    return Signal(zone, HOLD, now, f"RTD next {p.lookahead_min:.0f} min peaks at ${peak:,.0f}/MWh", age, peak)


# ---------------------------------------------------------------- reading the feeds


def _t(s: str) -> datetime:
    return datetime.strptime(s, "%m/%d/%Y %H:%M:%S").replace(tzinfo=CT)


def _t_end(s: str) -> datetime:
    return datetime.strptime(s, "%m/%d/%Y %H:%M").replace(tzinfo=CT) if s.count(":") == 1 else _t(s)


def read_csv(name: str) -> list[dict]:
    with (FEEDS / name).open() as f:
        return list(csv.DictReader(f))


def snapshots(rtd: list[dict], adders: list[dict], lambdas: list[dict]) -> list[Snapshot]:
    """Join the feeds by time: each RTD run gets the latest adder and lambda posted at or before it."""
    runs: dict[datetime, dict[str, list]] = {}
    for r in rtd:
        runs.setdefault(_t(r["RTDTimestamp"]), {}).setdefault(r["SettlementPoint"], []).append(
            (_t_end(r["IntervalEnding"]), float(r["LMP"])))
    add = sorted((_t(r["SCEDTimestamp"]), float(r["RTRDPA"])) for r in adders)
    lam = sorted((_t(r["SCEDTimeStamp"]), float(r["CappedSystemLambda"])) for r in lambdas)
    out, ia, il = [], 0, 0
    for at in sorted(runs):
        while ia + 1 < len(add) and add[ia + 1][0] <= at:
            ia += 1
        while il + 1 < len(lam) and lam[il + 1][0] <= at:
            il += 1
        a = add[ia][1] if add and add[ia][0] <= at else 0.0
        lm = lam[il][1] if lam and lam[il][0] <= at else 0.0
        out.append(Snapshot(at, {z: tuple(sorted(v)) for z, v in runs[at].items()}, a, lm))
    return out


def settled(spp: list[dict]) -> dict[str, list[tuple[datetime, float]]]:
    """Settled 15-min load-zone prices from NP6-905-CD: zone -> [(interval start, $/MWh)]."""
    out: dict[str, list] = {}
    for r in spp:
        d = datetime.strptime(r["DeliveryDate"], "%m/%d/%Y").replace(tzinfo=CT)
        start = d + timedelta(hours=int(r["DeliveryHour"]) - 1, minutes=15 * (int(r["DeliveryInterval"]) - 1))
        out.setdefault(r["SettlementPointName"], []).append((start, float(r["SettlementPointPrice"])))
    return {z: sorted(v) for z, v in out.items()}


# ---------------------------------------------------------------- backtest


@dataclass
class Backtest:
    spike_at: float
    runs: int
    first: str
    last: str
    events: int  # spike episodes: runs of consecutive settled intervals at or above spike_at, per zone
    hits: int  # episodes warned (PRE-CHARGE or DISCHARGE-NOW) before the interval began
    lead_min: list[float]  # minutes from first warning (within the hour before) to episode start
    alarms: int  # warning episodes (consecutive warned runs per zone)
    false_alarms: int  # warning episodes with no settled spike in the following hour
    by_action: dict[str, int]

    @property
    def hit_rate(self) -> float | None:
        return self.hits / self.events if self.events else None

    @property
    def false_alarm_rate(self) -> float | None:
        return self.false_alarms / self.alarms if self.alarms else None


def backtest(snaps: list[Snapshot], prices: dict[str, list[tuple[datetime, float]]], spike_at: float,
             p: WarnParams, horizon: timedelta = timedelta(hours=1)) -> Backtest:
    """Replay every RTD run as if live (feed age 0) and score the signals against settled prices."""
    sig = {z: [(s.at, signal(s, z, s.at, p).action) for s in snaps] for z in prices}
    by_action = {HOLD: 0, PRECHARGE: 0, DISCHARGE: 0}
    events = hits = alarms = false = 0
    leads = []
    for z, series in prices.items():
        for _, a in sig[z]:
            by_action[a] += 1
        starts = [t for k, (t, v) in enumerate(series) if v >= spike_at and (k == 0 or series[k - 1][1] < spike_at)]
        spikes = [t for t, v in series if v >= spike_at]
        for t0 in starts:
            events += 1
            warned = [at for at, a in sig[z] if a != HOLD and t0 - horizon <= at < t0]
            if warned:
                hits += 1
                leads.append((t0 - min(warned)).total_seconds() / 60)
        prev = HOLD
        for at, a in sig[z]:
            if a != HOLD and prev == HOLD:
                alarms += 1
                if not any(at <= t < at + horizon for t in spikes):
                    false += 1
            prev = a
    return Backtest(spike_at, len(snaps), snaps[0].at.isoformat() if snaps else "", snaps[-1].at.isoformat() if snaps else "",
                    events, hits, leads, alarms, false, by_action)


def look_ahead_bias(snaps: list[Snapshot]) -> list[dict]:
    """How RTD's indicative price at each lead compares with the price the same interval got when it was
    next up (lead 1). One row per lead: mean and median error, and how often a >= $500 indication held."""
    now = {(z, f[0][0]): f[0][1] for s in snaps for z, f in s.forward.items() if f}
    rows = []
    for k in range(max((len(f) for s in snaps for f in s.forward.values()), default=0)):
        err, high, held = [], 0, 0
        for s in snaps:
            for z, f in s.forward.items():
                if k < len(f) and (z, f[k][0]) in now:
                    real = now[(z, f[k][0])]
                    err.append(f[k][1] - real)
                    if f[k][1] >= 500:
                        high += 1
                        held += real >= 500
        if err:
            err.sort()
            rows.append({"lead_min": 5 * (k + 1), "n": len(err), "mean_error": round(sum(err) / len(err), 2),
                         "median_error": round(err[len(err) // 2], 2), "indicated_500": high, "held_500": held})
    return rows


# ---------------------------------------------------------------- live poller and CLI

LIST = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId={}"
GET = "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={}"
PRC_URL = "https://www.ercot.com/api/1/services/read/dashboards/daily-prc.json"
REPORT_IDS = {"rtd": 13073, "adders": 13221, "lambda": 13114}
ZONES = ("LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST")
BACKTEST_FILE = Path(__file__).resolve().parents[1] / "data" / "derived" / "warn_backtest.json"


def _get(url: str) -> bytes:  # pragma: no cover - network
    import urllib.request
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def _latest(rid: int) -> list[dict]:  # pragma: no cover - network
    import io
    import json
    import zipfile
    docs = json.loads(_get(LIST.format(rid)))["ListDocsByRptTypeRes"]["DocumentList"]
    doc = max((d["Document"] for d in docs if "_csv" in d["Document"]["FriendlyName"]), key=lambda d: d["PublishDate"])
    z = zipfile.ZipFile(io.BytesIO(_get(GET.format(doc["DocID"]))))
    return list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode())))


def live_snapshot() -> Snapshot:  # pragma: no cover - network
    import json
    rtd = [r for r in _latest(REPORT_IDS["rtd"]) if r["SettlementPoint"] in ZONES]
    snap = snapshots(rtd, _latest(REPORT_IDS["adders"]), _latest(REPORT_IDS["lambda"]))[-1]
    prc = json.loads(_get(PRC_URL))["current_condition"]["prc_value"]
    return Snapshot(snap.at, snap.forward, snap.adder, snap.system_lambda, float(str(prc).replace(",", "")))


def run_backtest() -> dict:
    """Backtest on every RTD run MIS still holds, against settled NP6-905-CD prices over the same window."""
    snaps = snapshots(read_csv("rtd.csv"), read_csv("adders.csv"), read_csv("lambda.csv"))
    first, last = snaps[0].at + timedelta(hours=1), snaps[-1].at
    prices = {z: [x for x in v if first <= x[0] <= last] for z, v in settled(read_csv("spp.csv")).items()}
    cases = []
    for spike_at, pre in ((1000.0, 500.0), (200.0, 200.0), (100.0, 100.0)):
        b = backtest(snaps, prices, spike_at, WarnParams(spike_at, pre))
        lead = sorted(b.lead_min)
        cases.append({"spike_at": spike_at, "precharge_at": pre, "events": b.events, "hits": b.hits,
                      "median_lead_min": round(lead[len(lead) // 2], 1) if lead else None,
                      "alarms": b.alarms, "false_alarms": b.false_alarms, "zone_runs": b.by_action})
    return {"rtd_runs": len(snaps), "first_run": snaps[0].at.isoformat(), "last_run": snaps[-1].at.isoformat(),
            "settled_intervals_per_zone": len(next(iter(prices.values()))),
            "max_settled": {z: max(v for _, v in xs) for z, xs in prices.items()},
            "cases": cases, "look_ahead_bias": look_ahead_bias(snaps)}


def main(argv: list[str]) -> None:  # pragma: no cover - CLI
    import json
    import time
    if "--live" in argv:
        while True:
            snap = live_snapshot()
            now = datetime.now(CT)
            for z in ZONES:
                s = signal(snap, z, now)
                print(f"{now:%H:%M:%S} CT  {z:<11} {s.action:<13} feed {s.feed_age_s:4.0f} s old  {s.why}", flush=True)
            if "--once" in argv:
                return
            time.sleep(300)
    out = run_backtest()
    BACKTEST_FILE.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "look_ahead_bias"}, indent=1))
    print("lead_min  n  mean_error  median_error  indicated>=500  held>=500")
    for r in out["look_ahead_bias"][::3]:
        print(f"{r['lead_min']:>8} {r['n']:>5} {r['mean_error']:>10} {r['median_error']:>12} {r['indicated_500']:>14} {r['held_500']:>9}")


if __name__ == "__main__":  # pragma: no cover
    import sys
    main(sys.argv[1:])
