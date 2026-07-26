// valoscan/frontend/static/js/app.js

const API = {
  async analyze(name, tag, region, game) {
    const query = new URLSearchParams({ game });
    const r = await fetch(`/api/analyze/${region}/${encodeURIComponent(name)}/${encodeURIComponent(tag)}?${query}`);
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    return r.json();
  },
};

const LOGS = [
  "connecting to riot api...",
  "fetching account puuid...",
  "loading match history...",
  "running stat anomaly detection...",
  "running physics impossibility check...",
  "running ml ensemble (5 models)...",
  "computing cumulative trust score...",
  "building suspicion report...",
];

let _charts = {};
let _lastResult = null;
let _selectedGame = "valorant";
let _alertSince = 0;
const _seenAlerts = new Set();

const GAME_META = {
  valorant: { note: "Riot official API · match history analysis", run: "ANALYZE" },
  overwatch: { note: "Official data source under review · replay analysis planned", run: "SOON" },
};

function selectGame(game) {
  _selectedGame = game;
  document.querySelectorAll(".game-tab").forEach((tab) => tab.classList.remove("on"));
  $("game-" + game).classList.add("on");
  $("game-note").textContent = GAME_META[game].note;
  $("run-button").textContent = GAME_META[game].run;
  $("run-button").disabled = game !== "valorant";
}

async function pollAlerts() {
  try {
    const query = new URLSearchParams({ game: _selectedGame, since: String(_alertSince) });
    const response = await fetch(`/api/alerts?${query}`);
    if (!response.ok) return;
    const alerts = await response.json();
    alerts.forEach((alert) => {
      _alertSince = Math.max(_alertSince, alert.created_at + 0.001);
      if (_seenAlerts.has(alert.id)) return;
      _seenAlerts.add(alert.id);
      showAlertToast(alert);
    });
    $("alert-count").textContent = String(_seenAlerts.size);
  } catch (err) {
    console.warn("alert polling unavailable", err);
  }
}

function showAlertToast(alert) {
  const panel = $("alert-panel");
  const toast = document.createElement("div");
  toast.className = `alert-toast ${alert.severity === "high-risk" ? "high-risk" : "review"}`;
  toast.innerHTML = `<div class="alert-toast-kicker">${alert.severity} · review queue</div><strong>${alert.player}</strong><span>${alert.detail}</span>`;
  panel.appendChild(toast);
  setTimeout(() => toast.remove(), 7000);
}

function showAlerts() {
  const count = $("alert-count");
  count.classList.remove("pulse");
  void count.offsetWidth;
  count.classList.add("pulse");
}

setInterval(pollAlerts, 5000);
pollAlerts();

// ── colour helpers ──────────────────────────────────────────────────────────
const colour = (v) => v >= 75 ? "#e8413a" : v >= 45 ? "#d4860a" : "#1e9e52";

// ── DOM shortcuts ───────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.add("on");
const hide = (id) => $(id).classList.remove("on");

// ── page switching ──────────────────────────────────────────────────────────
function goSearch() {
  show("pg-search"); ["pg-result", "pg-alerts", "pg-quality", "pg-model"].forEach(hide);
  _setNavActive(0);
}

function goResult() {
  if (!_lastResult) return;
  hide("pg-search"); ["pg-alerts", "pg-quality", "pg-model"].forEach(hide); show("pg-result");
  _setNavActive(1);
  setTimeout(() => _renderCharts(_lastResult), 60);
}

function goProductPage(pageId, navId) {
  ["pg-search", "pg-result", "pg-alerts", "pg-quality", "pg-model"].forEach(hide);
  show(pageId);
  document.querySelectorAll(".nav-btn").forEach((button) => button.classList.remove("on"));
  if (navId) $(navId).classList.add("on");
}

async function goAlerts() {
  goProductPage("pg-alerts", "nav-alerts");
  const response = await fetch(`/api/alerts?game=${_selectedGame}`);
  const alerts = await response.json();
  $("alert-list").innerHTML = alerts.length ? alerts.reverse().map(renderAlertRow).join("") : '<div class="empty-state">현재 검토 대기 알림이 없습니다.</div>';
}

async function goQuality() {
  goProductPage("pg-quality", "nav-quality");
  const report = await (await fetch("/api/quality")).json();
  $("quality-grid").innerHTML = [
    ["STATUS", report.status], ["BENCHMARK", `${report.accuracy ?? "—"}%`],
    ["FALSE POSITIVE", `${report.false_positive_rate ?? "—"}%`], ["SAMPLES", report.sample_count.toLocaleString()],
    ["COVERAGE", `${report.coverage}%`], ["CALIBRATION", report.calibration],
  ].map(([label, value]) => `<div class="quality-card"><span>${label}</span><strong>${value}</strong></div>`).join("");
  $("quality-note").innerHTML = `<strong>${report.benchmark_label}</strong><p>${report.validation_method}</p><ul>${report.limitations.map((item) => `<li>${item}</li>`).join("")}</ul>`;
}

