/* JarvisERP agent workbench — five tabs, one per close problem. Everything shown here comes from the run log,
   which is the audit chain: nothing is rendered that wasn't logged. */
const $ = (s, el = document) => el.querySelector(s);
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") el.className = v; else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = v; else if (v !== undefined && v !== null && v !== false) el.setAttribute(k, v);
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) el.append(c.nodeType ? c : document.createTextNode(String(c)));
  return el;
};
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const api = async (path, opts = {}) => {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined });
  const j = await r.json().catch(() => ({}));
  if (!r.ok && !j.denied) throw new Error(j.detail || r.statusText);
  return j;
};
const money = c => { if (c === null || c === undefined || c === "") return ""; const n = Number(c) / 100;
  const s = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); return (n < 0 ? "−$" : "$") + s; };
const hhmmss = t => (t || "").slice(11, 19);

const LEVELS = { info: "INFO", fix: "FIX", find: "FIND", warn: "WARN", decide: "DECIDE", ask: "ASK", ok: "OK", deny: "DENY",
  sim: "SIM", check: "CHECK", fail: "FAIL" };
const LEVEL_TIPS = { info: "progress", fix: "data cleaned: before → after", find: "something discovered", warn: "needs attention",
  decide: "agent judgement / proposal", ask: "waiting on a human", ok: "stage or action completed", deny: "blocked by policy, logged",
  sim: "simulated external party (vendor, PayPal, QBO…)", check: "tie-out / control", fail: "error" };

const S = { problems: [], accounts: {}, tab: null, runs: {}, sel: {}, cache: {}, art: {}, stageFilter: null,
  levelsOff: new Set(), task: {}, auditMode: false };

/* ------------------------------------------------------------------ boot */
async function boot() {
  const p = await api("/api/wb/problems");
  S.problems = p.problems; S.accounts = p.accounts || {};
  for (const r of await api("/api/wb/runs")) addRun(r);
  buildTabs(); buildFilters();
  selectTab(location.hash.slice(1) || S.problems[0].id);
  verifyChain();
  const es = new EventSource("/events");
  es.onmessage = e => { const ev = JSON.parse(e.data); if (ev.type === "wb") onEvent(ev); };
  $("#go").onclick = () => startRun(problem().agents[0]);
  $("#late").onclick = () => startRun("p2_late", "QBO changed after I downloaded the exports (AJE-0930-04 posted late). Re-download is in late_change/. Refresh the package, show me exactly what changed, and re-tie.");
  $("#runPick").onchange = e => { S.sel[S.tab] = e.target.value; loadRun(e.target.value); };
  $("#taskText").oninput = e => S.task[S.tab] = e.target.value;
  $("#chain").onclick = verifyChain;
  $("#reset").onclick = async () => { if (!confirm("Reset the workbench? All runs and the audit chain are wiped.")) return;
    await api("/api/wb/reset", { method: "POST" }); location.reload(); };
  $("#speed").oninput = e => api("/api/wb/speed", { method: "POST", body: { value: Number(e.target.value) } });
  $("#mClose").onclick = closeModal;
  $("#modal").onclick = e => { if (e.target.id === "modal") closeModal(); };
  document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });
  document.querySelector(".hero").addEventListener("click", e => { const t = e.target.closest(".pillar"); if (t) openPillar(t.dataset.k); });
  $("#auditRun").onchange = e => loadAudit(e.target.value);
  $("#auditVerify").onclick = async () => { const v = await verifyChain(); $("#auditMsg").textContent = v.ok ?
    `✓ ${v.rows} rows re-hashed, chain intact · head ${v.head.slice(0, 16)}…` : `✗ chain broken at row ${v.broken_at}`; };
  checkLLMStatus();
  $("#llm-badge").onclick = checkLLMStatus;
}

async function checkLLMStatus() {
  const badge = $("#llm-badge");
  badge.textContent = "LLM: testing…";
  badge.className = "chip llm-badge";
  try {
    const status = await api("/api/llm_status");
    if (status.status === "live") {
      badge.textContent = `LLM: ✓ LIVE`;
      badge.className = "chip llm-badge live";
      badge.title = `Claude ${status.model || "connected"} — real LLM responses`;
    } else {
      badge.textContent = `LLM: deterministic`;
      badge.className = "chip llm-badge fallback";
      const reason = status.reason ? ` (${status.reason})` : "";
      badge.title = `Using deterministic templates${reason} — no API key or connection failed. System still fully functional.`;
    }
  } catch (e) {
    badge.textContent = "LLM: error";
    badge.className = "chip llm-badge error";
    badge.title = `Error checking LLM: ${e.message}`;
  }
}
const problem = () => S.problems.find(p => p.id === S.tab);
function problemOfAgent(agent) { return S.problems.find(p => p.agents.includes(agent))?.id; }
function addRun(r) {
  const pid = r.problem; (S.runs[pid] ||= []);
  if (!S.runs[pid].find(x => x.id === r.id)) S.runs[pid].push(r); else Object.assign(S.runs[pid].find(x => x.id === r.id), r);
  if (!S.sel[pid]) S.sel[pid] = r.id;
}

