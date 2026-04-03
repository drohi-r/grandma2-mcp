/* grandMA2 MCP Console — app.js */

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
  lastExecutorId: "",
  lastSequenceId: "",
};

const $ = (sel) => document.querySelector(sel);
const el = {
  connectionPill:   $("#connection-pill"),
  connectionLabel:  $("#connection-label"),
  pageInput:        $("#page-input"),
  refreshBtn:       $("#refresh-btn"),
  debugToggle:      $("#debug-toggle"),
  debugPanel:       $("#debug-panel"),
  debugOutput:      $("#debug-output"),
  debugClose:       $("#debug-close"),
  navBtns:          [...document.querySelectorAll(".nav-btn")],
  views:            [...document.querySelectorAll(".view")],
  // Dashboard
  statTarget:       $("#stat-target"),
  statTransport:    $("#stat-transport"),
  statSession:      $("#stat-session"),
  statSessionDetail:$("#stat-session-detail"),
  statUsers:        $("#stat-users"),
  statUsersSub:     $("#stat-users-sub"),
  dashUsers:        $("#dash-users"),
  // Executors
  execId:           $("#exec-id"),
  execLookup:       $("#exec-lookup"),
  execDetail:       $("#exec-detail"),
  execCueCard:      $("#exec-cue-card"),
  execCueBadge:     $("#exec-cue-badge"),
  execCues:         $("#exec-cues"),
  execSequenceLink: $("#exec-sequence-link"),
  pageRefs:         [...document.querySelectorAll(".page-ref")],
  execRefs:         [...document.querySelectorAll(".exec-ref")],
  quickSeqBtns:     [...document.querySelectorAll(".quick-seq")],
  // Sequence
  seqForm:          $("#seq-form"),
  seqId:            $("#seq-id"),
  seqExec:          $("#seq-exec"),
  seqBadge:         $("#seq-badge"),
  seqCues:          $("#seq-cues"),
  seqInfo:          $("#seq-info"),
  // Patch
  patchFilter:      $("#patch-filter"),
  patchStat:        $("#patch-stat"),
  patchBadge:       $("#patch-badge"),
  patchList:        $("#patch-list"),
  patchDetail:      $("#patch-detail"),
  patchTypeSummary: $("#patch-type-summary"),
  // Analysis
  expectForm:       $("#expect-form"),
  expectInput:      $("#expect-input"),
  expectOutput:     $("#expect-output"),
  telemForm:        $("#telem-form"),
  telemDays:        $("#telem-days"),
  telemOutput:      $("#telem-output"),
  // Actions
  planForm:         $("#plan-form"),
  goalInput:        $("#goal-input"),
  runGoal:          $("#run-goal"),
  planOutput:       $("#plan-output"),
  activityLog:      $("#activity-log"),
};

// --- Helpers ---
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

function logActivity(path, payload) {
  state.lastPayload = payload;
  state.activity.unshift({ path, at: new Date().toLocaleTimeString(), ok: !payload?.error });
  if (state.activity.length > 30) state.activity.length = 30;
  el.activityLog.innerHTML = state.activity
    .map((a) => `<div class="activity-item"><span class="activity-path">${esc(a.path)}</span><span class="activity-time">${esc(a.at)}</span></div>`)
    .join("");
  if (state.debug) el.debugOutput.textContent = JSON.stringify(payload, null, 2);
}

async function api(path) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" } });
  const data = await res.json();
  logActivity(path.split("?")[0], data);
  return data;
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  logActivity(path, data);
  return data;
}

// --- Navigation ---
function activateView(name) {
  el.navBtns.forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  el.views.forEach((v) => v.classList.toggle("active", v.dataset.view === name));
  if (name === "patch" && !state.fixturesLoaded) loadFixtures();
  if (name === "executors" && state.lastExecutorId && !el.execId.value) el.execId.value = state.lastExecutorId;
  if (name === "sequence" && state.lastSequenceId && !el.seqId.value) el.seqId.value = state.lastSequenceId;
}

function syncPageRefs() {
  el.pageRefs.forEach((node) => { node.textContent = String(state.page); });
}

