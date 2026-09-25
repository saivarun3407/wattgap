"use strict";
const $ = id => document.getElementById(id);
const Z = ["LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH", "LZ_WEST"];
const COLOR = {LZ_HOUSTON: "var(--hou)", LZ_NORTH: "var(--nor)", LZ_SOUTH: "var(--sou)", LZ_WEST: "var(--wes)"};
const HOME_ZONE = "LZ_HOUSTON";
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const money = (v, d = 2) => (v < 0 ? "−$" : "$") + Math.abs(v).toLocaleString("en-US", {minimumFractionDigits: d, maximumFractionDigits: d});
const signed = (v, d = 2) => (v >= 0 ? "+" : "") + money(v, d);
const nice = z => z.replace("LZ_", "").toLowerCase().replace(/^./, c => c.toUpperCase());
const hhmm = iso => iso.slice(11, 16);
const pct = v => Math.round(v * 100) + "%";
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

let E = null, S = null, day = "spike", prev = {};

async function post(url) {
  const r = await fetch(url, {method: "POST"});
  if (!r.ok) console.warn(url, r.status);
  await refresh();
}

/* ---------- number motion ---------- */
function setNum(el, value, digits = 2) {
  const from = parseFloat(el.dataset.v ?? value), to = value;
  el.dataset.v = to;
  if (reduced || from === to) { el.textContent = to.toFixed(digits); return; }
  const t0 = performance.now();
  const step = t => {
    const k = Math.min(1, (t - t0) / 500), e = 1 - Math.pow(1 - k, 3);
    el.textContent = (from + (to - from) * e).toFixed(digits);
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
function flash(el) { el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); }

/* ---------- charts ---------- */
const X0 = 44, W = 820;
const xAt = (i, n) => X0 + i * (W - X0 - 10) / (n - 1);
function yAt(v, h, min, max) { return h - 20 - (v - min) / ((max - min) || 1) * (h - 36); }
function line(vals, h, min, max, color, width = 2, dash = "") {
  const pts = vals.map((v, i) => `${xAt(i, vals.length).toFixed(1)},${yAt(v, h, min, max).toFixed(1)}`).join(" ");
  return `<polyline fill="none" stroke="${color}" stroke-width="${width}" stroke-linejoin="round" stroke-dasharray="${dash}" points="${pts}"/>`;
}
function axis(h, min, max, fmt, labels) {
  let g = "";
  for (let k = 0; k <= 3; k++) {
    const v = min + (max - min) * k / 3, y = yAt(v, h, min, max);
    g += `<line x1="${X0}" x2="${W - 10}" y1="${y}" y2="${y}" stroke="#eef0f4"/><text x="0" y="${y + 4}">${fmt(v)}</text>`;
  }
  labels.forEach((t, i) => { if (i % 16 === 0) g += `<text x="${xAt(i, labels.length) - 13}" y="${h - 3}">${t}</text>`; });
  return g;
}
function band(hStart, hEnd, h, fill) {  // CT hours -> 96-interval x range
  const a = xAt(hStart * 4, 96), b = xAt(Math.min(95, hEnd * 4), 96);
  return `<rect x="${a}" y="8" width="${b - a}" height="${h - 28}" fill="${fill}"/>`;
}

/* ---------- hero ---------- */
function renderKpis() {
  const m = E.month, s = E.days.spike, q = E.days.quiet, z = E.zone_finding;
  const k = (label, v, sub, was) => `<div class="kpi"><div class="l">${label}</div><div class="v ${v >= 0 ? "pos" : "neg"}">${signed(v)}</div><div class="s">${sub}</div>${was ? `<span class="was">${was}</span>` : ""}</div>`;
  $("kpis").innerHTML =
    k("vs fair schedule · Sep 2023, 30 real days", m.gap_vs_fair,
      `${money(m.per_home.wattgap)} vs ${money(m.per_home.scheduled)} per home · won ${m.days_won}/${m.days} days`,
      `v1 (trailing 24 h): ${signed(m.v1_gap_vs_fair)} · ${m.v1_days_won}/${m.days}`) +
    k(`Scarcity day · ${s.day}`, s.gap_vs_fair, `${money(s.per_home.wattgap)} vs ${money(s.per_home.scheduled)} per home`,
      `v1: ${signed(s.per_home.trailing - s.per_home.scheduled)} (sold too early)`) +
    k(`Quiet day · ${q.day}`, q.gap_vs_fair, `${money(q.per_home.wattgap)} vs ${money(q.per_home.scheduled)} per home`,
      `v1: ${signed(q.per_home.trailing - q.per_home.scheduled)}`) +
    `<div class="kpi"><div class="l">Zone finding · ${s.day} scarcity</div><div class="v neg">${money(z.LZ_SOUTH.avg_vs_system, 0)}</div>
     <div class="s">LZ_SOUTH vs the 4-zone average over ${z.intervals} intervals ≥ $1,000/MWh (worst ${money(z.LZ_SOUTH.worst, 0)}/MWh)</div>
     <span class="was">parameters picked on Jul–Aug 2023 only</span></div>`;
}

/* ---------- real days ---------- */
function renderDay() {
  const d = E.days[day], P = d.prices, t = P.map(p => p.t), L = E.labels;
  $("daySeg").innerHTML = Object.entries(E.days).map(([k, v]) =>
    `<button role="tab" aria-selected="${k === day}" data-day="${k}">${k === "spike" ? "Scarcity" : "Quiet"} · ${v.day}</button>`).join("");
  const dam96 = d.dam[HOME_ZONE].flatMap(v => [v, v, v, v]);
  const all = [...P.flatMap(p => Z.map(z => p[z])), ...dam96], max = Math.max(...all), min = Math.min(0, ...all);
  const plan = d.plan[HOME_ZONE];
  const hatch = `<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="3" height="6" fill="#eef0f4"/></pattern></defs>`;
  const bands = h => band(17, 21, h, "url(#hatch)") + plan.discharge.map(hr => band(hr, hr + 1, h, "#ffe2cc")).join("");
  $("priceChart").innerHTML = hatch + bands(240) + axis(240, min, max, v => "$" + Math.round(v).toLocaleString(), t) +
    Z.map(z => line(P.map(p => p[z]), 240, min, max, COLOR[z], 1.8)).join("") + line(dam96, 240, min, max, "var(--hou)", 1.5, "5 4");
  const floorY = yAt(0.2, 130, 0, 1);
  $("socChart").innerHTML = hatch + bands(130) + axis(130, 0, 1, v => pct(v), t) +
    line(d.soc.scheduled, 130, 0, 1, "#9aa3b5", 2) + line(d.soc.trailing, 130, 0, 1, "var(--violet)", 1.6, "4 3") +
    line(d.soc.wattgap, 130, 0, 1, "var(--amber)", 2.6) +
    `<line x1="${X0}" x2="${W - 10}" y1="${floorY}" y2="${floorY}" stroke="var(--red)" stroke-dasharray="4 4"/><text x="${W - 118}" y="${floorY - 5}" style="fill:var(--red)">20% member reserve</text>`;
  const pols = ["scheduled", "trailing", "wattgap"];
  const head = `<tr><th>Zone</th><th>Fair</th><th>v1</th><th>WattGap</th><th>vs fair</th></tr>`;
  const rowOf = (name, vals, bold) => {
    const g = vals.wattgap - vals.scheduled;
    return `<tr class="${bold ? "hl" : ""}"><td>${bold ? "<b>" + name + "</b>" : name}</td>${pols.map(p => `<td>${p === "wattgap" ? "<b>" + money(vals[p]) + "</b>" : money(vals[p])}</td>`).join("")}<td class="${g >= 0 ? "pos" : "neg"}"><b>${signed(g)}</b></td></tr>`;
  };
  $("zoneTable").innerHTML = head + Z.map(z => rowOf(nice(z), Object.fromEntries(pols.map(p => [p, d.by_zone[z][p].net])))).join("") +
    rowOf("Avg home", d.per_home, true) +
    `<tr><td class="mute small" colspan="5">Naive overnight (charges, never sells): ${money(d.per_home.naive_overnight)} per home</td></tr>`;
  const hz = d.by_zone[HOME_ZONE].wattgap, a = E.assumptions;
  const ev = E.members[HOME_ZONE].spike_day.events;
  const story = day === "spike"
    ? `<p><b>Why WattGap wins here, when v1 lost.</b> v1 sold at 13:45 CT, the first time prices hit its trailing top 10%, and sat at its reserve through the 18:30–19:30 peak. The day-ahead plan, published the afternoon before, marked ${plan.discharge.map(h => h + ":00").join(", ")} CT as Houston's top hour. When real time ran more than ${a.planner.spike_mult}× that day-ahead peak, it sold into the spike instead: ${ev.map(e => `${hhmm(e.start)}–${hhmm(e.end)} CT, up to $${Math.round(e.peak_price).toLocaleString()}/MWh`).join("; ")}.</p>`
    : `<p><b>Quiet day.</b> Small spreads, so after 90% round-trip losses and $${a.degradation_per_kwh}/kWh of wear there's almost nothing to earn. WattGap and the fixed schedule tie, and v1 did slightly better by cycling on intraday noise. We show that too.</p>`;
  $("dayWhy").innerHTML = story +
    `<p class="mute small">Houston home, this day: ${hz.kwh_out} kWh discharged, of which ${hz.kwh_to_home} kWh powered the home itself and ${hz.kwh_exported} kWh was exported (ERCOT residential load profile). Planner: discharge in the top ${a.planner.window_h} day-ahead hour, charge in the cheapest ${a.refill_hours}. Parameters were picked on ${a.selection_days} only, and ${a.evaluation_days} was never used to choose them.</p>`;
}

/* ---------- live fleet ---------- */
function renderLive() {
  const s = S, l = s.last || {}, zt = l.zone_target_mw || {}, zd = l.zone_delivered_mw || {};
  $("clock").textContent = `${s.interval.slice(0, 10)} · ${hhmm(s.interval)} CT`;
  $("prices").textContent = Z.map(z => `${nice(z)} $${Math.round(s.prices[z]).toLocaleString()}`).join(" · ") + " /MWh";
  setNum($("target"), l.target_mw || 0); setNum($("delivered"), l.delivered_mw || 0); setNum($("export"), l.export_mw || 0);
  setNum($("healthy"), l.healthy ?? 0, 0); $("total").textContent = `of ${l.total ?? "—"} units`;
  const met = l.target_mw > 0 && !l.alarm;
  if (prev.alarm && met) { flash($("delivered")); document.querySelectorAll(".zone").forEach(flash); }
  const key = (l.alarm || "") + "|" + (l.degraded || []).join("|") + "|" + (met ? l.batch : "");
  if (key !== prev.statusKey) {
    $("status").innerHTML = (l.alarm ? `<div class="banner alarm"><span aria-hidden="true">⚠</span><span>${esc(l.alarm)}</span></div>`
      : met ? `<div class="banner ok"><span aria-hidden="true">✓</span><span>Every zone commitment met: ${l.delivered_mw.toFixed(2)} MW from ${l.healthy} healthy units · batch ${l.batch}</span></div>` : "") +
      (l.degraded || []).map(d => `<div class="banner deg">Degraded · ${esc(d)}</div>`).join("");
    prev.statusKey = key;
  }
  prev.alarm = !!l.alarm;
  const H = s.history, mx = Math.max(0.5, ...H.map(h => Math.max(h.target, h.delivered)));
  $("spark").innerHTML = H.length > 1 ? line(H.map(h => h.target), 64, 0, mx, "#9aa3b5", 1.5, "4 3") + line(H.map(h => h.delivered), 64, 0, mx, "var(--amber)", 2.4) +
    H.map((h, i) => h.alarm ? `<circle cx="${xAt(i, H.length)}" cy="9" r="3.5" fill="var(--red)"/>` : "").join("") + `<text x="0" y="12">MW</text>` : "";
  const zmax = Math.max(0.01, ...Object.values(zt), ...Object.values(zd));
  $("zones").innerHTML = Z.map(z => {
    const units = s.fleet.units.filter(x => x.zone === z), c = s.fleet.by_zone[z], t = zt[z] || 0, dv = zd[z] || 0;
    const short = t > 0 && dv + 1e-6 < t;
    return `<div class="zone${short ? " short" : ""}"><h4><span style="color:${COLOR[z]}">● ${nice(z)}</span><span>${c.healthy || 0}/${units.length}</span></h4>
      <div class="zmeta">${t ? `${dv.toFixed(2)} of ${t.toFixed(2)} MW committed` : "no commitment"}</div>
      <div class="zbar" title="delivered vs committed"><i style="width:${dv / zmax * 100}%"></i>${t ? `<u style="left:${t / zmax * 100}%"></u>` : ""}</div>
      <div class="dots">${units.map(x => `<div class="dot ${x.state === "healthy" ? x.action : x.state}" title="${x.id} · ${x.state} · SoC ${pct(x.soc)}"></div>`).join("")}</div></div>`;
  }).join("");
  $("play").textContent = s.playing ? "Pause" : "Play";
  $("deskState").className = "st " + (s.desk_alive ? "online" : "offline");
  $("deskState").textContent = s.desk_alive ? "desk online" : "desk offline";
  $("deskBtn").textContent = s.desk_alive ? "Kill desk" : "Revive desk";
  $("stormBtn").textContent = s.fleet.protected ? "End storm mode" : "Storm mode: Protect all";
  renderDesk(); renderFeed();
}

function renderDesk() {
  const ttl = S.desk_ttl_s;
  $("desk").innerHTML = S.desk.slice(0, 5).map(b => `<div class="batch ${b.status}"><div class="row"><span class="id">${b.id}</span>
    <span class="mute small">${b.kind} · ${b.target_mw.toFixed(2)} MW</span><span class="sp"></span><span class="st ${b.status}">${b.status}</span></div>
    ${Object.keys(b.zone_mw).length ? `<div class="zmw">${Object.entries(b.zone_mw).map(([z, mw]) => `${nice(z)} ${mw.toFixed(2)}`).join(" · ")} MW</div>` : ""}
    ${b.status === "pending" ? `<div class="ttl" role="progressbar" aria-label="time left to approve" aria-valuemin="0" aria-valuemax="${ttl}" aria-valuenow="${Math.ceil(b.ttl_left_s)}"><i style="width:${Math.min(100, b.ttl_left_s / ttl * 100)}%"></i></div>
      <div class="row"><span class="mute small">expires in ${Math.ceil(b.ttl_left_s)} s</span><span class="sp"></span><button class="btn" data-post="/api/desk/${b.id}/reject">Reject</button><button class="btn go" data-post="/api/desk/${b.id}/approve">Approve</button></div>`
      : `<div class="mute small" style="margin-top:4px">${b.decided_by ? `by ${b.decided_by}` : ""}${b.ticks_run ? ` · ran ${b.ticks_run}/${b.ticks} ticks` : ""}</div>`}
    <div class="mute small" style="margin-top:4px">${esc(b.reason)}</div></div>`).join("") || `<div class="mute small">No batches yet. The planner asks when prices justify it.</div>`;
}

function renderFeed() {
  const cls = k => /quarant|rejected|dead|expired|kill|forged|replayed|redirected|rogue|broken|revoked/.test(k) ? "bad"
    : /approved|recovered|healed|revived|enrolled/.test(k) ? "good" : /suspect|partition|stale|protect|recommit/.test(k) ? "warn" : "";
  const rows = [];
  for (const e of S.audit.slice().reverse().filter(e => e.kind !== "dispatch" || e.alarm)) {
    const last = rows[rows.length - 1];
    if (last && last.kind === e.kind && /^unit_(suspect|dead|recovered)$/.test(e.kind)) { last.n++; continue; }
    rows.push({...e, n: 1});
  }
  const txt = e => e.n > 1 ? `×${e.n} (${e.unit} …)` : [e.batch || e.unit || e.zone || "",
    e.why || e.alarm || (e.reported_soc !== undefined ? `SoC ${e.reported_soc} vs physics ${e.physics_soc}` : "") ||
    (e.to_mw !== undefined ? `${e.zone} ${e.from_mw} → ${e.to_mw} MW` : "")].join(" ");
  $("feed").innerHTML = rows.slice(0, 50).map(e => `<div class="${cls(e.kind)}">#${e.seq} ${esc(e.actor)} ${e.kind} ${esc(txt(e))}</div>`).join("");
}

/* ---------- member app ---------- */
const member = () => E.members[HOME_ZONE];
function renderHomeLive() {
  const h = S.home, m = member();
  const doing = h.state !== "healthy" ? `offline (${h.state})` : h.action === "DISCHARGE" ? `helping the grid · ${h.kw.toFixed(1)} kW` : h.action === "CHARGE" ? `charging from cheap power · ${(-h.kw).toFixed(1)} kW` : "holding charge";
  const hours = (h.soc * 40 * Math.sqrt(0.9)) / m.avg_home_kw;
  $("liveHome").innerHTML = `<div class="ring" style="--p:${Math.round(h.soc * 100)}"><span>${pct(h.soc)}</span></div>
    <div><b>Right now:</b> ${doing}<div class="mute small">Backup floor ${pct(h.reserve)}${h.protected ? " · Protect on" : ""} · about ${hours.toFixed(1)} h of your average use stored</div></div>`;
  const t = $("protectToggle");
  if (t) { t.setAttribute("aria-checked", h.protected); t.closest(".shield").classList.toggle("on", h.protected); $("protectState").textContent = h.protected ? "On. Earning is paused for your home and your backup is locked at " + pct(h.reserve) + "." : "Off. Your battery can help the grid, but it never goes below " + pct(0.2) + "."; }
}

function renderToday() {
  const m = member(), sd = m.spike_day, ev = sd.events, kwh = ev.reduce((a, e) => a + e.kwh, 0);
  $("tab-today").innerHTML = `<div class="receipt"><div class="lbl">Receipt · Wed, Sep 6, 2023 · ERCOT emergency evening</div>
    <div class="v">${money(sd.net)}</div><div>of grid value from your battery, after losses and wear.</div>
    ${ev.map(e => `<div class="ev"><span>${hhmm(e.start)}–${hhmm(e.end)} CT</span><span>${e.kwh.toFixed(1)} kWh · up to $${Math.round(e.peak_price).toLocaleString()}/MWh</span></div>`).join("")}
    <div class="check">✓ Your backup reserve never dropped below ${pct(sd.min_soc)}.</div></div>
    <p class="small mute">Why then? ${esc(ev[0] ? ev[0].reason : "")}. Your battery sent ${kwh.toFixed(1)} kWh while Texas was short on power.</p>`;
}

function renderMonth() {
  const m = member(), top = m.top_event;
  $("tab-month").innerHTML = `<div class="lbl">September 2023 · real ERCOT prices</div><div class="bigline">${money(m.net_value)}</div>
    <div class="small mute" style="margin-bottom:8px">grid value your battery created · a fixed evening schedule would have made ${money(m.fair_schedule_value)}</div>
    <div class="stmt">
      <div><span>Energy sent during ${m.events} grid events</span><b>${m.kwh_out.toFixed(0)} kWh</b></div>
      <div><span>…of that, powered your own home</span><b>${m.kwh_to_home.toFixed(0)} kWh</b></div>
      <div><span>…exported past your meter</span><b>${m.kwh_exported.toFixed(0)} kWh</b></div>
      <div><span>Stored from the cheapest hours</span><b>${m.kwh_in.toFixed(0)} kWh</b></div>
      <div><span>Your home used (ERCOT profile)</span><b>${m.home_kwh_month.toFixed(0)} kWh</b></div>
      <div><span>Battery wear accounted for</span><b>${money(m.wear)}</b></div>
      <div><span>Lowest charge all month</span><b>${pct(m.min_soc)} (floor ${pct(m.reserve_soc)})</b></div>
      <div><span>Best moment</span><b>Sep ${+top.start.slice(8, 10)}, ${hhmm(top.start)} CT · ${money(top.value)}</b></div>
    </div>`;
}

let billMode = "flat", creditShare = 50;
function renderBill() {
  const m = member(), v = m.net_value;
  const modes = {flat: "Flat plan", credit: "Bill credit", none: "No bill link"};
  const body = {
    flat: `<div class="bigline">$0.00</div><div class="small">change to your bill from dispatch. On a flat plan, the ${money(v)} of grid value goes toward the cost of running the plan, and you keep the backup, Protect and the receipts.</div>`,
    credit: `<label class="lbl" for="share">Illustrative credit share: <b id="shareV">${creditShare}%</b></label>
      <input class="range" id="share" type="range" min="0" max="100" step="5" value="${creditShare}">
      <div class="bigline">${money(v * creditShare / 100)}</div><div class="small">= ${creditShare}% × ${money(v)} of grid value created in September 2023. The share is yours to move. It's not Base's number.</div>`,
    none: `<div class="bigline">${money(v)}</div><div class="small">of grid value your battery created in September 2023, shown on its own without any claim about your bill.</div>`,
  };
  $("tab-bill").innerHTML = `<div class="seg" role="radiogroup" aria-label="How grid value reaches the bill">${Object.entries(modes).map(([k, l]) =>
      `<button role="radio" aria-selected="${k === billMode}" aria-checked="${k === billMode}" data-bill="${k}">${l}</button>`).join("")}</div>
    <div class="assume"><b>Assumption:</b> we don't know Base's tariff. These are three possible designs, not Base's terms. The ${money(v)} grid value is computed; any bill impact is illustrative.</div>
    ${body[billMode]}
    <div class="stmt" style="margin-top:12px"><div><span>Peak energy your battery covered for your home</span><b>${m.kwh_to_home.toFixed(0)} kWh</b></div></div>`;
  const r = $("share");
  if (r) r.oninput = e => { creditShare = +e.target.value; renderBill(); $("share").focus(); };
}

function renderProtect() {
  const m = member();
  $("tab-protect").innerHTML = `<div class="shield"><div style="flex:1"><div style="font-weight:700">Protect my backup</div><div class="small mute" id="protectState"></div></div>
      <button class="toggle" id="protectToggle" role="switch" aria-checked="false" aria-label="Protect my backup"><i></i></button></div>
    <div class="hours"><div><span class="small mute">Always kept, even while earning</span><b>${m.reserve_backup_hours} h</b><span class="small mute">20% floor at your average use (${m.avg_home_kw} kW)</span></div>
      <div><span class="small mute">Your guarantee</span><b>Never below 20%</b><span class="small mute">Lowest in September: ${pct(m.min_soc)}</span></div></div>
    <div class="storm"><b>Before a storm or a grid emergency</b><ol>
      <li>Tap Protect. Your home leaves any grid-earning batch right away.</li>
      <li>Your backup locks at whatever charge you have now, not just 20%.</li>
      <li>The lock travels inside every signed command, and your battery enforces it itself, even if a bad command gets through.</li>
      <li>Tap again when the danger's past. We never turn it off for you.</li></ol></div>
    <p class="small mute">Riding through an outage is the battery hardware's job. WattGap's job is to make sure the charge is there when it happens.</p>`;
  $("protectToggle").onclick = () => post(`/api/protect?scope=home&on=${!S.home.protected}`);
  if (S) renderHomeLive();
}

function renderMemberWhy() {
  const all = Z.map(z => E.members[z]), mx = Math.max(...all.map(m => m.net_value));
  $("memberWhy").innerHTML = `<h3 style="font-size:18px;margin-bottom:6px">Why this is a member product, not a battery dashboard</h3>
    <p>Every number in the app comes from the same audited ledger the operator sees, priced at real ERCOT settlement prices. No model writes the copy, and nothing is estimated that we could compute instead.</p>
    <p><b>Protect is a promise the hardware keeps.</b> The member's floor rides inside every signed command, and the device enforces it on its own. The supervisor can't override it, and neither can an attacker on the wire.</p>
    <p><b>Honest about money.</b> We don't know Base's tariff, so the Bill tab keeps it an explicit assumption with three designs. The member always sees the computed grid value and their backup hours.</p>
    <p><b>Same battery, different zone.</b> September 2023 grid value per home, WattGap vs the fixed schedule:</p>
    <div class="zv">${all.map(m => `<div class="r"><span>${nice(m.zone)}</span><span class="bar"><i style="width:${m.net_value / mx * 100}%;background:${COLOR[m.zone]}"></i></span><b>${money(m.net_value, 0)}</b></div>
      <div class="r mute"><span></span><span class="bar"><i style="width:${m.fair_schedule_value / mx * 100}%;background:#c3c9d5"></i></span><span>${money(m.fair_schedule_value, 0)}</span></div>`).join("")}</div>
    <p class="small mute">South earns least because LZ_SOUTH cleared about $460/MWh under the other zones during the Sep 6 scarcity: congestion the operator desk sees first. Home load is ERCOT's backcasted residential profile (RESHIWR) for each zone's weather region, scaled per home.</p>`;
}

const ONB = [
  ["🏠", "Your battery, your backup", "Your battery has two jobs: keep your home powered when the grid goes down, and help Texas when power is scarce."],
  ["🛡️", "Your backup comes first", () => `The bottom 20% is never used for the grid. For a home like yours that's about <b>${member().reserve_backup_hours} hours</b> of average use, always waiting.`],
  ["⛈️", "You're always in control", "Storm coming? Tap <b>Protect</b>. Earning stops and your battery holds everything it has. One tap to undo."],
  ["🧾", "Receipts, not mysteries", "After every grid event you get a receipt, and every month a statement. Every number traces back to a real ERCOT price."],
];
let onbStep = 0;
function renderOnb() {
  const [art, title, text] = ONB[onbStep], last = onbStep === ONB.length - 1;
  $("onb").innerHTML = `<div class="art" aria-hidden="true">${art}</div><h3 id="onbTitle">${title}</h3><p>${typeof text === "function" ? text() : text}</p>
    <div class="dotsbar" aria-hidden="true">${ONB.map((_, i) => `<i class="${i === onbStep ? "on" : ""}"></i>`).join("")}</div>
    <div class="nav">${onbStep ? `<button class="btn" data-onb="-1">Back</button>` : `<button class="btn" data-onb="skip">Skip</button>`}
    <button class="btn go" data-onb="${last ? "done" : "1"}">${last ? "Go to my battery" : "Next"}</button></div>`;
  $("onb").querySelector(".btn.go").focus({preventScroll: true});
}
function openOnb() { onbStep = 0; $("onb").hidden = false; renderOnb(); }
function closeOnb() { $("onb").hidden = true; localStorage.setItem("wattgap.onboarded", "1"); }

function selectTab(name) {
  document.querySelectorAll(".tabs [role=tab]").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === name));
  ["today", "month", "bill", "protect"].forEach(t => { $("tab-" + t).hidden = t !== name; });
}