/* ------------------------------------------------------------------ tabs */
function buildTabs() {
  const nav = $("#tabs"); nav.innerHTML = "";
  S.problems.forEach((p, i) => nav.append(h("button", { class: "tab", "data-id": p.id, onclick: () => selectTab(p.id) },
    h("span", { class: "num" }, `0${i + 1}`), h("span", { class: "ico" }, p.icon), p.tab, h("span", { class: "badge", id: `b-${p.id}` }, "idle"))));
  nav.append(h("button", { class: "tab", "data-id": "audit", onclick: () => selectTab("audit") },
    h("span", { class: "ico" }, "⛓"), "Audit trail"));
  updateBadges();
}
function updateBadges() {
  for (const p of S.problems) {
    const runs = S.runs[p.id] || []; const last = runs[runs.length - 1]; const b = $(`#b-${p.id}`);
    if (!b) continue; const st = last ? last.status : "idle";
    b.className = `badge ${st}`; b.textContent = { idle: "idle", queued: "queued", running: "running", awaiting_approval: "approve",
      done: "done", failed: "failed", superseded: "superseded" }[st] || st;
  }
}
function selectTab(id) {
  location.hash = id;
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("on", t.dataset.id === id));
  S.auditMode = id === "audit";
  $("#main").classList.toggle("hidden", S.auditMode); $("#auditView").classList.toggle("hidden", !S.auditMode);
  if (S.auditMode) return showAudit();
  S.tab = id; S.stageFilter = null;
  const p = problem();
  $("#eyebrow").textContent = p.eyebrow || "";
  $("#h1").replaceChildren(p.headline[0] + " ", h("span", {}, p.headline[1]));
  $("#problemText").textContent = p.problem;
  $("#pain").replaceChildren(...p.pain.map(x => h("span", {}, x)));
  $("#taskText").value = S.task[id] ?? p.default_task;
  $("#late").classList.toggle("hidden", id !== "p2_rollforward");
  renderFiles(p);
  renderRunPick();
  const rid = S.sel[id];
  if (rid) loadRun(rid); else renderEmptyRun(p);
  renderPillars(rid ? S.cache[rid] : null);
}
function renderFiles(p) {
  $("#fileCount").textContent = `${p.files.length} files`;
  const list = $("#fileList"); list.innerHTML = "";
  for (const f of p.files) {
    const ext = f.split(".").pop().toLowerCase(); const parts = f.split("/"); const name = parts.pop();
    list.append(h("div", { class: "file", title: f, onclick: () => openRaw(p.id, f) },
      h("span", { class: `ext ${ext}` }, ext), h("span", {}, h("span", { class: "dir" }, parts.length ? parts.join("/") + "/" : ""), name)));
  }
}
function renderRunPick() {
  const sel = $("#runPick"); const runs = S.runs[S.tab] || [];
  sel.replaceChildren(...(runs.length ? runs.slice().reverse().map(r => h("option", { value: r.id, selected: r.id === S.sel[S.tab] || undefined },
    `${r.id} · ${r.title.replace(/^.*?—\s*/, "")} · ${r.status}`)) : [h("option", {}, "no runs yet")]));
}
function renderEmptyRun(p) {
  $("#runStatus").className = "status"; $("#runStatus").textContent = "idle"; $("#runMeta").textContent = "";
  const spec = p.agent_specs[0];
  $("#pipeline").replaceChildren(...spec.stages.map(([k, t], i) => stageEl({ key: k, title: t, status: "pending", counts: {} }, i)));
  $("#log").innerHTML = `<div class="empty">Task the agent to watch it work. Every action, every fix and every decision lands here — and in the audit chain.</div>`;
  $("#proposals").innerHTML = `<div class="empty">Nothing touches the books until a human approves it here. Only the Gateway writes.</div>`;
  $("#propCount").textContent = "";
  $("#artTabs").innerHTML = ""; $("#artBody").innerHTML = `<div class="empty">Cleaned tables, before → after diffs, folder trees and workbooks appear here.</div>`;
}

/* ------------------------------------------------------------------ runs */
async function startRun(agent, instr) {
  $("#go").disabled = true;
  try {
    const r = await api("/api/wb/run", { method: "POST", body: { agent, instructions: instr || $("#taskText").value } });
    r.problem = problemOfAgent(agent) || r.problem;
    addRun(r); S.sel[S.tab] = r.id; S.cache[r.id] = { ...r, logs: [] }; S.stageFilter = null;
    renderRunPick(); renderRun(S.cache[r.id]); updateBadges();
  } finally { setTimeout(() => $("#go").disabled = false, 600); }
}
async function loadRun(id) {
  const r = await api(`/api/wb/run/${id}`); S.cache[id] = r; if (S.sel[S.tab] === id) renderRun(r);
}
function current() { return S.cache[S.sel[S.tab]]; }
function renderRun(r) {
  if (!r) return;
  $("#runStatus").className = `status ${r.status}`; $("#runStatus").textContent = r.status.replace("_", " ");
  $("#runMeta").textContent = `${r.id} · started ${hhmmss(r.started)} UTC`;
  renderPipeline(r); renderLogs(r); renderProposals(r); renderArtTabs(r); renderPillars(r);
  $("#footRun").textContent = `${r.id} · ${(r.logs || []).length} audit rows`;
}
function stageEl(s, i) {
  const c = Object.entries(s.counts || {}).slice(0, 2).map(([k, v]) => `${v} ${k.replace(/_/g, " ")}`).join(" · ");
  const icon = { done: "✓", flag: "!", waiting: "…", failed: "✗" }[s.status] || i + 1;
  return h("div", { class: `stage ${s.status} ${S.stageFilter === s.key ? "sel" : ""}`, title: (s.summary || s.title) + (s.seconds ? ` · ${s.seconds}s` : "") + " — click to filter the log",
    onclick: () => { S.stageFilter = S.stageFilter === s.key ? null : s.key; const r = current(); if (r) { renderPipeline(r); renderLogs(r); } } },
    h("div", { class: "node" }, icon), h("div", { class: "wire" }), h("div", { class: "label" }, s.title), h("div", { class: "cnt" }, c));
}
function renderPipeline(r) { $("#pipeline").replaceChildren(...r.stages.map(stageEl)); }