// --- Dashboard ---
function renderDashboard(data) {
  const sess = data.sessions?.sessions?.[0];
  const connected = sess?.connected;
  el.connectionPill.className = `connection-pill ${connected ? "live" : "error"}`;
  el.connectionLabel.textContent = connected ? "Live" : "Disconnected";

  el.statTarget.textContent = state.config ? `${state.config.gma_host}:${state.config.gma_port}` : "--";
  el.statTransport.textContent = state.config?.transport || "--";

  el.statSession.textContent = connected ? "Connected" : "No session";
  el.statSession.className = `stat-value ${connected ? "status-ok" : "status-bad"}`;
  el.statSessionDetail.textContent = sess?.username
    ? `${sess.username} \u00b7 idle ${Math.round(sess.idle_seconds || 0)}s`
    : "No active console session";

  const users = data.parsed_users || [];
  const activeUser = users.find((u) => u.logged_in);
  el.statUsers.textContent = activeUser ? activeUser.name : `${users.length} user${users.length !== 1 ? "s" : ""}`;
  el.statUsersSub.textContent = activeUser ? `${activeUser.rights} \u00b7 ${activeUser.profile || "Default"}` : "No active login";

  el.dashUsers.innerHTML = users.length
    ? users.map((u) =>
        `<div class="list-item"><span class="list-item-name">${esc(u.name)}${u.logged_in ? ' <span class="status-ok">\u2022</span>' : ""}</span><span class="list-item-meta">${esc(u.rights)} \u00b7 ${esc(u.profile || "Default")}</span></div>`
      ).join("")
    : `<div class="empty">No users parsed</div>`;
}

async function loadDashboard() {
  state.page = Number(el.pageInput.value || 1);
  state.fixturesLoaded = false;
  const data = await api("/api/dashboard");
  if (data) renderDashboard(data);
}

// --- Executors ---
async function lookupExecutor() {
  const id = Number(el.execId.value);
  if (!id || id < 1) {
    el.execDetail.innerHTML = `<div class="empty">Enter an executor number (e.g. 201)</div>`;
    el.execSequenceLink.innerHTML = `<div class="empty">No executor selected yet.</div>`;
    el.execCueCard.style.display = "none";
    return;
  }
  state.lastExecutorId = String(id);
  el.execRefs.forEach((node) => { node.textContent = String(id); });
  el.execDetail.innerHTML = `<div class="loading">Looking up executor ${state.page}.${id}</div>`;
  el.execCueCard.style.display = "none";
  el.execSequenceLink.innerHTML = `<div class="loading">Checking linked sequence</div>`;

  const data = await api(`/api/executor-detail?page=${state.page}&executor_id=${id}`);
  const info = data.executor_info;

  if (!info) {
    el.execDetail.innerHTML = `
      <div class="empty">
        Page ${state.page}.${id} returned no object from MA2.<br>
        This usually means the slot is empty, not that the UI is broken.
      </div>`;
    el.execSequenceLink.innerHTML = `
      <div class="empty">
        No linked sequence because the slot itself is empty.<br>
        Try a known assigned executor or use the Sequence view with a direct sequence ID.
      </div>`;
    return;
  }

  el.execDetail.innerHTML = kvTable([
    ["Executor", `${data.page}.${data.executor_id}`],
    ["Label", info.label || "--"],
    ["Sequence", data.has_sequence ? `Seq ${data.sequence_id}` : "None assigned"],
    ["Command", data.status?.command_sent || "--"],
  ]);

  // Show cues
  const cues = data.parsed_cues || [];
  el.execCueCard.style.display = "";
  el.execCueBadge.textContent = cues.length;

  if (data.has_sequence && data.sequence_id) {
    el.execSequenceLink.innerHTML = `
      ${kvTable([
        ["Linked Sequence", `Seq ${data.sequence_id}`],
        ["Cue Count", cues.length],
      ])}
      <div class="btn-row" style="margin-top:12px">
        <button id="open-linked-sequence" class="btn-sm btn-accent">Open In Sequence View</button>
      </div>
    `;
    document.querySelector("#open-linked-sequence")?.addEventListener("click", () => {
      el.seqId.value = String(data.sequence_id);
      el.seqExec.value = String(id);
      activateView("sequence");
      loadSequence();
    });
  } else {
    el.execSequenceLink.innerHTML = `
      <div class="empty">
        This executor exists, but MA2 did not resolve a linked sequence from this slot.<br>
        Use the Sequence view with a direct sequence ID if you want to inspect cues.
      </div>
    `;
  }

  if (cues.length) {
    el.execCues.innerHTML = cues.map((c) =>
      `<div class="cue-row"><span class="cue-num">${esc(c.cue || "--")}</span><span class="cue-label">${esc(c.label || c.raw || "")}</span></div>`
    ).join("");
  } else if (data.has_sequence) {
    el.execCues.innerHTML = `<div class="empty">Sequence ${data.sequence_id} exists but no cues parsed</div>`;
  } else {
    el.execCues.innerHTML = `<div class="empty">No sequence linked to this executor</div>`;
  }
}

