/* JarvisERP · Synapse Trace UI (vanilla JS + 3d-force-graph) */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const money = c => (c < 0 ? '-' : '') + '$' + (Math.abs(c) / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const api = async (path, opts = {}) => {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined });
  const j = await r.json().catch(() => ({}));
  if (!r.ok && !j.denied) toast(j.detail || j.error || r.statusText, 'warn');
  return j;
};

const COLORS = {
  system: '#8FE3FF', actor: '#FFFFFF', person: '#E6F7FF', rec_bank: '#B9A6FF', rec_paypal: '#C7B5FF', rec_ramp: '#A893FF',
  rec_injector: '#FFF58A', doc: '#D9CCFF', bill: '#C0B0F0', policy: '#7CFFC4', precedent: '#4FD8A0', vendor: '#FFD6A5', fx: '#FFF58A',
  ledger: '#FFB38A', ledger_ref: '#FFCBA8', vendor_master: '#FFB38A', denied: '#FF5E8A',
};
const STATE_COLORS = { NEW: '#E6F7FF', PROPOSED: '#FFF58A', NEEDS_INFO: '#FFB38A', APPROVED: '#7CFFC4', POSTED: '#7CFFC4', REJECTED: '#FF8AD8', DISMISSED: '#6B6690' };
const LINK_COLORS = { supports: 'rgba(124,255,196,0.55)', contradicts: 'rgba(255,138,216,0.85)', context: 'rgba(185,166,255,0.18)', policy: 'rgba(124,255,196,0.35)', precedent: 'rgba(79,216,160,0.35)', evidence: 'rgba(79,216,160,0.28)', posted: 'rgba(255,245,138,0.7)', approval: 'rgba(230,247,255,0.55)', revision: 'rgba(255,179,138,0.8)', denied: 'rgba(255,94,138,0.9)' };
const LAYER_X = [-400, -200, 0, 200, 400];

let G, graphData = { nodes: [], links: [] }, nodeIndex = new Map(), selected = null, STATE = {};
const pulses = new Map();

function nodeColor(n) {
  if (n.group === 'item') return STATE_COLORS[n.state] || '#E6F7FF';
  if (n.group === 'policy' && n.state === 'proposed') return '#FFF58A';
  return COLORS[n.group] || '#B9A6FF';
}
function nodeVal(n) {
  const base = { system: 6, actor: 5, item: 3.2, policy: 3, ledger: 2.4, denied: 3, precedent: 1.2, person: 2 }[n.group] || 1.3;
  const p = pulses.get(n.id);
  return p && p > performance.now() ? base * 2.2 : base;
}

function initGraph() {
  G = ForceGraph3D()($('#graph'))
    .backgroundColor('rgba(0,0,0,0)')
    .showNavInfo(false)
    .nodeLabel(n => `<b>${esc(n.label)}</b>${n.state ? `<br><span style="color:${STATE_COLORS[n.state]}">${n.state}</span> ${esc(n.amount || '')}` : ''}${n.detail ? `<br><span style="color:#9C93C2">${esc(String(n.detail).slice(0, 160))}</span>` : ''}`)
    .nodeColor(nodeColor).nodeVal(nodeVal).nodeOpacity(0.92).nodeResolution(14)
    .linkColor(l => LINK_COLORS[l.rel] || 'rgba(185,166,255,0.2)')
    .linkWidth(l => (l.rel === 'contradicts' || l.rel === 'denied') ? 1.2 : l.rel === 'posted' ? 0.9 : 0.35)
    .linkOpacity(0.55)
    .linkDirectionalParticles(l => (l.rel === 'posted' || l.rel === 'contradicts') ? 2 : 0)
    .linkDirectionalParticleWidth(1.6)
    .linkDirectionalParticleColor(l => LINK_COLORS[l.rel] || '#E6F7FF')
    .linkDirectionalParticleSpeed(0.006)
    .linkCurvature(0.12)
    .onNodeClick(n => openNode(n.id))
    .cooldownTicks(120)
    .d3VelocityDecay(0.35);
  G.d3Force('charge').strength(-38);
  G.d3Force('link').distance(l => 60);
  G.cameraPosition({ x: 0, y: 0, z: 1000 });
  const reset = document.createElement('button'); reset.textContent = '⊙ reset view'; reset.className = 'btn'; reset.id = 'resetView';
  reset.onclick = () => G.cameraPosition({ x: 0, y: 0, z: 1000 }, { x: 0, y: 0, z: 0 }, 800); $('#center').appendChild(reset);
  const resize = () => { const r = $('#center').getBoundingClientRect(); G.width(r.width).height(r.height); };
  window.addEventListener('resize', resize); resize();
  setInterval(() => {
    if (!graphData.nodes.length) return;
    const ys = graphData.nodes.map(n => n.y || 0); const top = Math.max(...ys) + 30;
    $$('#layers span').forEach((el, i) => { const c = G.graph2ScreenCoords(LAYER_X[i], top, 0); el.style.left = c.x + 'px'; });
  }, 300);
  setInterval(() => { if (pulses.size) { const now = performance.now(); let live = false; for (const [k, t] of pulses) { if (t < now) pulses.delete(k); else live = true; } G.nodeVal(nodeVal); } }, 250);
}