function buildFilters() {
  const f = $("#filters");
  for (const [lv, lab] of Object.entries(LEVELS)) f.append(h("button", { class: `lv-${lv}`, title: LEVEL_TIPS[lv],
    onclick: e => { S.levelsOff.has(lv) ? S.levelsOff.delete(lv) : S.levelsOff.add(lv); e.target.classList.toggle("off"); const r = current(); if (r) renderLogs(r); } }, lab));
}
function logEl(e) {
  const hasData = e.data !== null && e.data !== undefined;
  const auditBadge = h("span", { 
    class: "audit-badge", 
    title: `Click to view audit row #${e.audit_seq || '?'}\nsha256 ${e.hash || '?'}`,
    onclick: () => { selectTab("audit"); setTimeout(() => { 
      const row = document.querySelector(`#auditTable tr[data-seq="${e.audit_seq}"]`);
      if (row) { row.scrollIntoView({ behavior: "smooth", block: "center" }); row.classList.add("highlight"); 
        setTimeout(() => row.classList.remove("highlight"), 2000); }
    }, 100); }
  }, `audit #${e.audit_seq || '?'} · ${String(e.hash || "").slice(0, 6)}`);
  
  const el = h("div", { class: `ln ${e.msg.startsWith("▶") ? "stagehead" : ""} ${hasData ? "hasdata" : ""} ${e.level === "deny" ? "deny" : ""} ${e.moment ? "mom" : ""}`, "data-seq": e.seq, "data-audit": e.audit_seq },
    h("span", { class: "seq", title: `Log #${e.seq}` }, e.seq), h("span", { class: "tm" }, hhmmss(e.t)),
    h("span", { class: `lv lv-${e.level}`, title: LEVEL_TIPS[e.level] }, e.level),
    h("span", { class: "msg" }, e.moment ? h("span", { class: `tag ${e.moment}`, title: "a moment: " + e.moment }, "★ " + e.moment) : null, e.msg),
    auditBadge);
  if (hasData) el.querySelector(".msg").onclick = () => {
    const d = el.querySelector(".data"); if (d) return d.remove();
    el.append(h("div", { class: "data" }, JSON.stringify(e.data, null, 2)));
  };
  return el;
}
const visible = e => !S.levelsOff.has(e.level) && (!S.stageFilter || e.stage === S.stageFilter);
function renderLogs(r) {
  const box = $("#log"); const logs = (r.logs || []).filter(visible);
  if (!logs.length) { box.innerHTML = `<div class="empty">${r.status === "queued" || r.status === "running" ? "Agent starting…" : "No log lines match the filter."}</div>`; return; }
  box.replaceChildren(...logs.map(logEl)); box.scrollTop = box.scrollHeight;
}
function appendLog(r, e) {
  const box = $("#log"); if (!visible(e)) return;
  const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
  box.querySelector(".empty")?.remove(); box.append(logEl(e));
  if (nearBottom) box.scrollTop = box.scrollHeight;
}

/* ------------------------------------------------------------------ live events */
const refreshers = {};
let chainT; const chainSoon = () => { clearTimeout(chainT); chainT = setTimeout(verifyChain, 700); };
function refreshSoon(id, ms = 250) { clearTimeout(refreshers[id]); refreshers[id] = setTimeout(async () => {
  const r = await api(`/api/wb/run/${id}`); S.cache[id] = r; addRun(r); updateBadges();
  if (S.sel[S.tab] === id && !S.auditMode) { renderProposals(r); renderArtTabs(r); renderPipeline(r); renderPillars(r);
    $("#runStatus").className = `status ${r.status}`; $("#runStatus").textContent = r.status.replace("_", " "); renderRunPick(); }
}, ms); }
function onEvent(ev) {
  if (ev.kind === "reset") return location.reload();
  const id = ev.run_id; const r = S.cache[id];
  if (ev.kind === "log" && r) {
    if (!r.logs.find(x => x.seq === ev.entry.seq)) { r.logs.push(ev.entry); if (S.sel[S.tab] === id && !S.auditMode) appendLog(r, ev.entry);
      if (ev.entry.moment) { (r.moments ||= []).push({ kind: ev.entry.moment, seq: ev.entry.seq, stage: ev.entry.stage, msg: ev.entry.msg });
        if (S.sel[S.tab] === id && !S.auditMode) renderPillars(r); } }
    if (ev.entry.level === "decide" || ev.entry.level === "ok" || ev.entry.level === "deny") refreshSoon(id, 400);
    chainSoon();
  } else if (ev.kind === "stage" && r) {
    const i = r.stages.findIndex(s => s.key === ev.stage.key); if (i >= 0) r.stages[i] = ev.stage;
    if (S.sel[S.tab] === id && !S.auditMode) renderPipeline(r);
  } else if (ev.kind === "status") {
    const pid = problemOfAgent(ev.problem) || ev.problem;
    const run = (S.runs[pid] || []).find(x => x.id === id); if (run) run.status = ev.status;
    if (r) r.status = ev.status; updateBadges(); refreshSoon(id, 100); chainSoon();
  } else if (ev.kind === "artifact") refreshSoon(id, 300);
}

