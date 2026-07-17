/* grandMA2 MCP Console — app.js v2 */

const state = {
  page: 1,
  config: null,
  debug: false,
  lastPayload: null,
  activity: [],
  fixturesLoaded: false,
  fixtures: [],
  typeGroups: {},
  selectedFixtureId: null,
  expandedTypes: new Set(),
  execsLoaded: false,
  execs: [],
  selectedExec: null,
  hasBaseline: false,
  lastPlan: null,
  running: false,
};

const $ = (sel) => document.querySelector(sel);
const el = {
  showfileLabel:    $("#showfile-label"),
  versionLabel:     $("#version-label"),
  connectionPill:   $("#connection-pill"),
  connectionLabel:  $("#connection-label"),
  divergenceChip:   $("#divergence-chip"),
  divergenceLabel:  $("#divergence-label"),
  pageInput:        $("#page-input"),
  refreshBtn:       $("#refresh-btn"),
  debugToggle:      $("#debug-toggle"),
  debugPanel:       $("#debug-panel"),
  debugOutput:      $("#debug-output"),
  debugClose:       $("#debug-close"),
  sidebarFoot:      $("#sidebar-foot"),
  navBtns:          [...document.querySelectorAll(".nav-btn")],
  views:            [...document.querySelectorAll(".view")],
  toastStack:       $("#toast-stack"),
  // Dashboard
  statShowfile:     $("#stat-showfile"),
  statVersion:      $("#stat-version"),
  statSession:      $("#stat-session"),
  statSessionDetail:$("#stat-session-detail"),
  statUsers:        $("#stat-users"),
  statUsersSub:     $("#stat-users-sub"),
  statTarget:       $("#stat-target"),
  statTransport:    $("#stat-transport"),
  dashUsers:        $("#dash-users"),
  dashTelemetry:    $("#dash-telemetry"),
  dashTraces:       $("#dash-traces"),
  divergenceBadge:  $("#divergence-badge"),
  divergenceResult: $("#divergence-result"),
  snapshotBtn:      $("#snapshot-btn"),
  divergenceCheckBtn: $("#divergence-check-btn"),
  // Playback
  execGrid:         $("#exec-grid"),
  execOverviewBadge:  $("#exec-overview-badge"),
  execOverviewRefresh: $("#exec-overview-refresh"),
  execId:           $("#exec-id"),
  execLookup:       $("#exec-lookup"),
  execDetail:       $("#exec-detail"),
  seqForm:          $("#seq-form"),
  seqId:            $("#seq-id"),
  seqBadge:         $("#seq-badge"),
  seqCues:          $("#seq-cues"),
  seqInfo:          $("#seq-info"),
  pageRefs:         [...document.querySelectorAll(".page-ref")],
  // Patch
  patchFilter:      $("#patch-filter"),
  patchStat:        $("#patch-stat"),
  patchBadge:       $("#patch-badge"),
  patchList:        $("#patch-list"),
  patchDetail:      $("#patch-detail"),
  patchTypeSummary: $("#patch-type-summary"),
  patchUniverses:   $("#patch-universes"),
  // Agent
  planForm:         $("#plan-form"),
  goalInput:        $("#goal-input"),
  runGoal:          $("#run-goal"),
  autoConfirm:      $("#auto-confirm"),
  planCard:         $("#plan-card"),
  planMeta:         $("#plan-meta"),
  planOutput:       $("#plan-output"),
  traceCard:        $("#trace-card"),
  traceResult:      $("#trace-result"),
  traceOutput:      $("#trace-output"),
  tracesList:       $("#traces-list"),
  tracesRefresh:    $("#traces-refresh"),
  recipesList:      $("#recipes-list"),
  // Analysis
  expectForm:       $("#expect-form"),
  expectInput:      $("#expect-input"),
  expectOutput:     $("#expect-output"),
  telemForm:        $("#telem-form"),
  telemDays:        $("#telem-days"),
  telemOutput:      $("#telem-output"),
  activityLog:      $("#activity-log"),
  // Modal
  confirmModal:     $("#confirm-modal"),
  confirmText:      $("#confirm-text"),
  confirmSteps:     $("#confirm-steps"),
  confirmRun:       $("#confirm-run"),
  confirmCancel:    $("#confirm-cancel"),
};

/* ── Helpers ─────────────────────────────────────────── */