async function goModel() {
  goProductPage("pg-model", "nav-model");
  const report = await (await fetch("/api/model")).json();
  $("model-policy").innerHTML = `<span>DECISION POLICY</span><strong>${report.decision_policy}</strong><small>version ${report.version}</small>`;
  $("model-grid").innerHTML = report.signals.map((signal) => `<article class="model-card"><div><strong>${signal.name}</strong><span class="model-status">${signal.status}</span></div><p>${signal.role}</p><small>${signal.limitation}</small></article>`).join("");
  $("safeguard-list").innerHTML = report.safeguards.map((item) => `<div class="safeguard-item"><span>✓</span>${item}</div>`).join("");
}

function renderAlertRow(alert) {
  return `<article class="alert-row"><div class="alert-row-dot ${alert.severity}"></div><div><strong>${alert.player}</strong><p>${alert.detail}</p></div><span>${alert.severity}</span></article>`;
}

function _setNavActive(idx) {
  document.querySelectorAll(".nav-btn").forEach((b, i) => b.classList.toggle("on", i === idx));
}

// ── search ──────────────────────────────────────────────────────────────────
function doSearch() {
  const raw = $("searchInput").value.trim();
  if (!raw) { $("searchInput").focus(); return; }
  const [name, tag = "KR1"] = raw.includes("#") ? raw.split("#") : [raw, "KR1"];
  const region = $("regionSel").value;
  runAnalysis(name, tag, region, _selectedGame);
}