/* ------------------------------------------------------------------ proposals */
function jeTable(lines) {
  const acct = a => `${a} ${S.accounts[a] ? "· " + S.accounts[a] : ""}`;
  let dr = 0, cr = 0;
  const rows = lines.map(l => { const c = Number(l.cents); if (c > 0) dr += c; else cr -= c;
    return h("tr", {}, h("td", {}, acct(l.acct)), h("td", { class: "n" }, c > 0 ? money(c) : ""), h("td", { class: "n" }, c < 0 ? money(-c) : ""),
      h("td", { class: "memo" }, l.memo || "")); });
  rows.push(h("tr", {}, h("td", { class: "memo" }, dr === cr ? "balanced ✓" : "UNBALANCED"), h("td", { class: "n" }, money(dr)), h("td", { class: "n" }, money(cr)), h("td")));
  return h("table", { class: "je" }, h("tr", {}, h("th", {}, "Account"), h("th", { class: "n" }, "Debit"), h("th", { class: "n" }, "Credit"), h("th", {}, "Memo")), rows);
}
function proposalBody(p) {
  const pr = p.proposal || {}; const box = h("div");
  if (pr.lines) {
    box.append(h("div", { class: "kv" }, h("div", {}, h("b", {}, "date"), pr.date || "2026-09-30"),
      pr.auto_reverse ? h("div", {}, h("b", {}, "reverses"), pr.auto_reverse + " (auto)") : null));
    box.append(jeTable(pr.lines));
  } else if (pr.kind === "vendor_merge") {
    box.append(h("div", { class: "kv" }, h("div", {}, h("b", {}, "keep"), pr.master), h("div", {}, h("b", {}, "merge in"), pr.aliases.join(", "))));
  } else if (pr.kind === "vendor_rules") {
    box.append(h("table", { class: "je" }, pr.rules.map(x => h("tr", {}, h("td", { class: "memo" }, x.when), h("td", { class: "memo" }, "→ " + x.then)))));
  } else if (pr.kind === "file_evidence") {
    box.append(h("table", { class: "je" }, pr.plan.map(x => h("tr", {}, h("td", { class: "memo" }, x.from), h("td", { class: "memo" }, "→ " + x.to.split("/").slice(-1)[0])))));
  } else if (pr.kind === "package_publish") {
    box.append(h("div", { class: "kv" }, h("div", {}, h("b", {}, "file"), pr.file), h("div", {}, h("b", {}, "to"), "Drive › Finance › Financial Packages › 2026-09 (FINAL)")));
  } else if (pr.amount_cents) {
    box.append(h("div", { class: "kv" }, h("div", {}, h("b", {}, "amount"), money(pr.amount_cents)), h("div", {}, h("b", {}, "bank line"), pr.bank_line)));
  }
  return box;
}
function renderProposals(r) {
  const box = $("#proposals"); const ps = r.proposals || [];
  const open = ps.filter(p => p.state === "PROPOSED").length;
  $("#propCount").textContent = ps.length ? `${open} open · ${ps.length} total` : "";
  if (!ps.length) { box.innerHTML = `<div class="empty">${r.status === "running" ? "The agent will put proposed changes here. Nothing touches the books without your approval." : "No proposals from this run."}</div>`; return; }
  box.replaceChildren(...ps.map(p => {
    const card = h("div", { class: `prop ${p.state}` },
      h("div", { class: "pt" }, h("div", {}, h("div", { class: "pk" }, `${p.kind.replace(/_/g, " ")} · ${p.item_id}`), p.title), h("span", { class: `state ${p.state}` }, p.state)),
      h("div", { class: "why" }, p.rationale),
      p.question ? h("div", { class: "q" }, "❓ " + p.question) : null,
      proposalBody(p),
      h("div", { class: "conf" }, `confidence ${Math.round((p.confidence || 0) * 100)}%` + (p.proposal?.escalate ? " · escalated to a human" : "")),
      defenseEl(p.item_id));
    if (p.state === "PROPOSED") {
      const inp = h("input", { placeholder: p.question ? "Your answer (becomes the memo + audit reason)…" : "Reason (required to reject; e.g. 'use $13,500')" });
      const msg = h("div", { class: "denied" });
      const act = async (d) => {
        if (d === "reject" && !inp.value.trim()) { inp.focus(); inp.style.borderColor = "var(--red)"; return; }
        const res = await api(`/api/wb/item/${p.item_id}/${d}`, { method: "POST", body: { reason: inp.value } }).catch(e => ({ denied: true, reason: e.message }));
        if (res.denied) msg.textContent = `⛔ DENIED in code: ${res.reason} — logged to the audit chain, nothing changed.`;
        refreshSoon(r.id, 150);
      };
      card.append(h("div", { class: "act" }, inp,
        h("button", { class: "ok-btn", onclick: () => act("approve"), title: "Approve as Maya (Controller). The Gateway applies it." }, p.question ? "Answer & approve" : "Approve"),
        h("button", { class: "no-btn", onclick: () => act("reject") }, "Reject"),
        h("button", { class: "ch-btn", onclick: () => toggleChallenge(card, p, r), title: "Question the decision. The agent defends it from its evidence, and every point is logged" }, "Challenge"),
        h("button", { class: "self-btn", onclick: () => act("self-approve"), title: "Demonstrates separation of duties: the agent cannot approve its own work" }, "agent self-approve?")), msg);
    } else if (p.approved_by || p.answer) {
      card.append(h("div", { class: "after" }, `${p.state === "REJECTED" ? "rejected" : "approved by " + (p.approved_by || "maya")}${p.answer ? " · “" + p.answer + "”" : ""}`));
    }
    return card;
  }));
}