function esc(v) {
  return String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function kvTable(pairs) {
  const rows = pairs
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`)
    .join("");
  return rows ? `<table class="kv-table">${rows}</table>` : "";
}

function toast(msg, kind = "error") {
  const node = document.createElement("div");
  node.className = `toast ${kind}`;
  node.textContent = msg;
  el.toastStack.appendChild(node);
  setTimeout(() => node.remove(), 5000);
}

function logActivity(path, payload) {
  state.lastPayload = payload;
  state.activity.unshift({ path, at: new Date().toLocaleTimeString(), ok: !payload?.error });
  if (state.activity.length > 40) state.activity.length = 40;
  el.activityLog.innerHTML = state.activity
    .map((a) => `<div class="list-item"><span class="list-item-name ${a.ok ? "" : "status-bad"}">${esc(a.path)}</span><span class="list-item-meta">${esc(a.at)}</span></div>`)
    .join("");
  if (state.debug) el.debugOutput.textContent = JSON.stringify(payload, null, 2);
}

async function api(path) {
  const res = await fetch(path);
  const data = await res.json();
  logActivity(path.split("?")[0], data);
  if (data?.error && !data?.traces) toast(String(data.error));
  return data;
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json();
  logActivity(path, data);
  return data;
}

function fmtDuration(ms) {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function fmtAge(iso) {
  if (!iso) return "";
  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 90) return `${Math.round(secs)}s ago`;
  if (secs < 5400) return `${Math.round(secs / 60)}m ago`;
  if (secs < 129600) return `${Math.round(secs / 3600)}h ago`;
  return `${Math.round(secs / 86400)}d ago`;
}

/* ── Navigation ──────────────────────────────────────── */

function activateView(name) {
  el.navBtns.forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  el.views.forEach((v) => v.classList.toggle("active", v.dataset.view === name));
  if (name === "patch" && !state.fixturesLoaded) loadFixtures();
  if (name === "playback" && !state.execsLoaded) loadExecOverview();
  if (name === "agent") { loadTraces(); loadRecipes(); }
}

function syncPageRefs() {
  el.pageRefs.forEach((node) => { node.textContent = String(state.page); });
}

/* ── Header health ───────────────────────────────────── */

async function loadHealth() {
  try {
    const h = await api("/api/health");
    el.showfileLabel.textContent = h.showfile || "--";
    el.versionLabel.textContent = h.version ? `v${h.version}` : "--";
    el.connectionPill.className = `chip ${h.connected ? "live" : "dead"}`;
    el.connectionLabel.textContent = h.connected ? "Live" : "Disconnected";

    el.statShowfile.textContent = h.showfile || "--";
    el.statVersion.textContent = h.version ? `grandMA2 onPC ${h.version}` : "--";
    el.statSession.textContent = h.connected ? "Connected" : "No session";
    el.statSession.className = `stat-value ${h.connected ? "status-ok" : "status-bad"}`;
    el.statSessionDetail.textContent = h.session?.username
      ? `${h.session.username} · idle ${Math.round(h.session.idle_seconds || 0)}s`
      : "No active console session";
    el.sidebarFoot.textContent = h.showfile ? `${h.showfile} · page ${h.faderpage || "?"}` : "";
    return h;
  } catch {
    el.connectionPill.className = "chip dead";
    el.connectionLabel.textContent = "Unreachable";
    return null;
  }
}

/* ── Dashboard ───────────────────────────────────────── */

function renderUsers(users) {
  el.dashUsers.innerHTML = users.length
    ? users.map((u) =>
        `<div class="list-item"><span class="list-item-name">${esc(u.name)}${u.logged_in ? ' <span class="status-ok" title="Logged in">●</span>' : ""}</span><span class="list-item-meta">${esc(u.rights)} · ${esc(u.profile || "Default")}</span></div>`
      ).join("")
    : `<div class="empty">No users parsed</div>`;

  const active = users.find((u) => u.logged_in);
  el.statUsers.textContent = active ? active.name : `${users.length} users`;
  el.statUsersSub.textContent = active ? `${active.rights} · ${active.profile || "Default"}` : "No active login";
}

function riskBars(container, summary) {
  const read = summary?.SAFE_READ ?? 0;
  const write = summary?.SAFE_WRITE ?? 0;
  const destructive = summary?.DESTRUCTIVE ?? 0;
  const max = Math.max(read, write, destructive, 1);
  container.innerHTML = [
    ["SAFE_READ", read, "read"],
    ["SAFE_WRITE", write, "write"],
    ["DESTRUCTIVE", destructive, "destructive"],
  ].map(([label, val, cls]) =>
    `<div class="bar-row">
       <span class="bar-label">${label}</span>
       <div class="bar-track"><div class="bar-fill ${cls}" style="width:${Math.round((val / max) * 100)}%"></div></div>
       <span class="bar-value">${val}</span>
     </div>`
  ).join("");
}

async function loadDashboard() {
  state.page = Number(el.pageInput.value || 1);
  const [health, dash] = await Promise.all([loadHealth(), api("/api/dashboard")]);
  if (state.config) {
    el.statTarget.textContent = `${state.config.gma_host}:${state.config.gma_port}`;
    el.statTransport.textContent = state.config.transport || "";
  }
  if (dash) renderUsers(dash.parsed_users || []);

  api(`/api/analysis/telemetry?days=1`).then((t) => {
    if (t?.error) { el.dashTelemetry.innerHTML = `<div class="empty">${esc(t.error)}</div>`; return; }
    riskBars(el.dashTelemetry, t.risk_summary || {});
    const total = t.total_operations ?? 0;
    el.dashTelemetry.insertAdjacentHTML("beforeend",
      `<div class="stat-sub" style="margin-top:8px">${total} tool calls · ${t.errors ?? 0} errors</div>`);
  });

  api("/api/agent/traces?limit=6").then((t) => {
    renderTraceList(el.dashTraces, t.traces || [], true);
  });
  checkDivergence(false);
  return health;
}

/* ── Divergence ──────────────────────────────────────── */

function renderDivergence(d) {
  if (d?.error || d?.diverged == null) {
    state.hasBaseline = false;
    el.divergenceLabel.textContent = "Baseline: none";
    el.divergenceChip.className = "chip clickable";
    el.divergenceBadge.textContent = "off";
    el.divergenceResult.innerHTML = "";
    return;
  }
  state.hasBaseline = true;
  const age = Math.round(d.baseline_age_seconds || 0);
  el.divergenceBadge.textContent = `${age}s`;
  if (d.diverged) {
    el.divergenceLabel.textContent = "Diverged";
    el.divergenceChip.className = "chip clickable diverged";
    const varRows = Object.entries(d.changed_vars || {}).map(([k, v]) =>
      [k, `${v.baseline || "(empty)"} → ${v.current}`]);
    const poolRows = Object.entries(d.pool_changes || {}).map(([pool, c]) =>
      [pool, `${c.added.length ? "+" + c.added.join(",") : ""} ${c.removed.length ? "−" + c.removed.join(",") : ""}`.trim()]);
    el.divergenceResult.innerHTML =
      `<div class="status-warn" style="margin-bottom:8px">Console changed outside this session:</div>` +
      kvTable([...varRows, ...poolRows]);
  } else {
    el.divergenceLabel.textContent = "In sync";
    el.divergenceChip.className = "chip clickable clean-baseline";
    el.divergenceResult.innerHTML = `<div class="status-ok">No changes since baseline (${age}s old).</div>`;
  }
}

async function checkDivergence(interactive = true) {
  if (interactive) el.divergenceResult.innerHTML = `<div class="loading">Checking</div>`;
  const d = await api("/api/divergence");
  renderDivergence(d);
}

async function snapshotBaseline() {
  el.divergenceResult.innerHTML = `<div class="loading">Snapshotting</div>`;
  const r = await apiPost("/api/divergence/snapshot");
  if (r?.error) { toast(String(r.error)); el.divergenceResult.innerHTML = ""; return; }
  toast("Baseline captured", "ok");
  checkDivergence(false);
}

/* ── Playback ────────────────────────────────────────── */

function renderCues(cues, contextLabel) {
  el.seqBadge.textContent = cues.length;
  el.seqCues.innerHTML = cues.length
    ? cues.map((c) =>
        `<div class="cue-row"><span class="cue-num">${esc(c.cue || "--")}</span><span class="cue-label">${esc(c.label || c.raw || "")}</span></div>`
      ).join("")
    : `<div class="empty">${esc(contextLabel || "No cues parsed")}</div>`;
}

function renderExecGrid() {
  el.execOverviewBadge.textContent = state.execs.length;
  if (!state.execs.length) {
    el.execGrid.innerHTML = `<div class="empty">No assigned executors on page ${state.page}.</div>`;
    return;
  }
  el.execGrid.innerHTML = `<div class="exec-grid">` + state.execs.map((x) => {
    const sel = state.selectedExec === x.id ? " selected" : "";
    const kind = x.sequence_id != null
      ? `<span class="exec-tile-kind seq">SEQ ${x.sequence_id}</span>`
      : (x.effect_id != null ? `<span class="exec-tile-kind fx">FX ${x.effect_id}</span>` : `<span class="exec-tile-kind">—</span>`);
    const meta = x.sequence_id != null
      ? `${x.cue_count ?? "?"} cues${x.chaser ? " · chaser" : ""}`
      : (x.effect_id != null ? "effect" : "");
    return `<div class="exec-tile${sel}" data-exec="${x.id}">
      <div class="exec-tile-head"><span class="exec-tile-no">${x.page}.${x.id}</span>${kind}</div>
      <div class="exec-tile-name" title="${esc(x.name)}">${esc(x.name || "(unnamed)")}</div>
      <div class="exec-tile-meta">${esc(meta)}</div>
    </div>`;
  }).join("") + `</div>`;
  el.execGrid.querySelectorAll(".exec-tile").forEach((tile) =>
    tile.addEventListener("click", () => selectExecutor(Number(tile.dataset.exec))));
}

async function loadExecOverview(force = false) {
  el.execGrid.innerHTML = `<div class="loading">Scanning page ${state.page}</div>`;
  el.execOverviewBadge.textContent = "…";
  if (force) await apiPost("/api/cache/clear");
  const data = await api(`/api/executors-overview?page=${state.page}`);
  state.execs = data.executors || [];
  state.execsLoaded = true;
  renderExecGrid();
}

function selectExecutor(id) {
  state.selectedExec = id;
  renderExecGrid();
  const x = state.execs.find((e) => e.id === id);
  if (!x) return lookupExecutor(id);

  el.execDetail.innerHTML = kvTable([
    ["Executor", `${x.page}.${x.id}`],
    ["Name", x.name || "--"],
    ["Assigned", x.sequence_id != null ? `Sequence ${x.sequence_id}` : (x.effect_id != null ? `Effect ${x.effect_id}` : "--")],
    ["Width", x.width],
    ["Priority", x.priority || "--"],
    ["Chaser", x.chaser ? "On" : "Off"],
  ]);

  if (x.sequence_id != null) {
    el.seqId.value = String(x.sequence_id);
    el.seqCues.innerHTML = `<div class="loading">Loading cues for Seq ${x.sequence_id}</div>`;
    loadSequence();
  } else {
    renderCues([], x.effect_id != null
      ? `Executor ${x.page}.${x.id} runs Effect ${x.effect_id} — no cue list.`
      : "Nothing sequence-like on this executor.");
  }
}

async function lookupExecutor(idOverride) {
  const id = Number(idOverride || el.execId.value);
  if (!id || id < 1) return;
  state.selectedExec = id;
  renderExecGrid();
  el.execDetail.innerHTML = `<div class="loading">Probing ${state.page}.${id}</div>`;

  const data = await api(`/api/executor-detail?page=${state.page}&executor_id=${id}`);
  const info = data.executor_info;
  if (!info) {
    el.execDetail.innerHTML = `<div class="empty">Page ${state.page}.${id} returned no object — the slot is likely empty.</div>`;
    renderCues([], "No sequence linked");
    return;
  }
  el.execDetail.innerHTML = kvTable([
    ["Executor", `${data.page}.${data.executor_id}`],
    ["Label", info.label || "--"],
    ["Sequence", data.has_sequence ? `Seq ${data.sequence_id}` : "None assigned"],
  ]);
  if (data.has_sequence) el.seqId.value = String(data.sequence_id);
  renderCues(data.parsed_cues || [], data.has_sequence ? `Sequence ${data.sequence_id} has no parsed cues` : "No sequence linked to this executor");
}

async function loadSequence(ev) {
  if (ev) ev.preventDefault();
  const seqId = el.seqId.value.trim();
  if (!seqId) return;
  el.seqCues.innerHTML = `<div class="loading">Loading sequence ${esc(seqId)}</div>`;

  const data = await api(`/api/sequence?sequence_id=${encodeURIComponent(seqId)}&executor_page=${state.page}`);
  const cues = data.parsed_cues || [];
  el.seqInfo.innerHTML = kvTable([
    ["Sequence", `Seq ${seqId}`],
    ["Cues", cues.length],
    ["Command", data.command_sent || ""],
  ]);
  renderCues(cues, data.exists === false ? "No sequence found — check the ID" : "Sequence loaded but no cues parsed");
}

/* ── Patch ───────────────────────────────────────────── */

function fixtureIdRange(fixtures) {
  const ids = fixtures.map((f) => f.fixture_id).filter((n) => n != null).sort((a, b) => a - b);
  if (!ids.length) return "";
  // Compress into ranges: [1..10, 50] → "1–10, 50"
  const parts = [];
  let start = ids[0], prev = ids[0];
  for (let i = 1; i <= ids.length; i++) {
    if (ids[i] === prev + 1) { prev = ids[i]; continue; }
    parts.push(start === prev ? `${start}` : `${start}–${prev}`);
    start = prev = ids[i];
  }
  return parts.join(", ");
}

function universeOf(patch) {
  const m = /^(\d+)\./.exec(patch || "");
  return m ? Number(m[1]) : null;
}

function renderUniverseSummary() {
  const byUniverse = {};
  let unpatched = 0;
  for (const f of state.fixtures) {
    const u = universeOf(f.patch);
    if (u == null) { unpatched++; continue; }
    byUniverse[u] = (byUniverse[u] || 0) + 1;
  }
  const rows = Object.entries(byUniverse).sort((a, b) => Number(a[0]) - Number(b[0]));
  const max = Math.max(...rows.map(([, n]) => n), 1);
  el.patchUniverses.innerHTML = rows.length
    ? rows.map(([u, n]) =>
        `<div class="bar-row">
           <span class="bar-label">Universe ${u}</span>
           <div class="bar-track"><div class="bar-fill read" style="width:${Math.round((n / max) * 100)}%"></div></div>
           <span class="bar-value">${n}</span>
         </div>`).join("") +
      (unpatched ? `<div class="stat-sub" style="margin-top:6px">${unpatched} unpatched</div>` : "")
    : `<div class="empty">No DMX addresses parsed</div>`;
}

async function loadFixtures() {
  el.patchList.innerHTML = `<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>`;
  const data = await api("/api/fixtures");
  if (data.fixtures?.error || data.error) {
    el.patchList.innerHTML = `<div class="empty status-bad">${esc(data.fixtures?.error || data.error)}</div>`;
    return;
  }
  state.fixtures = data.fixture_rows || [];
  state.typeGroups = data.type_groups || {};
  state.fixturesLoaded = true;
  state.selectedFixtureId = null;
  state.expandedTypes = new Set();

  const total = data.total_count || state.fixtures.length;
  const types = data.type_count || Object.keys(state.typeGroups).length;
  el.patchStat.textContent = `${types} types · ${total} fixtures`;
  el.patchTypeSummary.innerHTML = Object.keys(state.typeGroups).length
    ? Object.entries(state.typeGroups).map(([name, g]) =>
        `<div class="list-item"><span class="list-item-name">${esc(name)}</span><span class="list-item-meta">${g.count}</span></div>`).join("")
    : `<div class="empty">No fixture types found</div>`;
  el.patchDetail.innerHTML = `<div class="empty">Select a fixture</div>`;
  renderUniverseSummary();
  renderFixtureList();
}

function renderFixtureList() {
  const q = el.patchFilter.value.trim().toLowerCase();
  let html = "";
  let matchCount = 0;

  for (const [typeName, group] of Object.entries(state.typeGroups)) {
    const fixtures = group.fixtures.filter((f) => {
      const hay = `${f.fixture_id} ${f.label} ${f.fixture_type} ${f.patch} ${f.summary}`.toLowerCase();
      return !q || hay.includes(q);
    });
    if (!fixtures.length) continue;
    matchCount += fixtures.length;

    // Filtered groups auto-expand; otherwise collapsed unless toggled open.
    const expanded = q ? true : state.expandedTypes.has(typeName);
    const universes = [...new Set(fixtures.map((f) => universeOf(f.patch)).filter((u) => u != null))];
    const uniLabel = universes.length ? `U${universes.join(", U")}` : "unpatched";

    html += `<div class="type-group${expanded ? "" : " collapsed"}" data-type="${esc(typeName)}">
      <div class="type-group-header">
        <span class="type-group-meta">
          <span class="type-group-caret">▼</span>
          <span class="type-group-name">${esc(typeName)}</span>
          <span class="type-group-range">${esc(fixtureIdRange(fixtures))}</span>
        </span>
        <span class="type-group-count">${fixtures.length} · ${esc(uniLabel)}</span>
      </div>
      <div class="type-group-body"><div class="fixture-chips">${fixtures.map((f) => {
        const sel = state.selectedFixtureId === f.fixture_id ? " selected" : "";
        const patched = f.patch && f.patch !== "(-)";
        const label = f.label ? `${f.fixture_id} · ${f.label}` : `${f.fixture_id}`;
        return `<span class="fixture-chip${sel}${patched ? "" : " unpatched"}" data-fid="${f.fixture_id}" title="${esc(f.label || "")} ${patched ? "DMX " + esc(f.patch) : "unpatched"}">${esc(label)}</span>`;
      }).join("")}</div></div>
    </div>`;
  }

  el.patchList.innerHTML = html || `<div class="empty">No fixtures${q ? " match the filter" : " in show"}</div>`;
  el.patchBadge.textContent = matchCount;

  el.patchList.querySelectorAll(".type-group-header").forEach((h) =>
    h.addEventListener("click", () => {
      const group = h.parentElement;
      const name = group.dataset.type;
      group.classList.toggle("collapsed");
      if (group.classList.contains("collapsed")) state.expandedTypes.delete(name);
      else state.expandedTypes.add(name);
    }));
  el.patchList.querySelectorAll(".fixture-chip").forEach((chip) =>
    chip.addEventListener("click", (e) => { e.stopPropagation(); selectFixture(Number(chip.dataset.fid)); }));
}

function selectFixture(id) {
  state.selectedFixtureId = id;
  const f = state.fixtures.find((x) => x.fixture_id === id);
  if (!f) return;
  const pairs = [["Fixture ID", f.fixture_id]];
  if (f.label) pairs.push(["Label", f.label]);
  if (f.fixture_type) pairs.push(["Fixture Type", f.fixture_type]);
  if (f.fix_id != null) pairs.push(["Fix ID", f.fix_id]);
  if (f.channel_id != null) pairs.push(["Channel ID", f.channel_id]);
  pairs.push(["DMX Patch", f.patch && f.patch !== "(-)" ? f.patch : "Unpatched"]);
  el.patchDetail.innerHTML = kvTable(pairs);
  renderFixtureList();
}

/* ── Agent ───────────────────────────────────────────── */

function renderPlan(data) {
  el.planCard.style.display = "";
  const steps = data.plan || data.steps || [];
  el.planMeta.textContent = `${data.intent || "?"} · conf ${data.confidence ?? "?"}`;
  el.planOutput.innerHTML = steps.length
    ? steps.map((s) => {
        const risk = s.risk || s.risk_tier || "";
        return `<div class="list-item">
          <span class="list-item-name mono">${esc(s.tool || s.tool_name || "step")}</span>
          <span class="list-item-meta">${risk ? `<span class="risk ${esc(risk)}">${esc(risk)}</span>` : ""}</span>
        </div>${s.step || s.description ? `<div class="trace-desc" style="padding:0 16px 8px">${esc(s.step || s.description)}</div>` : ""}`;
      }).join("")
    : `<div class="empty">No steps planned</div>`;
  if (data.policy_warnings?.length) {
    el.planOutput.insertAdjacentHTML("beforeend",
      `<div class="trace-error" style="margin:8px 16px">${data.policy_warnings.map(esc).join("<br>")}</div>`);
  }
}

function renderTrace(trace) {
  el.traceCard.style.display = "";
  el.traceResult.textContent = trace.result || "?";
  el.traceResult.className = `result-pill ${esc(trace.result || "")}`;
  const steps = trace.steps || [];
  el.traceOutput.innerHTML = steps.length
    ? steps.map((s) => `
        <div class="trace-step">
          <div class="trace-marker"><div class="trace-dot ${esc(s.status)}"></div><div class="trace-line"></div></div>
          <div class="trace-tool">${esc(s.tool_name)} <span class="risk ${esc(s.risk_tier)}">${esc(s.risk_tier)}</span> <span class="step-status ${esc(s.status)}">${esc(s.status)}</span></div>
          <div class="trace-duration">${fmtDuration(s.duration_ms)}</div>
          ${s.error ? `<div class="trace-error">${esc(s.error)}</div>` : ""}
        </div>`).join("")
    : `<div class="empty">Trace has no steps${trace.policy_warnings?.length ? " — " + esc(trace.policy_warnings.join("; ")) : ""}</div>`;
  if (trace.policy_warnings?.length && steps.length) {
    el.traceOutput.insertAdjacentHTML("afterbegin",
      `<div class="trace-error" style="margin:10px 16px 0">${trace.policy_warnings.map(esc).join("<br>")}</div>`);
  }
}

function renderTraceList(container, traces, compact = false) {
  container.innerHTML = traces.length
    ? traces.map((t) => `
        <div class="list-item interactive" data-run="${esc(t.run_id)}">
          <span class="list-item-name">${esc(t.goal || t.run_id)}</span>
          <span class="list-item-meta"><span class="result-pill ${esc(t.result)}">${esc(t.result)}</span>${compact ? "" : ` · ${fmtAge(t.started_at)}`}</span>
        </div>`).join("")
    : `<div class="empty">No agent runs recorded yet</div>`;
  container.querySelectorAll(".list-item").forEach((item) =>
    item.addEventListener("click", async () => {
      activateView("agent");
      const full = await api(`/api/agent/trace?run_id=${encodeURIComponent(item.dataset.run)}`);
      if (!full.error) { el.goalInput.value = full.goal || el.goalInput.value; renderTrace(full); }
    }));
}

async function loadTraces() {
  const t = await api("/api/agent/traces?limit=15");
  renderTraceList(el.tracesList, t.traces || []);
}

async function loadRecipes() {
  const r = await api("/api/agent/recipes");
  el.recipesList.innerHTML = (r.recipes || []).length
    ? r.recipes.map((rec) => `
        <div class="list-item" title="${esc((rec.tools || []).join(" → "))}">
          <span class="list-item-name">${esc(rec.name)}</span>
          <span class="list-item-meta">${rec.step_count} steps · ×${rec.use_count}</span>
        </div>`).join("")
    : `<div class="empty">No learned recipes yet — successful runs are stored automatically</div>`;
}

async function planGoal(ev) {
  if (ev) ev.preventDefault();
  const goal = el.goalInput.value.trim();
  if (!goal) return;
  el.planCard.style.display = "";
  el.planOutput.innerHTML = `<div class="loading">Planning</div>`;
  el.traceCard.style.display = "none";
  const data = await apiPost("/api/plan", { goal });
  state.lastPlan = data;
  renderPlan(data);
  return data;
}

function planHasDestructive(plan) {
  return (plan?.plan || plan?.steps || []).some((s) =>
    (s.risk || s.risk_tier) === "DESTRUCTIVE");
}

async function executeGoal(autoConfirm) {
  const goal = el.goalInput.value.trim();
  if (!goal || state.running) return;
  state.running = true;
  el.runGoal.disabled = true;
  el.traceCard.style.display = "";
  el.traceResult.textContent = "running";
  el.traceResult.className = "result-pill";
  el.traceOutput.innerHTML = `<div class="loading">Executing on console</div>`;
  try {
    const trace = await apiPost("/api/run", { goal, auto_confirm: autoConfirm });
    if (trace.error) {
      el.traceOutput.innerHTML = `<div class="trace-error" style="margin:12px 16px">${esc(trace.error)}</div>`;
      el.traceResult.textContent = "blocked";
      el.traceResult.className = "result-pill failed";
    } else {
      renderTrace(trace);
      toast(`Run ${trace.result}`, trace.result === "success" ? "ok" : "error");
    }
  } finally {
    state.running = false;
    el.runGoal.disabled = false;
    loadTraces();
    loadRecipes();
  }
}

async function runGoalClicked() {
  const goal = el.goalInput.value.trim();
  if (!goal) return;
  const plan = await planGoal();
  const wantsAuto = el.autoConfirm.checked;
  if (planHasDestructive(plan)) {
    // Destructive plans always pass through the modal
    const steps = (plan.plan || []).filter((s) => (s.risk || s.risk_tier) === "DESTRUCTIVE");
    el.confirmText.textContent = wantsAuto
      ? "This plan contains destructive steps. They will be auto-confirmed and will modify the show."
      : "This plan contains destructive steps. Without auto-confirm the runtime will block them; run with auto-confirm?";
    el.confirmSteps.innerHTML = steps.map((s) =>
      `<div class="list-item"><span class="list-item-name mono">${esc(s.tool || s.tool_name)}</span><span class="risk DESTRUCTIVE">DESTRUCTIVE</span></div>`).join("");
    el.confirmModal.classList.remove("hidden");
    return;
  }
  executeGoal(wantsAuto);
}

/* ── Analysis ────────────────────────────────────────── */

async function runExpectation(ev) {
  ev.preventDefault();
  const expected = el.expectInput.value.trim();
  if (!expected) return;
  el.expectOutput.innerHTML = `<div class="loading">Comparing</div>`;
  const data = await api(`/api/analysis/patch?expected=${encodeURIComponent(expected)}`);
  const fits = data.fits_expectation ?? data.identical ?? false;
  el.expectOutput.innerHTML =
    `<div class="${fits ? "status-ok" : "status-warn"}" style="margin-bottom:8px">${fits ? "Patch matches expectation" : "Patch differs from expectation"}</div>` +
    kvTable([
      ["Missing", String((data.missing || []).length)],
      ["Over", String((data.over || []).length)],
    ]) +
    (data.missing || []).map((m) =>
      `<div class="list-item"><span class="list-item-name status-bad">${esc(m.fixture_type || m.type || "Missing")}</span><span class="list-item-meta">expected ${m.expected_count ?? m.expected}, actual ${m.actual_count ?? m.actual}</span></div>`
    ).join("");
}

async function runTelemetry(ev) {
  ev.preventDefault();
  const days = Number(el.telemDays.value || 1);
  el.telemOutput.innerHTML = `<div class="loading">Loading</div>`;
  const data = await api(`/api/analysis/telemetry?days=${days}`);
  if (data.error) { el.telemOutput.innerHTML = `<div class="empty">${esc(data.error)}</div>`; return; }
  const wrap = document.createElement("div");
  riskBars(wrap, data.risk_summary || {});
  el.telemOutput.innerHTML = wrap.innerHTML + kvTable([
    ["Total tool calls", data.total_operations ?? 0],
    ["Errors", data.errors ?? 0],
    ["Destructive ops", data.destructive_operations ?? 0],
  ]);
}

/* ── Debug ───────────────────────────────────────────── */

function toggleDebug() {
  state.debug = el.debugToggle.checked;
  el.debugPanel.classList.toggle("hidden", !state.debug);
  if (state.debug && state.lastPayload) {
    el.debugOutput.textContent = JSON.stringify(state.lastPayload, null, 2);
  }
}

/* ── Wire & boot ─────────────────────────────────────── */

function wire() {
  el.navBtns.forEach((b) => b.addEventListener("click", () => activateView(b.dataset.view)));
  el.debugToggle.addEventListener("change", toggleDebug);
  el.debugClose.addEventListener("click", () => { el.debugToggle.checked = false; toggleDebug(); });
  el.refreshBtn.addEventListener("click", () => {
    state.fixturesLoaded = false;
    loadDashboard();
    const active = document.querySelector(".nav-btn.active");
    if (active && active.dataset.view === "patch") loadFixtures();
    if (active && active.dataset.view === "agent") { loadTraces(); loadRecipes(); }
  });
  el.pageInput.addEventListener("change", () => {
    state.page = Number(el.pageInput.value || 1);
    syncPageRefs();
    state.execsLoaded = false;
    state.selectedExec = null;
    if (document.querySelector(".nav-btn.active")?.dataset.view === "playback") loadExecOverview();
  });
  el.execOverviewRefresh.addEventListener("click", () => loadExecOverview(true));
  // Divergence
  el.snapshotBtn.addEventListener("click", snapshotBaseline);
  el.divergenceCheckBtn.addEventListener("click", () => checkDivergence(true));
  el.divergenceChip.addEventListener("click", () => checkDivergence(true));
  // Playback
  el.execLookup.addEventListener("click", () => lookupExecutor());
  el.execId.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); lookupExecutor(); } });
  el.seqForm.addEventListener("submit", loadSequence);
  // Patch
  el.patchFilter.addEventListener("input", renderFixtureList);
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA") {
      e.preventDefault();
      activateView("patch");
      el.patchFilter.focus();
    }
  });
  // Agent
  el.planForm.addEventListener("submit", planGoal);
  el.runGoal.addEventListener("click", runGoalClicked);
  el.tracesRefresh.addEventListener("click", loadTraces);
  el.confirmCancel.addEventListener("click", () => el.confirmModal.classList.add("hidden"));
  el.confirmRun.addEventListener("click", () => {
    el.confirmModal.classList.add("hidden");
    executeGoal(true);
  });
  // Analysis
  el.expectForm.addEventListener("submit", runExpectation);
  el.telemForm.addEventListener("submit", runTelemetry);
}

async function boot() {
  wire();
  try {
    state.config = await api("/api/config");
    syncPageRefs();
    await loadDashboard();
  } catch (err) {
    el.connectionPill.className = "chip dead";
    el.connectionLabel.textContent = "Error";
    toast(String(err));
  }
  // Light header poll — one cached read every 20s
  setInterval(loadHealth, 20000);
}

boot();
