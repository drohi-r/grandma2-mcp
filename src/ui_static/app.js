const state = {
  page: 1,
  dashboard: null,
  executors: [],
  fixtures: [],
  activity: [],
};

const els = {
  pageInput: document.querySelector("#page-input"),
  refreshDashboard: document.querySelector("#refresh-dashboard"),
  navButtons: [...document.querySelectorAll(".nav")],
  views: [...document.querySelectorAll(".view")],
  consoleSummary: document.querySelector("#console-summary"),
  fixtureTypeSummary: document.querySelector("#fixture-type-summary"),
  sessionSummary: document.querySelector("#session-summary"),
  userSummary: document.querySelector("#user-summary"),
  executorFilter: document.querySelector("#executor-filter"),
  executorGrid: document.querySelector("#executor-grid"),
  executorDetail: document.querySelector("#executor-detail"),
  sequenceForm: document.querySelector("#sequence-form"),
  sequenceId: document.querySelector("#sequence-id"),
  sequenceExecutor: document.querySelector("#sequence-executor"),
  sequenceSummary: document.querySelector("#sequence-summary"),
  cueList: document.querySelector("#cue-list"),
  fixtureFilter: document.querySelector("#fixture-filter"),
  fixtureList: document.querySelector("#fixture-list"),
  patchDetail: document.querySelector("#patch-detail"),
  expectationForm: document.querySelector("#expectation-form"),
  expectationInput: document.querySelector("#expectation-input"),
  expectationOutput: document.querySelector("#expectation-output"),
  telemetryForm: document.querySelector("#telemetry-form"),
  telemetryDays: document.querySelector("#telemetry-days"),
  telemetryOutput: document.querySelector("#telemetry-output"),
  planForm: document.querySelector("#plan-form"),
  goalInput: document.querySelector("#goal-input"),
  runGoal: document.querySelector("#run-goal"),
  planOutput: document.querySelector("#plan-output"),
  activityOutput: document.querySelector("#activity-output"),
};

function setActivity(summary, payload) {
  state.activity.unshift({
    at: new Date().toISOString(),
    summary,
    blocked: payload?.blocked || false,
    error: payload?.error || "",
  });
  state.activity = state.activity.slice(0, 25);
  els.activityOutput.textContent = JSON.stringify(state.activity, null, 2);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {"Content-Type": "application/json"},
    ...options,
  });
  const payload = await response.json();
  setActivity(`${options.method || "GET"} ${path}`, payload);
  return payload;
}

function activateView(name) {
  els.navButtons.forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  els.views.forEach((view) => view.classList.toggle("active", view.dataset.view === name));
}

function renderDashboard(payload) {
  state.dashboard = payload;
  els.consoleSummary.textContent = JSON.stringify(payload.console_location, null, 2);
  els.fixtureTypeSummary.textContent = JSON.stringify({
    entry_count: payload.fixture_types?.entry_count || 0,
    entries: (payload.fixture_types?.entries || []).slice(0, 20),
  }, null, 2);
  els.sessionSummary.textContent = JSON.stringify(payload.sessions, null, 2);
  els.userSummary.textContent = JSON.stringify(payload.users, null, 2);
  state.executors = payload.page_map?.executors || [];
  renderExecutors();
}

function renderExecutors() {
  const query = els.executorFilter.value.trim().toLowerCase();
  const matches = state.executors.filter((item) => {
    const hay = `${item.id} ${item.label} ${item.type} ${item.sequence_id || ""}`.toLowerCase();
    return !query || hay.includes(query);
  });
  els.executorGrid.innerHTML = "";
  for (const item of matches) {
    const el = document.createElement("button");
    el.className = "executor-card";
    el.innerHTML = `
      <strong>${item.label || `Exec ${item.id}`}</strong>
      <small>ID ${item.id} · ${item.type}</small>
      <small>Seq ${item.sequence_id ?? "—"} · ${item.trigger}</small>
    `;
    el.addEventListener("click", async () => {
      const detail = await api(`/api/executor-detail?page=${state.page}&executor_id=${item.id}`);
      els.executorDetail.textContent = JSON.stringify(detail, null, 2);
      renderCueList(detail.parsed_cues || []);
      activateView("executors");
    });
    els.executorGrid.appendChild(el);
  }
}