const CHALLENGES = {
  accrual: "Why not just wait for the invoice and book it in October?",
  bank_categorize: "Why not just expense it all like we always do with PayPal? It's under materiality.",
  vendor_merge: "Are you sure these are the same company? The names are different.",
  vendor_rules: "Why do we need rules? Just merge them.",
  file_evidence: "Why not just upload everything in Downloads?",
  package_publish: "Why not just send the version we already have?",
  question: "Why not just book it to crew costs? It's probably the stagehand.",
};
const DEFENSES = {};
function toggleChallenge(card, p, r) {
  const ex = card.querySelector(".chbox"); if (ex) return ex.remove();
  const inp = h("input", { value: CHALLENGES[p.kind] || "Why?" });
  const go = async () => {
    btn.disabled = true; btn.textContent = "defending…";
    const res = await api(`/api/wb/item/${p.item_id}/challenge`, { method: "POST", body: { question: inp.value } });
    DEFENSES[p.item_id] = { q: inp.value, points: res.points || [] };
    refreshSoon(r.id, 100);
  };
  const btn = h("button", { class: "ch-btn", onclick: go }, "Ask");
  card.querySelector(".act").after(h("div", { class: "chbox" }, inp, btn));
  inp.focus(); inp.select();
}
function defenseEl(id) {
  const d = DEFENSES[id]; if (!d) return null;
  return h("div", { class: "defense" }, h("div", { class: "dq" }, `▸ maya: “${d.q}”`), h("ol", {}, d.points.map(x => h("li", {}, x))));
}