async function loadGraph() {
  const g = await api('/api/graph');
  const keep = new Map(graphData.nodes.map(n => [n.id, n]));
  const nodes = g.nodes.map(n => {
    const old = keep.get(n.id);
    const fx = LAYER_X[n.layer] ?? 0;
    if (old) { Object.assign(old, n); old.fx = fx; return old; }
    return { ...n, fx, x: fx, y: (Math.random() - .5) * 300, z: (Math.random() - .5) * 300 };
  });
  nodeIndex = new Map(nodes.map(n => [n.id, n]));
  graphData = { nodes, links: g.links.filter(l => nodeIndex.has(l.source.id || l.source) && nodeIndex.has(l.target.id || l.target)) };
  G.graphData(graphData);
}
let gTimer = null;
const refreshGraph = () => { clearTimeout(gTimer); gTimer = setTimeout(loadGraph, 450); };

function pulse(ids) {
  const until = performance.now() + 1800;
  for (const id of ids) {
    for (const cand of [id, `rec:${id}`, `doc:${id}`, `prec:${id}`, `pol:${id}`, `je:${id}`, `vendor:${id}`, `bill:${id}`]) {
      if (nodeIndex.has(cand)) {
        pulses.set(cand, until);
        graphData.links.forEach(l => { const s = l.source.id || l.source, t = l.target.id || l.target; if (s === cand || t === cand) { try { G.emitParticle(l); } catch (e) { } } });
      }
    }
  }
  G.nodeVal(nodeVal);
}

// ------------------------------------------------------------------ panels
async function loadState() {
  STATE = await api('/api/state');
  const s = STATE.status || {}, br = s.bank_rec || {}, st = s.states || {};
  $('#subtitle').textContent = `${STATE.company} · ${STATE.period} close · world date ${STATE.world_date || '—'} · seed ${STATE.seed}`;
  const kv = (k, v, cls = '') => `<div class="kv"><span>${k}</span><span class="${cls}">${v}</span></div>`;
  const pend = (st.PROPOSED || 0) + (st.NEEDS_INFO || 0);
  $('#cockpit').innerHTML = [
    kv('Bank rec (Sep)', br.statement_ending_cents == null ? '—' : (br.ties ? '✅ ties to $0.00' : `${money(br.difference_cents)} open`), br.ties ? 'ok' : 'warn'),
    kv('Unreconciled lines', (s.unreconciled || []).length, (s.unreconciled || []).length ? 'warn' : 'ok'),
    kv('Trial balance', s.trial_balance_ok === undefined ? '—' : (s.trial_balance_ok ? 'balanced' : 'OUT'), s.trial_balance_ok ? 'ok' : 'bad'),
    kv('Posted / proposed', `${st.POSTED || 0} / ${st.PROPOSED || 0}`),
    kv('Waiting on Controller', pend, pend ? 'warn' : 'ok'),
    kv('Needs info', st.NEEDS_INFO || 0),
    kv('Rejected → re-planned', st.REJECTED || 0),
    kv('Policies active', (STATE.policies || []).filter(p => p.status === 'active').length),
    kv('Audit events', STATE.counts?.audit ?? 0),
    kv('Denied attempts', STATE.counts?.denied ?? 0, STATE.counts?.denied ? 'bad' : ''),
    kv('Retrieval', STATE.search?.backend + (STATE.search?.semantic ? ' + semantic' : '')),
    kv('LLM layer', STATE.llm ? 'Claude on' : 'off (deterministic)'),
    kv('PayPal API', STATE.paypal_fault || 'healthy', STATE.paypal_fault ? 'warn' : 'ok'),
  ].join('');
  $('#inboxN').textContent = pend;
  $('#autoctl').checked = STATE.auto_controller;
  $$('header button[data-act]').forEach(b => b.disabled = !!STATE.busy && ['connect', 'onboard', 'close', 'october', 'controller', 'inject'].includes(b.dataset.act));
  const done = { connect: STATE.bootstrapped, onboard: (STATE.policies || []).length > 0, close: (st.POSTED || 0) > 0, october: STATE.phase === 'october' };
  $$('nav.flow button').forEach(b => b.classList.toggle('done', !!done[b.dataset.act]));
  renderPolicies();
}