/* ---------- evidence ---------- */
async function renderEvidence() {
  const s = (await (await fetch("/api/export")).json()).summary;
  const items = [["decisions_count", "dispatch decisions"], ["approvals_count", "approvals"], ["expirations_count", "expired (fail-closed)"],
    ["alarms_count", "alarm ticks"], ["recommits_count", "zone re-commits"], ["quarantines_count", "quarantines"],
    ["revocations_count", "revoked keys"], ["security_count", "rejected messages"], ["discharge_without_live_batch", "discharges without a live batch"]];
  $("evi").innerHTML = items.map(([k, l]) => `<div class="${k === "discharge_without_live_batch" ? "zero" : ""}"><b>${s[k]}</b><span>${l}</span></div>`).join("") +
    `<div><b>${s.mwh_delivered}</b><span>MWh delivered · ${s.mwh_exported} exported</span></div>`;
}

/* ---------- wiring ---------- */
document.addEventListener("click", e => {
  const b = e.target.closest("button, a");
  if (!b) return;
  if (b.dataset.post) post(b.dataset.post);
  else if (b.dataset.chaos) post(`/api/chaos/${b.dataset.chaos}?zone=${$("zoneSel").value}`);
  else if (b.dataset.day) { day = b.dataset.day; renderDay(); }
  else if (b.dataset.tab) selectTab(b.dataset.tab);
  else if (b.dataset.bill) { billMode = b.dataset.bill; renderBill(); }
  else if (b.dataset.onb) {
    const a = b.dataset.onb;
    if (a === "skip" || a === "done") closeOnb(); else { onbStep += +a; renderOnb(); }
  }
});
$("play").onclick = () => post(`/api/control/${S && S.playing ? "pause" : "play"}`);
$("deskBtn").onclick = () => post(`/api/chaos/${S.desk_alive ? "kill_desk" : "revive_desk"}`);
$("stormBtn").onclick = () => post(`/api/protect?scope=fleet&on=${!S.fleet.protected}`);
$("replayOnb").onclick = openOnb;
document.querySelector(".tabs").addEventListener("keydown", e => {
  const tabs = [...document.querySelectorAll(".tabs [role=tab]")], i = tabs.indexOf(document.activeElement);
  if (i < 0 || !["ArrowLeft", "ArrowRight"].includes(e.key)) return;
  const n = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
  n.focus(); selectTab(n.dataset.tab);
});

async function refresh() {
  S = await (await fetch("/api/state")).json();
  renderLive(); renderHomeLive();
}

(async () => {
  E = await (await fetch("/api/economics")).json();
  renderKpis(); renderDay(); renderToday(); renderMonth(); renderBill(); renderMemberWhy();
  await refresh(); renderProtect(); renderEvidence();
  if (!localStorage.getItem("wattgap.onboarded")) openOnb();
  setInterval(refresh, 1000);
  setInterval(renderEvidence, 5000);
})();