/* ------------------------------------------------------------------ pillars: the four judging questions, answered per run */
function renderPillars(r) {
  const p = problem(); if (!p) return;
  const pf = r && r.proof; const logs = (r && r.logs) || []; const moms = (r && r.moments) || [];
  const cnt = k => moms.filter(m => m.kind === k).length;
  const asks = logs.filter(e => e.level === "ask").length; const denied = logs.filter(e => e.level === "deny").length;
  const tiles = [
    { k: "real", q: "is it real enough?", v: pf ? `${pf.jarvis}/${pf.total} correct` : "—", s: pf ? `baseline ${pf.baseline}/${pf.total} · ${pf.baseline_name.split(" (")[0]}` : "run the agent to score it", hot: !!pf },
    { k: "hire", q: "would you hire it?", v: p.seat.split(":")[0], s: r ? `read-only · ${asks} asks · ${denied} denied · ${logs.length} logged` : "read-only · proposes, never posts" },
    { k: "new", q: "something new?", v: p.new_short, s: "click for the approach" },
    { k: "moment", q: "the moment", v: r ? `${cnt("caught")} caught` + (cnt("recovered") ? ` · ${cnt("recovered")} recovered` : "") : "—", s: r ? `${cnt("recovered")} recovered · ${cnt("asked")} asked · ${cnt("defended")} defended` : "catch · recover · defend", hot: moms.length > 0 },
  ];
  $("#pillars").replaceChildren(...tiles.map((t, i) => h("button", { class: `pillar ${t.hot ? "hot" : ""}`, "data-k": t.k, title: t.v },
    h("div", { class: "q" }, h("b", {}, `0${i + 1}`), " · " + t.q), h("div", { class: "v" }, t.v), h("div", { class: "s" }, t.s))));
}
function openSmall(kind, title, ...kids) {
  $("#mKind").textContent = kind; $("#mTitle").textContent = title; $("#mMess").textContent = "";
  $("#mBody").replaceChildren(...kids); $(".modalbox").classList.add("small"); openModal();
}
function openPillar(k) {
  const p = problem(); const r = current();
  if (k === "real") {
    if (!r || !r.proof) return openSmall("01 · is it real enough?", "Run the agent to score it against the answer key.", h("p", {}, "Every run is scored against an answer key written by whoever designed the messy data, next to the way it's usually done without an agent."));
    return openSmall("01 · is it real enough? proof against the answer key", `Jarvis ${r.proof.jarvis}/${r.proof.total} · ${r.proof.baseline_name} ${r.proof.baseline}/${r.proof.total}`, proofEl(r.proof));
  }
  if (k === "hire") {
    const logs = (r && r.logs) || [];
    const props = (r && r.proposals) || [];
    return openSmall("02 · would you hire it?", p.seat, h("dl", { class: "hire" },
      h("dt", {}, "seat"), h("dd", {}, p.seat),
      h("dt", {}, "can read"), h("dd", {}, p.reads),
      h("dt", {}, "can write"), h("dd", {}, p.writes),
      h("dt", {}, "asks when"), h("dd", {}, p.asks),
      h("dt", {}, "record"), h("dd", {}, r ? `${logs.length} log lines, each a hash-chained audit row · ${props.length} proposals (${props.filter(x => x.state === "POSTED").length} applied, ${props.filter(x => x.state === "REJECTED").length} rejected) · ${logs.filter(e => e.level === "ask").length} times it stopped to ask · ${logs.filter(e => e.level === "deny").length} denied attempts` : "run the agent"),
      h("dt", {}, "limits in code"), h("dd", {}, "Role ai_agent may propose, ask, revise or withdraw — never approve or post. Requester ≠ approver. Only the Gateway writes, and only after a human approves. Try 'agent self-approve?' on any proposal.")));
  }
  if (k === "new") return openSmall("03 · did we see something new?", p.tab, h("p", { class: "newtext" }, p.new),
    h("p", { class: "muted" }, "Across all five tabs, every stage is logged, every fix shows before → after, and every decision can be challenged."));
  if (k === "moment") {
    const moms = (r && r.moments) || [];
    if (!moms.length) return openSmall("04 · the moment", "Run the agent, then come back.", h("p", {}, "Moments are the log lines where it catches what others missed, recovers from something going wrong, stops to ask, or defends a decision when questioned (press Challenge on a proposal)."));
    return openSmall("04 · the moment", `${moms.length} moments in ${r.id}`, h("div", { class: "momlist" }, moms.map(m =>
      h("button", { onclick: () => { closeModal(); jumpTo(m.seq); } }, h("span", { class: `k ${m.kind}` }, m.kind), `#${m.seq} · ${m.msg}`))));
  }
}
function jumpTo(seq) {
  S.stageFilter = null; S.levelsOff.clear(); document.querySelectorAll("#filters button").forEach(b => b.classList.remove("off"));
  const r = current(); renderPipeline(r); renderLogs(r);
  const el = document.querySelector(`.ln[data-seq="${seq}"]`); if (!el) return;
  el.scrollIntoView({ block: "center", behavior: "smooth" }); el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
}
function proofEl(pf) {
  return h("div", {},
    h("div", { class: "prooftop" },
      h("div", { class: "j" }, h("div", { class: "lab" }, "Jarvis"), h("div", { class: "big" }, `${pf.jarvis} / ${pf.total}`)),
      h("div", {}, h("div", { class: "lab" }, "baseline"), h("div", { class: "big" }, `${pf.baseline} / ${pf.total}`), h("div", { class: "muted" }, pf.baseline_name))),
    h("table", { class: "t" }, h("tr", {}, ["check", "answer key", "jarvis", "", "baseline", ""].map(x => h("th", {}, x))),
      pf.rows.map(x => h("tr", {}, h("td", {}, x.check), h("td", {}, x.answer_key), h("td", {}, x.jarvis),
        h("td", { class: x.jarvis_pass ? "pass" : "failc" }, x.jarvis_pass ? "✓" : "✗"), h("td", {}, x.baseline),
        h("td", { class: x.baseline_pass ? "pass" : "failc" }, x.baseline_pass ? "✓" : "✗")))));
}

