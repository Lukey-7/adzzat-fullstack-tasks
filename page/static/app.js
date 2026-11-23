// List + detail view over the task API. Hash routing: #/tasks/<id>.
const list = document.getElementById("task-list");
const detail = document.getElementById("detail");

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
}

function badge(text, cls) {
  return text ? `<span class="badge ${esc(cls)}">${esc(text)}</span>` : "";
}

function reward(r) {
  if (r === null || r === undefined) return "–";
  return `<span class="${r >= 1 ? "pass" : "fail"}">${Number(r).toFixed(1)}</span>`;
}

function cases(row) {
  return row.cases ? `${row.passed ?? "?"}/${row.cases}` : "";
}

function resultsHTML(res) {
  const parts = [];
  if (res.harbor?.length) {
    parts.push(`<h3>Harbor runs</h3><table><tr><th>Agent</th><th>Reward</th><th>Hidden cases</th><th>Job</th></tr>
      ${res.harbor.map((r) => `<tr><td>${esc(r.agent)}</td><td>${reward(r.reward)}</td><td>${cases(r)}</td><td>${esc(r.job)}</td></tr>`).join("")}</table>`);
  }
  if (res.agent_runs?.length) {
    parts.push(`<h3>Free local agent</h3><table><tr><th>Model</th><th>Reward</th><th>Hidden cases</th><th>Steps</th><th>Minutes</th></tr>
      ${res.agent_runs.map((r) => `<tr><td>${esc(r.model)}</td><td>${reward(r.reward)}</td><td>${cases(r)}</td><td>${esc(r.steps)}</td><td>${esc(r.minutes)}</td></tr>`).join("")}</table>`);
  }
  if (res.shortcuts?.length) {
    parts.push(`<h3>Shortcut attempts</h3><table><tr><th>Attempt</th><th>Visible check</th><th>Hidden reward</th><th>Hidden cases</th></tr>
      ${res.shortcuts.map((r) => `<tr><td>${esc(r.attempt)}</td><td>${esc(r.visible_check)}</td><td>${reward(r.hidden_reward)}</td><td>${cases(r)}</td></tr>`).join("")}</table>`);
  }
  return parts.join("") || `<p class="muted">No recorded results yet.</p>`;
}

async function showTask(id) {
  for (const a of list.querySelectorAll("a")) {
    a.setAttribute("aria-current", a.dataset.id === id ? "page" : "false");
  }
  detail.innerHTML = `<p class="muted">Loading…</p>`;
  try {
    const t = await getJSON(`/api/tasks/${encodeURIComponent(id)}`);
    detail.innerHTML = `
      <div class="meta">${badge(t.kind, "kind")}${badge(t.difficulty, "diff-" + t.difficulty)}
        ${t.tags.map((x) => badge(x, "tag")).join("")}</div>
      <h2 class="task-id">${esc(t.id)}</h2>
      <article class="statement">${t.statement_html}</article>
      <h3>Difficulty: ${esc(t.difficulty)}</h3>
      <p>${esc(t.difficulty_note)}</p>
      <h3>Environment</h3>
      <p>Base image <code>${esc(t.environment.base_image)}</code>; graded artifact(s)
        <code>${esc(t.environment.graded_artifacts.join(", "))}</code>; verifier runs in a
        <code>${esc(t.environment.verifier_mode)}</code> container.</p>
      <details><summary>Dockerfile</summary><pre>${esc(t.environment.dockerfile)}</pre></details>
      ${resultsHTML(t.results)}`;
  } catch (err) {
    detail.innerHTML = `<p class="error">Could not load task: ${esc(err.message)}</p>`;
  }
}

async function init() {
  try {
    const tasks = await getJSON("/api/tasks");
    list.innerHTML = tasks.map((t) => `
      <li><a href="#/tasks/${esc(t.id)}" data-id="${esc(t.id)}">
        <strong>${esc(t.title)}</strong>
        <span>${badge(t.kind, "kind")}${badge(t.difficulty, "diff-" + t.difficulty)}</span>
      </a></li>`).join("") || `<li class="muted">No tasks found.</li>`;
  } catch (err) {
    list.innerHTML = `<li class="error">Could not load tasks: ${esc(err.message)}</li>`;
    return;
  }
  route();
}

function route() {
  const m = location.hash.match(/^#\/tasks\/([a-z0-9-]+)$/);
  if (m) showTask(m[1]);
}

window.addEventListener("hashchange", route);
init();