// --- Sequence ---
async function loadSequence(ev) {
  if (ev) ev.preventDefault();
  const seqId = el.seqId.value.trim();
  const execId = el.seqExec.value.trim();
  if (!seqId && !execId) {
    el.seqInfo.innerHTML = `<div class="empty">Provide a sequence ID or executor ID</div>`;
    return;
  }
  if (seqId) state.lastSequenceId = seqId;
  if (execId) state.lastExecutorId = execId;
  const params = new URLSearchParams({ executor_page: String(state.page) });
  if (seqId) params.set("sequence_id", seqId);
  if (execId) params.set("executor_id", execId);

  el.seqCues.innerHTML = `<div class="loading">Loading sequence</div>`;
  el.seqInfo.innerHTML = `<div class="loading">Resolving</div>`;

  const data = await api(`/api/sequence?${params}`);
  const cues = data.parsed_cues || [];
  const exists = data.exists !== false;
  const seqResolved = data.resolved_sequence_id;
  const fromExecutor = Boolean(execId && !seqId);

  // Determine status
  let statusHtml;
  if (data.blocked || data.error) {
    const msg = data.error || "Failed to load sequence";
    statusHtml = `<span class="status-bad">${esc(msg)}</span>`;
  } else if (!exists) {
    statusHtml = `<span class="status-warn">No linked sequence</span>`;
  } else {
    statusHtml = `<span class="status-ok">${cues.length} cue${cues.length !== 1 ? "s" : ""} loaded</span>`;
  }

  el.seqInfo.innerHTML = kvTable([
    ["Lookup Mode", seqId ? "Direct sequence" : (fromExecutor ? `Executor ${state.page}.${execId}` : "Unknown")],
    ["Sequence", seqResolved ? `Seq ${seqResolved}` : "Not resolved"],
    ["Command", data.command_sent || "--"],
  ]) + `<div style="margin-top:8px">${statusHtml}</div>` + (
    !seqId && !seqResolved
      ? `<div class="empty" style="margin-top:12px">That executor lookup did not resolve a sequence. Use a direct sequence ID for reliable cue inspection.</div>`
      : ""
  );

  // Cue list
  el.seqBadge.textContent = cues.length;
  if (!cues.length) {
    el.seqCues.innerHTML = exists
      ? `<div class="empty">Sequence loaded but contains no parsed cues</div>`
      : `<div class="empty">No sequence found \u2014 check the ID or executor assignment</div>`;
    return;
  }
  el.seqCues.innerHTML = cues.map((c) =>
    `<div class="cue-row"><span class="cue-num">${esc(c.cue || "--")}</span><span class="cue-label">${esc(c.label || c.raw || "")}</span></div>`
  ).join("");
}