$("searchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });

function loadDemo(nameTag) {
  $("searchInput").value = nameTag;
  const [name, tag] = nameTag.split("#");
  runAnalysis(name, tag, "kr", "valorant");
}

// ── analysis flow ────────────────────────────────────────────────────────────
async function runAnalysis(name, tag, region, game) {
  _startLoading();

  try {
    const data = await API.analyze(name, tag, region, game);
    _lastResult = data;
    _renderResult(data);
    $("nav-result").style.display = "";
    _stopLoading();
    goResult();
  } catch (err) {
    _stopLoading();
    _showError(err.message);
  }
}

// loading sequence
let _logInterval = null;

function _startLoading() {
  hide("pg-search"); hide("pg-result");
  show("loading");
  $("log-list").innerHTML = "";
  $("ld-txt").textContent = "initializing...";

  let i = 0;
  _logInterval = setInterval(() => {
    if (i >= LOGS.length) { clearInterval(_logInterval); return; }

    const el = document.createElement("div");
    el.className = "log-line run";
    el.textContent = LOGS[i];
    $("log-list").appendChild(el);
    requestAnimationFrame(() => el.classList.add("on"));

    if (i > 0) {
      const prev = $("log-list").children[i - 1];
      if (prev) { prev.className = "log-line done on"; }
    }

    $("ld-txt").textContent = LOGS[i];
    i++;
  }, 280);
}

function _stopLoading() {
  clearInterval(_logInterval);
  hide("loading");
  show("pg-search");
}

function _showError(msg) {
  goSearch();
  const note = document.createElement("div");
  note.className = "error-toast";
  note.textContent = `오류: ${msg}`;
  document.body.appendChild(note);
  setTimeout(() => note.remove(), 4000);
}

// ── render ───────────────────────────────────────────────────────────────────
function _renderResult(p) {
  const c   = colour(p.suspicion_pct);
  const vt  = { cheater: "핵 강력 의심", suspect: "요주의", clean: "정상" }[p.verdict] ?? p.verdict;

  // topbar
  $("r-avatar").textContent = p.name.slice(0, 2).toUpperCase();
  $("r-avatar").style.cssText = `color:${c};border-color:${c}44`;
  $("r-name").textContent = p.name;
  $("r-meta").textContent = `#${p.tag} · ${p.rank} · WR ${p.stats.win_rate}%`;
  $("r-pct").textContent  = `${p.suspicion_pct}%`;
  $("r-pct").style.color  = c;
  $("r-vlbl").textContent = vt;
  $("demo-badge").style.display = p.demo ? "inline-block" : "none";
  $("evidence-banner").innerHTML = `
    <div><span class="evidence-kicker">EVIDENCE QUALITY</span><strong>${p.evidence_quality ?? "limited"}</strong></div>
    <div><span class="evidence-kicker">CONFIDENCE</span><strong>${p.confidence ?? 50}%</strong></div>
    <div class="evidence-source"><span class="evidence-kicker">SOURCE</span>${p.data_source ?? "unknown"}</div>`;

  // stat row
  $("stat-row").innerHTML = [
    { l: "HS RATE",  v: `${p.stats.avg_hs_pct}%`,  s: "avg all matches", a: p.stats.avg_hs_pct > 75 },
    { l: "K/D",      v: p.stats.avg_kda,            s: "this season",     a: p.stats.avg_kda > 6    },
    { l: "ADR",      v: p.stats.avg_adr,            s: "per round",       a: p.stats.avg_adr > 280  },
    { l: "WIN RATE", v: `${p.stats.win_rate}%`,     s: "total",           a: false                   },
  ].map(x => `
    <div class="sc">
      <div class="sc-l">${x.l}</div>
      <div class="sc-v" style="color:${x.a ? colour(90) : "var(--t0)"}">${x.v}</div>
      <div class="sc-s">${x.s}</div>
    </div>`).join("");

  // subsystems
  $("sys-grid").innerHTML = [
    { k: "stat_anomaly", l: "STAT ANOMALY" },
    { k: "physics",      l: "PHYSICS CHECK" },
    { k: "ml_ensemble",  l: "ML ENSEMBLE" },
    { k: "trust_score",  l: "TRUST SCORE", inv: true },
  ].map(s => {
    const raw  = p.subsystems[s.k];
    const disp = s.inv ? 100 - raw : raw;
    const c    = colour(disp);
    return `
      <div class="sys-c">
        <div class="sys-l">${s.l}</div>
        <div class="sys-v" style="color:${c}">${disp}%</div>
        <div class="sys-bg"><div class="sys-fill" style="width:${disp}%;background:${c}"></div></div>
      </div>`;
  }).join("");

  // flags
  const sc = { red: "#e8413a", amber: "#d4860a", green: "#1e9e52" };
  const sb = { red: "rgba(232,65,58,.1)", amber: "rgba(212,134,10,.09)", green: "rgba(30,158,82,.09)" };
  const st = { red: "CRIT", amber: "WARN", green: "OK" };
  $("flag-block").innerHTML = p.flags.map(f => `
    <div class="flag-row">
      <div class="f-ind" style="background:${sc[f.severity]}"></div>
      <div class="f-body">
        <div class="f-title">${f.title}</div>
        <div class="f-desc">${f.detail}</div>
      </div>
      <div class="f-tag" style="background:${sb[f.severity]};color:${sc[f.severity]}">${st[f.severity]}</div>
    </div>`).join("");

  // match history
  $("match-body").innerHTML = p.matches.map(m => `
    <tr>
      <td>${m.map}</td>
      <td style="color:var(--t2)">${m.agent}</td>
      <td><span class="dot" style="background:${m.won ? "#1e9e52" : "#e8413a"}"></span>${m.kda}</td>
      <td style="color:${colour(m.hs_pct)}">${m.hs_pct}%</td>
      <td style="color:var(--t1)">${m.adr}</td>
      <td style="color:${colour(m.suspicion)};font-weight:600">${m.suspicion}%</td>
    </tr>`).join("");

  // ML votes
  $("ml-votes").innerHTML = p.ml_votes.map(v => `
    <div class="ml-row">
      <div class="ml-name">${v.model}</div>
      <div class="ml-bg"><div class="ml-fill" style="width:${v.confidence}%;background:${colour(v.confidence)}"></div></div>
      <div class="ml-pct" style="color:${colour(v.confidence)}">${v.confidence}%</div>
    </div>`).join("");

  // trust
  const t  = p.subsystems.trust_score;
  const tc = t > 60 ? "#1e9e52" : t > 35 ? "#d4860a" : "#e8413a";
  $("trust-num").textContent  = t;
  $("trust-num").style.color  = tc;
  $("trust-fill").style.cssText = `width:${t}%;background:${tc}`;
  $("trust-hint").textContent = t < 30 ? "자동 신고 권장" : t < 60 ? "추가 관찰 필요" : "신뢰 계정";
}

function _renderCharts(p) {
  ["hs", "susp"].forEach(k => { if (_charts[k]) _charts[k].destroy(); });

  const labels = p.hs_history.map((_, i) => `G${i + 1}`);

  const baseOpts = () => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: {
        min: 0, max: 100,
        ticks: { callback: v => v + "%", font: { size: 8, family: "'IBM Plex Mono'" }, color: "#505058" },
        grid: { color: "rgba(255,255,255,0.04)" },
        border: { display: false },
      },
      x: {
        ticks: { font: { size: 8, family: "'IBM Plex Mono'" }, color: "#505058" },
        grid: { display: false },
        border: { display: false },
      },
    },
  });

  const make = (id, data, ref, c) => new Chart($(id), {
    type: "line",
    data: {
      labels,
      datasets: [
        { data, borderColor: c, backgroundColor: c + "12", tension: .3, pointRadius: 2, borderWidth: 1.5, fill: true },
        { data: Array(data.length).fill(ref), borderColor: "#2a2a30", borderDash: [3, 3], borderWidth: 1, pointRadius: 0 },
      ],
    },
    options: baseOpts(),
  });

  _charts.hs   = make("hsChart",   p.hs_history,         52, colour(p.stats.avg_hs_pct));
  _charts.susp = make("suspChart", p.suspicion_history,  45, colour(p.suspicion_pct));
}