/* ------------------------------------------------------------------ artifacts */
function renderArtTabs(r) {
  const tabs = $("#artTabs"); const arts = r.artifacts || [];
  if (!arts.length) { tabs.innerHTML = ""; $("#artBody").innerHTML = `<div class="empty">${r.status === "running" ? "Artifacts will appear as each stage finishes." : "No artifacts."}</div>`; return; }
  const sel = S.art[r.id] && arts.find(a => a.id === S.art[r.id]) ? S.art[r.id] : arts[arts.length - 1].id;
  const prevSel = tabs.dataset.sel, prevN = tabs.childElementCount;
  tabs.replaceChildren(...arts.map(a => h("button", { class: (a.id === sel ? "on " : "") + (a.kind === "proof" ? "prooft" : ""), title: `${a.title} (stage: ${a.stage})`,
    onclick: () => { S.art[r.id] = a.id; renderArtTabs(r); } }, h("span", { class: "k" }, a.kind), a.title)));
  if (prevSel !== `${r.id}:${sel}` || prevN !== arts.length) { tabs.dataset.sel = `${r.id}:${sel}`; showArtifact(r, sel); }
}
async function showArtifact(r, aid) {
  const a = await api(`/api/wb/artifact/${r.id}/${aid}`); const body = $("#artBody"); const p = a.payload;
  const stage = r.stages.find(s => s.key === a.stage);
  const meta = h("div", { class: "artmeta" }, `${a.id} · ${a.kind} · produced in stage “${stage ? stage.title : a.stage}”`);
  if (a.kind === "table") body.replaceChildren(meta, h("div", { class: "tablewrap" }, dataTable(p.columns, p.rows)));
  else if (a.kind === "diff") body.replaceChildren(meta, h("div", { class: "muted", style: "margin-bottom:6px" }, `${p.rows.length} changes — every one is also a FIX line in the log`),
    ...p.rows.map(d => h("div", { class: "diffrow" }, h("div", { class: "dh" }, h("span", {}, d.row !== undefined ? `row ${d.row}` : (d.cell || d.where || "")), h("span", { class: "w" }, d.why || "")),
      h("div", { class: "b" }, d.before ?? ""), h("div", { class: "a" }, d.after ?? ""))));
  else if (a.kind === "proof") body.replaceChildren(meta, proofEl(p));
  else if (a.kind === "tree") body.replaceChildren(meta, treeEl(p.lines));
  else if (a.kind === "file") body.replaceChildren(meta, h("div", { class: "filecard" }, h("span", { style: "font:600 13px DM Mono,monospace;color:#fff;background:#791515;padding:8px 9px;border-radius:6px" }, "xlsx"),
    h("div", {}, h("div", { style: "font-weight:600" }, a.title), h("a", { href: p.url, download: "" }, "Download workbook ↓"),
      h("div", { class: "muted" }, "Draft until the Controller approves; the Gateway then files it as FINAL."))));
  else body.replaceChildren(meta, h("pre", { class: "raw" }, JSON.stringify(p, null, 2)));
}
function dataTable(cols, rows) {
  const isMoneyCol = c => /cents$/.test(c);
  const fmt = (c, v) => { if (isMoneyCol(c) && v !== "" && v !== null && !isNaN(v)) return money(v);
    if (v !== null && typeof v === "object") return JSON.stringify(v); return v ?? ""; };
  return h("table", { class: "t" }, h("tr", {}, cols.map(c => h("th", {}, c.replace(/_cents$/, "").replace(/_/g, " ")))),
    rows.map(row => h("tr", {}, cols.map(c => { const v = row[c]; const s = String(fmt(c, v));
      const cls = (typeof v === "number" || isMoneyCol(c) || /^[−\-]?\$[\d,]/.test(s)) ? "n" : "";
      const pf = /^(pass|✓|ok|tied)/i.test(s) ? "pass" : /^(fail|✗|missing|MISSING)/i.test(s) ? "failc" : "";
      return h("td", { class: `${cls} ${pf}` }, s); }))));
}
function treeEl(lines) {
  const root = {};
  for (const l of lines) { let n = root; for (const part of l.split("/")) n = (n[part] ||= {}); }
  const out = [];
  const walk = (n, pre) => { const ks = Object.keys(n); ks.forEach((k, i) => { const last = i === ks.length - 1; const leaf = !Object.keys(n[k]).length;
    out.push(`${pre}${last ? "└─ " : "├─ "}${leaf ? `<span class="leaf">${esc(k)}</span>` : esc(k) + "/"}`); walk(n[k], pre + (last ? "   " : "│  ")); }); };
  walk(root, "");
  return h("div", { class: "tree", html: out.join("\n") });
}

/* ------------------------------------------------------------------ raw file viewer: show the mess */
const WORDNUM = /^(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)$/i;
function suspect(v) {
  const s = String(v ?? ""); if (!s) return null; const t = s.trim();
  if (s !== t && t) return "leading/trailing spaces";
  if (/^\(\$?[\d,]+(\.\d+)?\)$/.test(t)) return "negative in parentheses";
  if (/\d[O]|[O]\d/.test(t) && /\d/.test(t) && !/[a-np-z]/.test(t)) return "OCR: letter O instead of zero";
  if (/^\$[\d,]/.test(t) || /^-\$/.test(t)) return "currency symbol in a number";
  if (/^\d+(\.\d+)?\s?(h|hrs?|hours)$/i.test(t)) return "unit suffix in a number";
  if (WORDNUM.test(t)) return "number written as a word";
  if (/^\d{1,2}\/\d{1,2}\/\d{2}$/.test(t)) return "two-digit year";
  if (/^(TOTAL|Total for|Total |GRAND TOTAL)/.test(t)) return "summary row mixed into data";
  if (/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(t)) return "number stored as text with separators";
  if (/^(Accrual Basis|Cash Basis|.*GMT.*|Report run|Page \d)/i.test(t)) return "report header/footer, not data";
  return null;
}
function markText(text) {
  let n = 0;
  const html = esc(text).replace(/(\$?\d[\d,]*O[\d,.O]*|\b(?:around|about|approx\.?|~)\s?\$?\d[\d,.]*k?\b|\b\d{1,2}\/\d{1,2}(?:\/\d{2,4})?\b|\bTBD\b|\bASAP\b)/gi,
    m => { n++; return `<mark class="sus" title="ambiguous / needs cleaning">${m}</mark>`; });
  return { html, n };
}
const showSpaces = v => { const s = String(v ?? ""); if (!s.trim()) return s;
  return "·".repeat(s.match(/^ */)[0].length) + s.trim() + "·".repeat(s.match(/ *$/)[0].length); };