// --- Patch ---
async function loadFixtures() {
  el.patchList.innerHTML = `<div class="loading">Loading fixture inventory</div>`;
  el.patchDetail.innerHTML = `<div class="empty">Loading...</div>`;

  const data = await api("/api/fixtures");
  if (data.fixtures?.error || data.error) {
    el.patchList.innerHTML = `<div class="empty status-bad">${esc(data.fixtures?.error || data.error)}</div>`;
    return;
  }
  state.fixtures = data.fixture_rows || [];
  state.typeGroups = data.type_groups || {};
  state.fixturesLoaded = true;
  state.selectedFixtureId = null;

  const total = data.total_count || state.fixtures.length;
  const types = data.type_count || Object.keys(state.typeGroups).length;
  el.patchBadge.textContent = total;
  el.patchStat.textContent = `${types} type${types !== 1 ? "s" : ""} \u00b7 ${total} fixture${total !== 1 ? "s" : ""}`;

  el.patchTypeSummary.innerHTML = Object.keys(state.typeGroups).length
    ? kvTable(Object.entries(state.typeGroups).map(([name, g]) => [name, `${g.count}`]))
    : `<div class="empty">No fixture types found</div>`;

  el.patchDetail.innerHTML = `<div class="empty">Select a fixture</div>`;
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
    html += `<div class="type-group">
      <div class="type-group-header">
        <span class="type-group-name">${esc(typeName)}</span>
        <span class="type-group-count">${fixtures.length}</span>
      </div>
      <div class="type-group-body">${fixtures.map((f) => {
        const sel = state.selectedFixtureId === f.fixture_id ? " selected" : "";
        const label = f.label || `Fixture ${f.fixture_id}`;
        const meta = f.patch && f.patch !== "(-)" ? `DMX ${f.patch}` : "Unpatched";
        return `<div class="list-item${sel}" data-fid="${f.fixture_id}">
          <span class="list-item-name">${esc(label)}</span>
          <span class="list-item-meta">${esc(meta)}</span>
        </div>`;
      }).join("")}</div>
    </div>`;
  }

  if (!html) {
    // If no type groups parsed, show raw fixture list
    const rawFixtures = state.fixtures.filter((f) => {
      if (!q) return true;
      return `${f.fixture_id} ${f.summary}`.toLowerCase().includes(q);
    });
    matchCount = rawFixtures.length;
    if (rawFixtures.length) {
      html = rawFixtures.map((f) => {
        const sel = state.selectedFixtureId === f.fixture_id ? " selected" : "";
        return `<div class="list-item${sel}" data-fid="${f.fixture_id}">
          <span class="list-item-name">Fixture ${f.fixture_id}</span>
          <span class="list-item-meta">${esc(f.summary || "--")}</span>
        </div>`;
      }).join("");
    }
  }

  el.patchList.innerHTML = html || `<div class="empty">No fixtures${q ? " match filter" : " in show"}</div>`;
  el.patchBadge.textContent = matchCount;

  el.patchList.querySelectorAll(".list-item").forEach((item) => {
    item.addEventListener("click", () => selectFixture(Number(item.dataset.fid)));
  });
}

function selectFixture(id) {
  state.selectedFixtureId = id;
  const f = state.fixtures.find((x) => x.fixture_id === id);
  if (!f) return;

  const detailPairs = [["Fixture ID", f.fixture_id]];
  if (f.label) detailPairs.push(["Label", f.label]);
  if (f.fixture_type) detailPairs.push(["Fixture Type", f.fixture_type]);
  if (f.fixture_type_id != null) detailPairs.push(["Type ID", f.fixture_type_id]);
  if (f.fix_id != null) detailPairs.push(["Fix ID", f.fix_id]);
  if (f.channel_id != null) detailPairs.push(["Channel ID", f.channel_id]);
  detailPairs.push(["DMX Patch", f.patch && f.patch !== "(-)" ? f.patch : "Unpatched"]);
  if (f.has_parameters != null) detailPairs.push(["Parameters", f.has_parameters ? "Yes" : "No"]);
  if (f.summary) detailPairs.push(["Raw", f.summary]);

  el.patchDetail.innerHTML = kvTable(detailPairs);
  renderFixtureList();
}

// --- Analysis ---
async function runExpectation(ev) {
  ev.preventDefault();
  const expected = el.expectInput.value.trim();
  if (!expected) return;
  el.expectOutput.innerHTML = `<div class="loading">Comparing</div>`;
  const data = await api(`/api/analysis/patch?expected=${encodeURIComponent(expected)}`);
  el.expectOutput.innerHTML = kvTable([
    ["Fits", String(data.fits_expectation ?? data.identical ?? false)],
    ["Missing", String((data.missing || []).length)],
    ["Over", String((data.over || []).length)],
  ]) + (data.missing || []).map((m) =>
    `<div class="list-item"><span class="list-item-name status-bad">${esc(m.fixture_type || m.type || "Missing")}</span><span class="list-item-meta">expected ${m.expected_count ?? m.expected}, actual ${m.actual_count ?? m.actual}</span></div>`
  ).join("");
}