function renderCueList(cues) {
  els.cueList.innerHTML = "";
  if (!cues.length) {
    els.cueList.innerHTML = `<div class="cue-item"><strong>No parsed cues</strong><small>Raw sequence output is still available in the summary panel.</small></div>`;
    return;
  }
  for (const cue of cues) {
    const el = document.createElement("div");
    el.className = "cue-item";
    el.innerHTML = `
      <strong>${cue.cue || "Cue"}</strong>
      <small>${cue.label || "No parsed label"}</small>
      <small>${cue.raw}</small>
    `;
    els.cueList.appendChild(el);
  }
}

async function loadSequenceFromForm(event) {
  event.preventDefault();
  const sequenceId = els.sequenceId.value.trim();
  const executorId = els.sequenceExecutor.value.trim();
  const params = new URLSearchParams({executor_page: String(state.page)});
  if (sequenceId) params.set("sequence_id", sequenceId);
  if (executorId) params.set("executor_id", executorId);
  const payload = await api(`/api/sequence?${params.toString()}`);
  els.sequenceSummary.textContent = JSON.stringify(payload, null, 2);
  renderCueList(payload.parsed_cues || []);
}

function renderFixtures() {
  const query = els.fixtureFilter.value.trim().toLowerCase();
  const matches = state.fixtures.filter((item) => {
    const hay = `${item.fixture_id} ${item.summary}`.toLowerCase();
    return !query || hay.includes(query);
  });
  els.fixtureList.innerHTML = "";
  for (const item of matches) {
    const el = document.createElement("button");
    el.className = "fixture-item";
    el.innerHTML = `
      <strong>Fixture ${item.fixture_id}</strong>
      <small>${item.summary}</small>
    `;
    el.addEventListener("click", () => {
      els.patchDetail.textContent = JSON.stringify(item, null, 2);
    });
    els.fixtureList.appendChild(el);
  }
}

async function loadFixtures() {
  const payload = await api("/api/fixtures");
  state.fixtures = payload.fixture_rows || [];
  els.patchDetail.textContent = JSON.stringify({
    fixture_types: payload.fixture_types?.entry_count || 0,
    worlds: payload.worlds,
    layouts: payload.layouts,
  }, null, 2);
  renderFixtures();
}

async function loadDashboard() {
  state.page = Number(els.pageInput.value || 1);
  const payload = await api(`/api/dashboard?page=${state.page}`);
  renderDashboard(payload);
}

async function runPatchExpectation(event) {
  event.preventDefault();
  const expected = els.expectationInput.value.trim();
  const payload = await api(`/api/analysis/patch?expected=${encodeURIComponent(expected)}`);
  els.expectationOutput.textContent = JSON.stringify(payload, null, 2);
}

async function loadTelemetry(event) {
  event.preventDefault();
  const days = Number(els.telemetryDays.value || 1);
  const payload = await api(`/api/analysis/telemetry?days=${days}`);
  els.telemetryOutput.textContent = JSON.stringify(payload, null, 2);
}

async function planGoal(event) {
  event.preventDefault();
  const goal = els.goalInput.value.trim();
  const payload = await api("/api/plan", {
    method: "POST",
    body: JSON.stringify({goal}),
  });
  els.planOutput.textContent = JSON.stringify(payload, null, 2);
}

async function runGoal() {
  const goal = els.goalInput.value.trim();
  const payload = await api("/api/run", {
    method: "POST",
    body: JSON.stringify({goal, auto_confirm: false}),
  });
  els.planOutput.textContent = JSON.stringify(payload, null, 2);
}

function wire() {
  els.navButtons.forEach((button) => button.addEventListener("click", () => activateView(button.dataset.view)));
  els.refreshDashboard.addEventListener("click", loadDashboard);
  els.executorFilter.addEventListener("input", renderExecutors);
  els.sequenceForm.addEventListener("submit", loadSequenceFromForm);
  els.fixtureFilter.addEventListener("input", renderFixtures);
  els.expectationForm.addEventListener("submit", runPatchExpectation);
  els.telemetryForm.addEventListener("submit", loadTelemetry);
  els.planForm.addEventListener("submit", planGoal);
  els.runGoal.addEventListener("click", runGoal);
}

async function bootstrap() {
  wire();
  await loadDashboard();
  await loadFixtures();
  const cfg = await api("/api/config");
  setActivity("config", cfg);
}

bootstrap().catch((error) => {
  els.activityOutput.textContent = JSON.stringify({error: String(error)}, null, 2);
});