function rawTable(rows) {
  let n = 0; const seen = new Set();
  const width = Math.max(...rows.map(r => r.length), 1);
  const tbl = h("table", { class: "rawt" }, rows.map((r, i) => {
    const key = r.join("\u0001"); const blank = r.every(c => !String(c).trim());
    const dup = !blank && seen.has(key) && i > 0; seen.add(key); if (blank || dup) n++;
    const tr = h("tr", { class: blank ? "blank" : dup ? "dup" : "", title: blank ? "blank row" : dup ? "exact duplicate of an earlier row" : "" },
      h("td", { class: "rn" }, i + 1));
    for (let c = 0; c < width; c++) { const v = r[c] ?? ""; const why = suspect(v); if (why) n++;
      tr.append(h("td", { class: why ? "sus" : "", title: why || "" }, showSpaces(v))); }
    return tr;
  }));
  return { tbl, n };
}
async function openRaw(pid, path) {
  const d = await api(`/api/wb/raw/${pid}/${encodeURI(path)}`);
  $(".modalbox").classList.remove("small");
  $("#mKind").textContent = `raw input · ${d.kind}${d.bom ? " · UTF-8 BOM" : ""}`; $("#mTitle").textContent = path;
  const body = $("#mBody"); body.innerHTML = "";
  const legend = h("div", { class: "legend" }, h("span", {}, h("i", { style: "background:#fff1e8;outline:1px solid #ffc29f" }), "cell a human would have to clean (hover for why)"),
    h("span", {}, h("i", { style: "background:#fbeaea" }), "duplicate row"), h("span", {}, h("i", { style: "background:#f2ede7" }), "blank row"),
    h("span", {}, "· = stray space"));
  let n = 0;
  if (d.kind === "csv") { const t = rawTable(d.rows); n = t.n; body.append(legend, t.tbl); }
  else if (d.kind === "xlsx") {
    const names = Object.keys(d.sheets); const holder = h("div"); const tabs = h("div", { class: "sheettabs" });
    const show = nm => { const t = rawTable(d.sheets[nm]); holder.replaceChildren(t.tbl); $("#mMess").textContent = `${t.n} things to clean on “${nm}”`;
      tabs.querySelectorAll("button").forEach(b => b.classList.toggle("on", b.textContent === nm)); };
    names.forEach(nm => tabs.append(h("button", { class: "ghost", onclick: () => show(nm) }, nm)));
    body.append(legend, tabs, holder); openModal(); show(names[0]); return;
  } else {
    const m = markText(d.text); n = m.n;
    if (d.kind === "pdf") body.append(h("div", { class: "muted", style: "margin-bottom:8px" }, "Text layer extracted from the PDF (what the agent reads). ",
      h("a", { href: d.url, target: "_blank", style: "color:var(--o1)" }, "open original PDF ↗")));
    body.append(h("div", { class: "raw", html: m.html }));
  }
  $("#mMess").textContent = n ? `${n} things a human would have to clean` : "";
  openModal();
}
function openModal() { $("#modal").classList.remove("hidden"); }
function closeModal() { $("#modal").classList.add("hidden"); }

/* ------------------------------------------------------------------ audit */
async function verifyChain() {
  const v = await api("/api/wb/verify"); const c = $("#chain");
  c.className = `chip ${v.ok ? "ok" : "bad"}`;
  c.textContent = v.ok ? `⛓ chain ✓ ${v.rows} rows · ${String(v.head || "").slice(0, 8)}` : `⛓ chain BROKEN @${v.broken_at}`;
  return v;
}
async function showAudit() {
  const all = Object.values(S.runs).flat().sort((a, b) => (b.started || "").localeCompare(a.started || ""));
  $("#auditRun").replaceChildren(...(all.length ? all.map(r => h("option", { value: r.id }, `${r.id} · ${r.title} · ${r.status}`)) : [h("option", {}, "no runs yet")]));
  if (all.length) loadAudit(all[0].id); else $("#auditTable").innerHTML = `<div class="empty">Run an agent on any tab; every line it logs appears here as a hash-chained row.</div>`;
  verifyChain();
}
async function loadAudit(id) {
  const rows = await api(`/api/wb/audit/${id}`);
  $("#auditMsg").textContent = `${rows.length} rows for ${id}`;
  $("#auditTable").replaceChildren(h("table", { class: "t" },
    h("tr", {}, ["#", "at (UTC)", "actor", "role", "action", "subject", "allowed", "reason", "prev → hash"].map(x => h("th", {}, x))),
    rows.map(r => h("tr", { class: r.allowed ? "" : "deny-row", "data-seq": r.seq }, h("td", { class: "n" }, r.seq), h("td", {}, (r.at || "").slice(11, 23)),
      h("td", {}, r.actor), h("td", {}, r.actor_role), h("td", {}, r.action), h("td", {}, r.subject), h("td", {}, r.allowed ? "✓" : "✗ denied"),
      h("td", {}, r.reason), h("td", { title: `${r.prev_hash}\n→ ${r.hash}` }, `${String(r.prev_hash).slice(0, 6)} → ${String(r.hash).slice(0, 8)}`)))));
}

boot();