async function runTelemetry(ev) {
  ev.preventDefault();
  const days = Number(el.telemDays.value || 1);
  el.telemOutput.innerHTML = `<div class="loading">Loading</div>`;
  const data = await api(`/api/analysis/telemetry?days=${days}`);
  el.telemOutput.innerHTML = kvTable([
    ["Total Ops", data.total_operations ?? 0],
    ["Destructive", data.destructive_operations ?? 0],
    ["Errors", data.errors ?? 0],
    ["SAFE_READ", data.risk_summary?.SAFE_READ ?? 0],
    ["SAFE_WRITE", data.risk_summary?.SAFE_WRITE ?? 0],
    ["DESTRUCTIVE", data.risk_summary?.DESTRUCTIVE ?? 0],
  ]);
}

// --- Actions ---
async function planGoal(ev) {
  ev.preventDefault();
  const goal = el.goalInput.value.trim();
  if (!goal) return;
  el.planOutput.innerHTML = `<div class="loading">Planning</div>`;
  const data = await apiPost("/api/plan", { goal });
  el.planOutput.innerHTML = kvTable([
    ["Intent", data.intent || "--"],
    ["Object Type", data.object_type || "--"],
    ["Confidence", data.confidence ?? "--"],
    ["Steps", data.step_count || (data.plan || []).length],
  ]) + (data.plan || []).map((s) =>
    `<div class="list-item"><span class="list-item-name">${esc(s.tool || "step")}</span><span class="list-item-meta">${esc(s.description || "")}</span></div>`
  ).join("");
}

async function runGoalAction() {
  const goal = el.goalInput.value.trim();
  if (!goal) return;
  el.planOutput.innerHTML = `<div class="loading">Executing</div>`;
  const data = await apiPost("/api/run", { goal, auto_confirm: false });
  el.planOutput.innerHTML = kvTable([
    ["Goal", data.goal || goal],
    ["Completed", String(data.completed ?? data.success ?? false)],
    ["Steps", (data.steps || []).length],
    ["Warnings", (data.warnings || []).length],
  ]);
}

// --- Debug ---
function toggleDebug() {
  state.debug = el.debugToggle.checked;
  el.debugPanel.classList.toggle("hidden", !state.debug);
  if (state.debug && state.lastPayload) {
    el.debugOutput.textContent = JSON.stringify(state.lastPayload, null, 2);
  }
}

// --- Wire & Boot ---
function wire() {
  el.navBtns.forEach((b) => b.addEventListener("click", () => activateView(b.dataset.view)));
  el.debugToggle.addEventListener("change", toggleDebug);
  el.debugClose.addEventListener("click", () => { el.debugToggle.checked = false; toggleDebug(); });
  el.refreshBtn.addEventListener("click", () => {
    state.fixturesLoaded = false;
    loadDashboard();
    const active = document.querySelector(".nav-btn.active");
    if (active) activateView(active.dataset.view);
  });
  el.pageInput.addEventListener("change", () => {
    state.page = Number(el.pageInput.value || 1);
    syncPageRefs();
    loadDashboard();
  });
  // Executors — single lookup, not bulk scan
  el.execLookup.addEventListener("click", lookupExecutor);
  el.execId.addEventListener("keydown", (e) => { if (e.key === "Enter") lookupExecutor(); });
  // Sequence
  el.seqForm.addEventListener("submit", loadSequence);
  el.quickSeqBtns.forEach((btn) => btn.addEventListener("click", () => {
    const seq = btn.dataset.seq;
    el.seqId.value = seq;
    el.seqExec.value = "";
    state.lastSequenceId = seq;
    loadSequence();
  }));
  // Patch
  el.patchFilter.addEventListener("input", renderFixtureList);
  // Analysis
  el.expectForm.addEventListener("submit", runExpectation);
  el.telemForm.addEventListener("submit", runTelemetry);
  // Actions
  el.planForm.addEventListener("submit", planGoal);
  el.runGoal.addEventListener("click", runGoalAction);
}

async function boot() {
  wire();
  try {
    const cfg = await api("/api/config");
    state.config = cfg;
    syncPageRefs();
    await loadDashboard();
  } catch (err) {
    el.connectionPill.className = "connection-pill error";
    el.connectionLabel.textContent = "Error";
    el.activityLog.innerHTML = `<div class="empty status-bad">${esc(String(err))}</div>`;
  }
}

boot();