async function loadInbox() {
  const items = (await api('/api/items')).filter(i => ['PROPOSED', 'NEEDS_INFO'].includes(i.state));
  $('#tab-inbox').innerHTML = items.length ? items.map(i => `
    <div class="item" data-id="${i.item_id}">
      <div class="t"><span class="badge st-${i.state}">${i.state}</span>${esc(i.title)}</div>
      <div class="meta">${i.kind} · conf ${(i.confidence ?? 0).toFixed(2)} · ${esc(i.policy_id || '')}</div>
      ${i.state === 'NEEDS_INFO' ? `<div class="meta" style="color:#FFB38A">? ${esc(i.question)}</div>` : ''}
      ${i.proposal?.escalate ? `<div class="meta" style="color:#FFB38A">⚑ escalated: ${esc(i.question)}</div>` : ''}
      <div class="row">
        ${i.state === 'PROPOSED' ? `<button class="btn go" data-a="approve">Approve</button><button class="btn no" data-a="reject">Reject…</button>` : `<button class="btn" data-a="answer">Answer…</button>`}
        <button class="btn" data-a="open">Dossier</button>
      </div>
    </div>`).join('') : '<div class="empty">Nothing waiting on the Controller.</div>';
  $$('#tab-inbox .item').forEach(el => el.addEventListener('click', async e => {
    const id = el.dataset.id, a = e.target.dataset.a;
    if (!a || a === 'open') return openNode(id);
    if (a === 'approve') await api(`/api/item/${id}/approve`, { method: 'POST', body: { reason: 'Approved in inbox' } });
    if (a === 'reject') { const r = prompt('Reason (include the corrected amount if any, e.g. $2,000.00):'); if (r) await api(`/api/item/${id}/reject`, { method: 'POST', body: { reason: r } }); }
    if (a === 'answer') { const r = prompt('Your answer:'); if (r) await api(`/api/item/${id}/answer`, { method: 'POST', body: { text: r } }); }
    refreshAll();
  }));
}

function renderPolicies() {
  const ps = STATE.policies || [];
  $('#tab-policies').innerHTML = ps.length ? ps.map(p => `
    <div class="item">
      <div class="t"><span class="badge st-${p.status === 'active' ? 'POSTED' : p.status === 'proposed' ? 'PROPOSED' : 'DISMISSED'}">${p.status}</span>${p.policy_id} v${p.version} · ${esc(p.title)}</div>
      <div class="meta">${esc(p.rule_text)}</div>
      <div class="meta">evidence: ${p.evidence.length} precedent(s) · ${esc(JSON.stringify(p.matcher))}${p.approved_by ? ' · approved by ' + p.approved_by : ''}</div>
      ${p.status === 'proposed' ? `<div class="row"><button class="btn go" onclick="decidePolicy('${p.policy_id}',${p.version},'approve')">Approve</button><button class="btn no" onclick="decidePolicy('${p.policy_id}',${p.version},'reject')">Reject</button></div>` : ''}
    </div>`).join('') : '<div class="empty">No policies yet. Run ② Learn the job.</div>';
}
async function decidePolicy(id, v, d) { await api(`/api/policy/${id}/${v}/${d}`, { method: 'POST' }); refreshAll(); }

