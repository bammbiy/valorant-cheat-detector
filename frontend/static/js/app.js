// valoscan/frontend/static/js/app.js

const API = {
  async analyze(name, tag, region) {
    const r = await fetch(`/api/analyze/${region}/${encodeURIComponent(name)}/${encodeURIComponent(tag)}`);
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

// ── colour helpers ──────────────────────────────────────────────────────────
const colour = (v) => v >= 75 ? "#e8413a" : v >= 45 ? "#d4860a" : "#1e9e52";

// ── DOM shortcuts ───────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.add("on");
const hide = (id) => $(id).classList.remove("on");

// ── page switching ──────────────────────────────────────────────────────────
function goSearch() {
  show("pg-search"); hide("pg-result");
  _setNavActive(0);
}

function goResult() {
  if (!_lastResult) return;
  hide("pg-search"); show("pg-result");
  _setNavActive(1);
  setTimeout(() => _renderCharts(_lastResult), 60);
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
  runAnalysis(name, tag, region);
}

$("searchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });

function loadDemo(nameTag) {
  $("searchInput").value = nameTag;
  const [name, tag] = nameTag.split("#");
  runAnalysis(name, tag, "kr");
}

// ── analysis flow ────────────────────────────────────────────────────────────
async function runAnalysis(name, tag, region) {
  _startLoading();

  try {
    const data = await API.analyze(name, tag, region);
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
