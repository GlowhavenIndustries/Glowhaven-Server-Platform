const state = { view: 'overview', me: null, servers: [], jobs: [], pendingAction: null };
const $ = id => document.getElementById(id);
const fmtTime = value => value ? new Date(value).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : 'Never';
const pct = value => `${Math.round(Number(value || 0))}%`;

async function api(path, options = {}) {
  const opts = {...options, headers: {...(options.headers || {})}};
  if (opts.body && typeof opts.body !== 'string') { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(opts.body); }
  if (['POST','PUT','PATCH','DELETE'].includes((opts.method || 'GET').toUpperCase())) {
    const csrf = document.cookie.split('; ').find(x => x.startsWith('helix_csrf='));
    if (csrf) opts.headers['X-CSRF-Token'] = decodeURIComponent(csrf.split('=')[1]);
  }
  const response = await fetch(path, opts);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}
async function checkSession() {
  try { state.me = await api('/api/me'); $('login').classList.add('hidden'); $('app').classList.remove('hidden'); $('identity').textContent = `${state.me.username} · ${state.me.role}`; document.querySelectorAll('.admin-only').forEach(el => el.classList.toggle('hidden', state.me.role !== 'admin')); await loadOverview(); }
  catch { $('login').classList.remove('hidden'); $('app').classList.add('hidden'); }
}
$('login-form').addEventListener('submit', async e => { e.preventDefault(); $('login-error').textContent=''; try { await api('/api/auth/login', {method:'POST', body:{username:$('username').value,password:$('password').value}}); await checkSession(); } catch (err) { $('login-error').textContent = err.message; } });
$('logout').addEventListener('click', async () => { try { await api('/api/auth/logout',{method:'POST'}); } finally { location.reload(); } });
document.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.view)));
function switchView(view) { state.view = view; document.querySelectorAll('.view').forEach(v => v.classList.add('hidden')); $(`${view}-view`).classList.remove('hidden'); document.querySelectorAll('.nav-item').forEach(v => v.classList.toggle('active', v.dataset.view === view)); const titles = {overview:['OPERATIONS','Fleet overview'], fleet:['SERVER INVENTORY','Managed fleet'], jobs:['CONTROLLED OPERATIONS','Operations queue'], audit:['CONTROL TRAIL','Audit events']}; $('view-kicker').textContent = titles[view][0]; $('view-title').textContent = titles[view][1]; if (view==='overview') loadOverview(); if (view==='fleet') loadFleet(); if (view==='jobs') loadJobs(); if (view==='audit') loadAudit(); }
async function loadOverview() { const [summary, servers] = await Promise.all([api('/api/summary'),api('/api/servers')]); state.servers=servers; $('metric-servers').textContent=summary.servers; $('metric-online').textContent=summary.online; $('metric-warning').textContent=summary.warning; $('metric-queued').textContent=summary.queued_jobs; $('metric-online-sub').textContent=`${summary.online} online now`; $('metric-failed-sub').textContent=`${summary.failed_jobs_24h} failed in last 24h`; $('overview-table').innerHTML = servers.slice(0,12).map(serverRow).join('') || `<tr><td colspan="7" class="muted">No servers registered yet.</td></tr>`; }
function serverRow(s){ return `<tr><td><div class="server-name">${esc(s.name)}</div><div class="server-host">${esc(s.hostname)}</div></td><td>${esc(s.platform)} · ${esc(s.arch)}</td><td><span class="state"><span class="health-dot ${s.status}"></span>${esc(s.status)}</span></td><td>${pct(s.cpu_percent)}</td><td>${pct(s.memory_percent)}</td><td>${pct(s.disk_percent)}</td><td>${fmtTime(s.last_seen)}</td></tr>` }
async function loadFleet() { state.servers=await api('/api/servers'); renderFleet(); }
function renderFleet(){ const q=($('server-search').value||'').toLowerCase(); const list=state.servers.filter(s=>`${s.name} ${s.hostname} ${s.platform}`.toLowerCase().includes(q)); $('fleet-cards').innerHTML=list.map(serverCard).join('') || `<div class="muted">No matching servers.</div>`; }
function serverCard(s){ return `<article class="server-card"><div class="server-card-head"><div><h4>${esc(s.name)}</h4><div class="server-meta">${esc(s.hostname)} · ${esc(s.platform)} ${esc(s.arch)}</div></div><span class="state"><span class="health-dot ${s.status}"></span>${esc(s.status)}</span></div><div class="util"><div class="util-item"><span>CPU</span><strong>${pct(s.cpu_percent)}</strong></div><div class="util-item"><span>Memory</span><strong>${pct(s.memory_percent)}</strong></div><div class="util-item"><span>Disk</span><strong>${pct(s.disk_percent)}</strong></div></div><div class="server-meta">Last seen ${fmtTime(s.last_seen)}</div><div class="card-actions"><button class="ghost" onclick="queueAction('${s.id}','refresh_inventory')">Refresh</button><button class="ghost" onclick="queueAction('${s.id}','collect_diagnostics')">Diagnostics</button><button class="ghost" onclick="queueAction('${s.id}','service_restart')">Restart service</button><button class="ghost" onclick="queueAction('${s.id}','reboot')">Reboot</button></div></article>` }
async function loadJobs(){ state.jobs=await api('/api/jobs'); $('jobs-table').innerHTML=state.jobs.map(j=>`<tr><td>${esc(j.action)}</td><td>${esc((state.servers.find(s=>s.id===j.server_id)||{}).name||j.server_id)}</td><td>${esc(j.status)}</td><td>${fmtTime(j.created_at)}</td><td>${esc(JSON.stringify(j.result||{}))}</td></tr>`).join('') || `<tr><td colspan="5" class="muted">No operations yet.</td></tr>`; }
async function loadAudit(){ const rows=await api('/api/audit'); $('audit-table').innerHTML=rows.map(r=>`<tr><td>${fmtTime(r.created_at)}</td><td>${esc(r.actor)}</td><td>${esc(r.action)}</td><td>${esc(r.target)}</td><td><code>${esc(JSON.stringify(r.detail||{}))}</code></td></tr>`).join('') || `<tr><td colspan="5" class="muted">No audit events.</td></tr>`; }
$('server-search').addEventListener('input', renderFleet); $('refresh-overview').addEventListener('click', loadOverview); $('refresh-jobs').addEventListener('click',loadJobs); $('refresh-audit').addEventListener('click',loadAudit);
$('add-server').addEventListener('click',()=>{ $('server-modal').classList.remove('hidden'); $('enrollment-output').classList.add('hidden'); }); $('close-server-modal').addEventListener('click',()=>closeServerModal());
$('generate-token').addEventListener('click',async()=>{ try{const r=await api('/api/enrollment-tokens',{method:'POST'}); $('enrollment-token').textContent=r.token; $('enrollment-expiry').textContent=`Expires ${fmtTime(r.expires_at)}`; $('enrollment-output').classList.remove('hidden');}catch(e){alert(e.message)} });
$('close-action-modal').addEventListener('click',()=>closeAction()); $('cancel-action').addEventListener('click',()=>closeAction());
document.querySelectorAll('.modal-backdrop').forEach(b => b.addEventListener('click', () => { closeServerModal(); closeAction(); }));
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeServerModal(); closeAction(); } });
function closeServerModal(){ $('server-modal').classList.add('hidden'); }
$('confirm-action').addEventListener('click',async()=>{ const p=state.pendingAction; if(!p)return; const params={}; if(p.action.startsWith('service_')) params.service=$('service-name').value.trim(); try{await api(`/api/servers/${p.id}/jobs`,{method:'POST',body:{action:p.action,params}}); closeAction(); await loadFleet(); await loadOverview();}catch(e){alert(e.message)} });
window.queueAction=(id,action)=>{ state.pendingAction={id,action}; $('action-title').textContent=action.replaceAll('_',' '); $('action-description').textContent={reboot:'Restart the server through its local agent.',shutdown:'Power down the server through its local agent.',service_restart:'Restart a named service.',service_start:'Start a named service.',service_stop:'Stop a named service.',refresh_inventory:'Ask the agent to refresh local inventory on the next heartbeat.',collect_diagnostics:'Collect a bounded diagnostic snapshot on the server.'}[action]||'Queue a controlled server operation.'; $('service-field').classList.toggle('hidden',!action.startsWith('service_')); $('action-modal').classList.remove('hidden'); }
function closeAction(){state.pendingAction=null;$('service-field').classList.add('hidden');$('action-modal').classList.add('hidden');}
function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
checkSession();