async function loadMessages() {
  const ms = await api('/api/messages');
  $('#tab-messages').innerHTML = ms.length ? ms.map(m => `<div class="item" onclick="${m.item_id ? `openNode('${m.item_id}')` : ''}"><div class="t">${esc(m.subject)}</div><div class="meta">${esc(m.from_actor)} → ${esc(m.to_actor)} · ${m.at.slice(11, 19)}</div><p style="font-size:12.5px;margin:6px 0 0">${esc(m.body)}</p></div>`).join('') : '<div class="empty">No messages yet.</div>';
}
async function loadAudit() {
  const rows = await api('/api/audit?limit=250');
  $('#tab-audit').innerHTML = `<div class="trail">${rows.map(r => `<div class="${r.allowed ? '' : 'no'}">#${r.seq} ${r.at.slice(11, 19)} <b>${esc(r.actor)}</b> ${esc(r.action)} ${esc(r.subject)} — ${esc((r.reason || '').slice(0, 140))}<br><span class="dim">hash ${r.hash.slice(0, 16)}… ← ${r.prev_hash.slice(0, 10)}…</span></div>`).join('')}</div>`;
}

// ------------------------------------------------------------------ dossier
function tab(name) {
  $$('.tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab === name));
  $$('.tabbody').forEach(b => b.classList.toggle('hidden', b.id !== 'tab-' + name));
  if (name === 'messages') loadMessages();
  if (name === 'audit') loadAudit();
}

async function openNode(id) {
  selected = id; tab('dossier');
  const el = $('#tab-dossier');
  const n = nodeIndex.get(id);
  if (n) { pulse([id]); G.cameraPosition({ x: n.x * 0.6, y: n.y * 0.6, z: 620 }, { x: n.x * 0.6, y: n.y * 0.6, z: 0 }, 900); }
  if (id.startsWith('WI-')) return renderItem(await api(`/api/item/${id}`));
  const r = await api(`/api/node/${encodeURIComponent(id)}`);
  const d = r.data || {};
  let body = `<div class="dossier"><h2>${esc(n?.label || id)}</h2><div class="meta">${r.type}</div>`;
  if (r.type === 'record' && d) body += `<h4>Golden record</h4><table class="je">${Object.entries({ source: d.source, date: d.txn_date, amount: money(d.amount_cents) + ' ' + d.currency, counterparty: d.counterparty, description: d.description, evidence_quality: d.evidence_quality, raw_ref: d.raw_ref }).map(([k, v]) => `<tr><td>${k}</td><td>${esc(v)}</td></tr>`).join('')}</table><h4>Raw row (as landed from the source)</h4><pre class="doc">${esc(JSON.stringify(d.raw, null, 1))}</pre>`;
  else if (r.type === 'doc' && d) body += `<h4>${esc(d.kind)} · ${esc(d.date)}</h4><pre class="doc">${esc(d.text)}</pre>`;
  else if (r.type === 'precedent' && d) body += `<h4>${esc(d.pattern)} · ${esc(d.period)} · ${esc(d.decided_by)}</h4><p>${esc(d.summary)}</p><pre class="doc">${esc(d.decision)}</pre>`;
  else if (r.type === 'policy') body += (r.data || []).map(p => `<h4>${p.policy_id} v${p.version} · ${p.status}</h4><p>${esc(p.rule_text)}</p><p class="meta">evidence: ${esc(p.evidence)}<br>stats: ${esc(p.matcher)}<br>proposed by ${p.proposed_by} · approved by ${p.approved_by || '—'}</p>`).join('');
  else if (r.type === 'ledger' && d) body += `<h4>${esc(d.date)} · ${esc(d.memo)}</h4>${jeTable(d.lines.map(l => ({ acct: l.account, cents: l.amount_cents, memo: l.memo })))}<p class="meta">posted by ${esc(d.posted_by)} · work item ${esc(d.work_item_id || '—')}</p>`;
  else if (r.type === 'vendor' && d) body += `<table class="je">${Object.entries(d).map(([k, v]) => `<tr><td>${k}</td><td>${esc(v)}</td></tr>`).join('')}</table><h4>Aliases</h4>${(r.aliases || []).map(a => `<div class="meta">${esc(a.alias)} (${a.source}${a.work_item_id ? ', ' + a.work_item_id : ''})</div>`).join('')}`;
  else if (r.type === 'denied' && d) body += `<div class="ev contradicts">${esc(d.actor)} tried <b>${esc(d.action)}</b> on ${esc(d.subject)}<small>${esc(d.reason)}</small></div><p class="meta">Denied in code by roles.can() and logged in the same transaction (audit #${d.seq}).</p>`;
  else body += `<pre class="doc">${esc(JSON.stringify(d, null, 1))}</pre>`;
  el.innerHTML = body + '</div>';
}

const ACCT = {};
function jeTable(lines) {
  if (!lines?.length) return '<p class="meta">No journal entry (reconciliation link / master-data change only).</p>';
  let dr = 0, cr = 0;
  const rows = lines.map(l => { if (l.cents > 0) dr += l.cents; else cr -= l.cents; return `<tr><td>${esc(l.acct)}</td><td>${esc(l.memo || '')}</td><td class="n">${l.cents > 0 ? money(l.cents) : ''}</td><td class="n">${l.cents < 0 ? money(-l.cents) : ''}</td></tr>`; }).join('');
  return `<table class="je"><tr><th>Acct</th><th>Memo</th><th>Dr</th><th>Cr</th></tr>${rows}<tr class="tot"><td></td><td>${dr === cr ? 'balanced' : 'OUT OF BALANCE'}</td><td class="n">${money(dr)}</td><td class="n">${money(cr)}</td></tr></table>`;
}

function renderItem(it) {
  const ev = (it.evidence || []).map(e => `<div class="ev ${e.relation}" onclick="openNode('${{ record: 'rec:', doc: 'doc:', precedent: 'prec:', vendor: 'vendor:', ledger: 'je:', bill: 'bill:', fx: 'fx:', person: 'person:' }[e.type] || ''}${e.id}')">${esc(e.label)}<small>${e.relation} · ${e.type} ${esc(e.id)} ${esc(e.detail || '')}</small></div>`).join('');
  const rv = it.review?.checks ? `<div class="checks">${Object.entries(it.review.checks).map(([k, v]) => `<span class="${v ? 'ok' : 'bad'}">${v ? '✓' : '✗'} ${k}</span>`).join('')}</div>` : '';
  const trail = (it.audit || []).map(a => `<div class="${a.allowed ? '' : 'no'}">#${a.seq} ${a.at.slice(11, 19)} <b>${esc(a.actor)}</b> ${esc(a.action)} — ${esc((a.reason || '').slice(0, 160))}</div>`).join('');
  const p = it.proposal || {};
  $('#tab-dossier').innerHTML = `<div class="dossier">
    <h2>${esc(it.title)}</h2>
    <div><span class="badge st-${it.state}">${it.state}</span><span class="badge" style="color:#8FE3FF">${it.kind}</span><span class="badge" style="color:#B9A6FF">conf ${(it.confidence ?? 0).toFixed(2)}</span>${p.escalate ? '<span class="badge" style="color:#FFB38A">escalated</span>' : ''}</div>
    ${it.question ? `<h4>Question / escalation</h4><p style="color:#FFB38A">${esc(it.question)}</p>` : ''}
    ${it.answer ? `<h4>Human answer</h4><p>${esc(it.answer)}</p>` : ''}
    <h4>Why</h4><div class="rationale">${esc(it.rationale || '—')}</div>
    <h4>Proposed entry</h4>${jeTable(p.lines)}
    ${p.vendor ? `<p class="meta">Vendor master: ${esc(p.vendor.action)} alias '${esc(p.vendor.alias)}' → ${esc(p.vendor.vendor_id || p.vendor.new?.vendor_id)}</p>` : ''}
    ${p.extra ? '' : ''}${p.trueup_cents !== undefined ? `<p class="meta">Accrued ${money(p.accrued_cents)} · actual ${money(p.actual_cents)} · true-up ${money(p.trueup_cents)}</p>` : ''}
    <h4>Evidence (${(it.evidence || []).length})</h4>${ev}
    <p class="meta">Policy: ${esc(it.policy_id || '—')} · Precedents: ${esc((it.precedent_ids || []).join(', ') || '—')}</p>
    <h4>Reviewer (separate identity)</h4>${rv}<p class="meta">${esc(it.review?.note || '')}</p>
    <h4>Actions</h4>
    <div class="row">
      ${it.state === 'PROPOSED' ? `<button class="btn go" id="dApprove">Approve as Controller</button><button class="btn no" id="dReject">Reject…</button>` : ''}
      ${it.state === 'NEEDS_INFO' ? `<button class="btn" id="dAnswer">Answer…</button>` : ''}
      ${it.state === 'PROPOSED' ? `<button class="btn warn" id="dSelf" title="Shows the limit: the agent cannot approve its own work">Let Jarvis self-approve (should be denied)</button>` : ''}
    </div>
    <h4>Challenge this decision</h4>
    <textarea class="txt" id="chq" placeholder="e.g. Why not just expense it all to software like we always do with PayPal? It's under materiality."></textarea>
    <div class="row"><button class="btn" id="dChallenge">Challenge Jarvis</button></div>
    <div id="defense"></div>
    <h4>Audit trail — "why?" is one query</h4><div class="trail">${trail}</div>
    ${it.ledger_entry ? `<h4>Ledger entry ${it.ledger_entry.entry_id}</h4><p class="meta">posted by ${it.ledger_entry.posted_by} at ${it.ledger_entry.posted_at}</p>` : ''}
  </div>`;
  const id = it.item_id;
  $('#dApprove')?.addEventListener('click', async () => { await api(`/api/item/${id}/approve`, { method: 'POST', body: { reason: 'Approved in dossier' } }); refreshAll(); openNode(id); });
  $('#dReject')?.addEventListener('click', async () => { const r = prompt('Reason (include the corrected amount if any):'); if (r) { await api(`/api/item/${id}/reject`, { method: 'POST', body: { reason: r } }); refreshAll(); openNode(id); } });
  $('#dAnswer')?.addEventListener('click', async () => { const r = prompt('Your answer:'); if (r) { await api(`/api/item/${id}/answer`, { method: 'POST', body: { text: r } }); refreshAll(); openNode(id); } });
  $('#dSelf')?.addEventListener('click', async () => { const r = await api(`/api/item/${id}/self-approve`, { method: 'POST' }); toast(r.denied ? `DENIED in code: ${r.reason}` : 'allowed?!', r.denied ? 'denied' : 'warn'); refreshAll(); });
  $('#dChallenge').addEventListener('click', async () => {
    const q = $('#chq').value.trim() || $('#chq').placeholder.replace('e.g. ', '');
    $('#defense').innerHTML = '<div class="answer">Jarvis is assembling its defense from the evidence…</div>';
    const r = await api(`/api/item/${id}/challenge`, { method: 'POST', body: { question: q } });
    $('#defense').innerHTML = `<div class="answer">${esc(r.answer)}</div><p class="meta">${r.llm ? 'Written by Claude from the dossier' : 'Deterministic defense from the dossier (no LLM key)'} · logged as audit events 'challenge' + 'defend'</p>`;
    pulse(r.evidence || []);
  });
}

// ------------------------------------------------------------------ modals
function modal(html) { $('#modal-body').innerHTML = html; $('#modal').classList.remove('hidden'); }
function closeModal() { $('#modal').classList.add('hidden'); }

async function showScore() {
  const r = await api('/api/score');
  const s = r.jarvis.summary, b = r.b1;
  const m = (label, v, bv) => `<div class="metric"><div class="v">${Math.round(v * 100)}%</div><div>${label}</div><div class="b">rules baseline: ${Math.round(bv * 100)}%</div></div>`;
  modal(`<h2>Proof it works — answer key vs Jarvis</h2>
    <p class="meta">The world generator planted ${s.items} items (${s.issues} issues + ${s.traps} traps) for phases ${r.phases.join(' + ')}. The agent never reads the key. Baseline = rules-based bank feed (exact-amount match, payee rules, accepts card categories).</p>
    <div class="score-grid">${m('fully correct', s.fully_correct, b.fully_correct)}${m('detection', s.detection_recall, b.detection_recall)}${m('treatment (exact lines)', s.treatment_accuracy, b.treatment_accuracy)}${m('trap precision', s.trap_precision, b.trap_precision)}${m('asked when it should', s.escalation_correct, b.escalation_correct)}</div>
    <table class="score"><tr><th>key</th><th>category</th><th>expected</th><th>got</th><th>ok</th></tr>
    ${r.jarvis.rows.map(x => `<tr><td>${x.key_id}</td><td>${esc(x.category)}</td><td>${x.expected}</td><td>${x.got}</td><td class="${x.ok ? 'ok' : 'bad'}">${x.ok ? '✓' : '✗'}</td></tr>`).join('')}</table>`);
}

function showInject() {
  const t = STATE.templates || {};
  modal(`<h2>⚡ Judge scenario</h2>
    <p class="meta">Type anything — it's mapped onto bounded generator primitives (so the world stays consistent), inserted as new source records, and Jarvis processes it live.</p>
    <textarea class="txt" id="injText" placeholder="e.g. There's an unknown $742.18 debit 'SQ *MOONLIGHT GEAR CO' on 9/29"></textarea>
    <div class="row"><button class="btn go" id="injGo">Inject & run</button></div>
    <h4 style="color:#8FE3FF">or pick a template</h4>
    <div class="tmpl">${Object.entries(t).map(([k, v]) => `<button class="btn" data-t="${k}">${esc(v)}</button>`).join('')}</div>`);
  $('#injGo').onclick = async () => { const text = $('#injText').value.trim(); if (!text) return; await api('/api/inject', { method: 'POST', body: { text } }); closeModal(); toast('Scenario injected — watch the graph'); };
  $$('.tmpl button').forEach(b => b.onclick = async () => { await api('/api/inject', { method: 'POST', body: { template: b.dataset.t } }); closeModal(); toast(`Injected: ${t[b.dataset.t]}`); });
}

async function showPack() {
  const r = await api('/api/closepack', { method: 'POST' });
  modal(`<h2>🗂 Close evidence pack — ${r.period}</h2><p class="meta">${esc(r.root)}</p>
    <p>${r.complete ? '<span class="ok">✅ complete: statement + reconciliation present, rec ties</span>' : `<span class="warn">⚠ incomplete: ${esc(r.missing.join(', ') || 'reconciliation does not tie yet')}</span>`}</p>
    <table class="score"><tr><th>document</th><th>type</th><th>check</th></tr>${r.documents.map(d => `<tr><td>${esc(d.doc)}</td><td>${d.type}</td><td class="${d.verified ? 'ok' : 'warn'}">${esc(d.check)}</td></tr>`).join('')}</table>
    <div class="row"><a class="btn go" href="/api/closepack.zip">Download zip</a><a class="btn" href="/api/export/gl.csv?period=2026-09" target="_blank">GL export (QBO format)</a><a class="btn" href="/api/export/beancount" target="_blank">Beancount ledger</a></div>`);
}

// ------------------------------------------------------------------ toasts, ticker, SSE
function toast(msg, cls = '') { const d = document.createElement('div'); d.className = 'toast ' + cls; d.textContent = msg; $('#toasts').appendChild(d); setTimeout(() => d.remove(), 6000); }
function tick(ev) {
  const d = document.createElement('div');
  d.className = (ev.allowed === false ? 'denied ' : '') + (ev.actor || '') + (/fail|fallback/.test(ev.action) ? ' fault' : '');
  d.textContent = `${ev.allowed === false ? '✗ ' : ''}${ev.actor} · ${ev.action} · ${ev.subject}${ev.reason ? ' — ' + ev.reason : ''}`;
  const t = $('#ticker'); t.prepend(d); while (t.children.length > 9) t.lastChild.remove();
}
let thinkTimer;
function think(text) { const t = $('#think'); t.textContent = text; t.style.display = 'block'; clearTimeout(thinkTimer); thinkTimer = setTimeout(() => t.style.display = 'none', 4000); }

let sTimer;
const refreshAll = () => { clearTimeout(sTimer); sTimer = setTimeout(() => { loadState(); loadInbox(); refreshGraph(); }, 300); };

function connectSSE() {
  const es = new EventSource('/events');
  es.onmessage = m => {
    const ev = JSON.parse(m.data);
    switch (ev.type) {
      case 'audit': tick(ev); pulse([ev.subject, ...(ev.evidence || [])]); if (/^(propose|post|approve|reject|create|dismiss|ask|answer)/.test(ev.action)) refreshAll(); break;
      case 'denied': toast(`DENIED · ${ev.actor} ${ev.action}: ${ev.reason}`, 'denied'); refreshAll(); break;
      case 'focus': think(`Working: ${ev.title}`); break;
      case 'think': think(ev.text); break;
      case 'phase': think(ev.text); toast(ev.text); break;
      case 'policy': refreshAll(); break;
      case 'message': if (ev.to.startsWith('vendor') || ev.to.startsWith('employee')) toast(`✉ ${ev.to}: ${ev.subject}`); break;
      case 'defend': pulse(ev.evidence || []); break;
      case 'sync': toast(`Sync ${ev.phase}: ` + Object.entries(ev.result).filter(([k, v]) => typeof v === 'object').map(([k, v]) => `${k} +${v.new ?? 0}${v.updated ? ' ~' + v.updated : ''}${v.unchanged ? ' =' + v.unchanged : ''}${v.fallback_months?.length ? ' (fallback: ' + v.fallback_months.join(',') + ')' : ''}`).join(' · ')); refreshAll(); break;
      case 'fault': toast(`PayPal API fault: ${ev.mode || 'cleared'}`, 'warn'); loadState(); break;
      case 'error': toast(`Error in ${ev.where}: ${ev.error}`, 'denied'); break;
      case 'inject_done': toast(`Scenario processed: ${ev.result.items.length} item(s)`); if (ev.result.items[0]) openNode(ev.result.items[0].item_id); break;
      case 'busy': case 'refresh': refreshAll(); break;
    }
  };
  es.onerror = () => { es.close(); setTimeout(connectSSE, 2000); };
}

// ------------------------------------------------------------------ wiring
document.addEventListener('DOMContentLoaded', async () => {
  initGraph();
  $('#legend').innerHTML = [['system', 'systems'], ['rec_bank', 'source records'], ['doc', 'documents'], ['policy', 'policies'], ['precedent', 'precedents'], ['fx', 'FX / reference'], ['ledger', 'ledger entries'], ['denied', 'denied attempt']].map(([k, l]) => `<span><i style="color:${COLORS[k]};background:${COLORS[k]}"></i>${l}</span>`).join('') +
    Object.entries(STATE_COLORS).map(([k, c]) => `<span><i style="color:${c};background:${c}"></i>${k.toLowerCase()}</span>`).join('');
  $$('.tabs button').forEach(b => b.onclick = () => tab(b.dataset.tab));
  $$('header button[data-act]').forEach(b => b.onclick = async () => {
    const a = b.dataset.act;
    if (a === 'inject') return showInject();
    if (a === 'score') return showScore();
    if (a === 'pack') return showPack();
    if (a === 'verify') { const r = await api('/api/verify'); return toast(r.ok ? `⛓ Audit chain intact: ${r.rows} events, head ${r.head.slice(0, 12)}…` : `⛓ CHAIN BROKEN at #${r.broken_at}`, r.ok ? '' : 'denied'); }
    if (a === 'resync') { const r = await api('/api/resync', { method: 'POST' }); return toast(`Re-sync: ${Object.entries(r).filter(([k, v]) => typeof v === 'object').map(([k, v]) => `${k} new ${v.new ?? 0} / unchanged ${v.unchanged ?? 0}`).join(' · ')} — no duplicates`); }
    if (a === 'reset') { if (!confirm('Reset to a fresh world?')) return; await api('/api/reset', { method: 'POST', body: {} }); graphData = { nodes: [], links: [] }; G.graphData(graphData); return refreshAll(); }
    if (a === 'controller') return api('/api/controller/run', { method: 'POST' });
    await api('/api/' + a, { method: 'POST' });
  });
  $('#fault').onchange = e => api('/api/fault', { method: 'POST', body: { mode: e.target.value || null } });
  $('#autoctl').onchange = e => api('/api/controller/auto', { method: 'POST', body: { on: e.target.checked } });
  $('#modal').onclick = e => { if (e.target.id === 'modal') closeModal(); };
  connectSSE();
  await loadState(); await loadInbox(); await loadGraph();
});
