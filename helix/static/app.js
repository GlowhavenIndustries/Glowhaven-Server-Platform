const state = {
  view: 'overview',
  me: null,
  servers: [],
  jobs: [],
  audit: [],
  pendingAction: null
};

const $ = id => document.getElementById(id);

const fmtTime = value => {
  if (!value) return 'Never';
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
  return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const pct = value => `${Math.round(Number(value || 0))}%`;

// Toast notification helper
function showToast(message, type = 'info', title = '') {
  const container = $('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const titles = { success: 'Success', error: 'Error', info: 'System Notice' };
  toast.innerHTML = `
    <div class="toast-content">
      <div class="toast-title">${esc(title || titles[type] || 'Notice')}</div>
      <div class="toast-message">${esc(message)}</div>
    </div>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    setTimeout(() => toast.remove(), 200);
  }, 4000);
}

async function api(path, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  if (opts.body && typeof opts.body !== 'string') {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes((opts.method || 'GET').toUpperCase())) {
    const csrf = document.cookie.split('; ').find(x => x.startsWith('helix_csrf='));
    if (csrf) opts.headers['X-CSRF-Token'] = decodeURIComponent(csrf.split('=')[1]);
  }
  const response = await fetch(path, opts);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return payload;
}

// Session checking & app initialization
async function checkSession() {
  try {
    state.me = await api('/api/me');
    $('login').classList.add('hidden');
    $('app').classList.remove('hidden');
    $('identity').textContent = `${state.me.username} · ${state.me.role}`;
    if ($('user-avatar-initial')) {
      $('user-avatar-initial').textContent = (state.me.username || 'A')[0].toUpperCase();
    }
    document.querySelectorAll('.admin-only').forEach(el => {
      el.classList.toggle('hidden', state.me.role !== 'admin');
    });
    await loadOverview();
  } catch (err) {
    $('login').classList.remove('hidden');
    $('app').classList.add('hidden');
  }
}

// Login
$('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  $('login-error').textContent = '';
  try {
    await api('/api/auth/login', {
      method: 'POST',
      body: { username: $('username').value, password: $('password').value }
    });
    showToast('Authenticated successfully.', 'success', 'Session Active');
    await checkSession();
  } catch (err) {
    $('login-error').textContent = err.message;
    showToast(err.message, 'error', 'Authentication Failed');
  }
});

// Logout
$('logout').addEventListener('click', async () => {
  try {
    await api('/api/auth/logout', { method: 'POST' });
  } finally {
    location.reload();
  }
});

// Navigation View Switcher
document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => switchView(btn.dataset.view));
});

function switchView(view) {
  state.view = view;
  closeMobileSidebar();
  document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
  const targetView = $(`${view}-view`);
  if (targetView) targetView.classList.remove('hidden');

  document.querySelectorAll('.nav-item').forEach(v => {
    v.classList.toggle('active', v.dataset.view === view);
  });

  const titles = {
    overview: ['TELEMETRY', 'Fleet overview'],
    fleet: ['SERVER INVENTORY', 'Managed fleet'],
    jobs: ['GOVERNANCE', 'Operations queue'],
    audit: ['SECURITY & COMPLIANCE', 'Audit trail']
  };

  if (titles[view]) {
    $('view-kicker').textContent = titles[view][0];
    $('view-title').textContent = titles[view][1];
  }

  if (view === 'overview') loadOverview();
  if (view === 'fleet') loadFleet();
  if (view === 'jobs') loadJobs();
  if (view === 'audit') loadAudit();
}

// Mobile sidebar handling
const mobileNavToggle = $('mobile-nav-toggle');
const sidebar = $('sidebar');
const sidebarOverlay = $('sidebar-overlay');

if (mobileNavToggle) {
  mobileNavToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    sidebarOverlay.classList.toggle('active');
  });
}

if (sidebarOverlay) {
  sidebarOverlay.addEventListener('click', closeMobileSidebar);
}

function closeMobileSidebar() {
  if (sidebar) sidebar.classList.remove('open');
  if (sidebarOverlay) sidebarOverlay.classList.remove('active');
}

// Overview Loader
async function loadOverview() {
  try {
    const [summary, servers] = await Promise.all([api('/api/summary'), api('/api/servers')]);
    state.servers = servers;
    $('metric-servers').textContent = summary.servers;
    $('metric-online').textContent = summary.online;
    $('metric-warning').textContent = summary.warning;
    $('metric-queued').textContent = summary.queued_jobs;
    $('metric-online-sub').textContent = `${summary.online} online now`;
    $('metric-failed-sub').textContent = `${summary.failed_jobs_24h} failed in last 24h`;

    const overviewTable = $('overview-table');
    if (overviewTable) {
      overviewTable.innerHTML = servers.slice(0, 15).map(serverRow).join('') ||
        `<tr><td colspan="7" class="muted text-center" style="padding: 32px;">No servers registered yet. Click "Enroll Server" to connect host nodes.</td></tr>`;
    }
  } catch (err) {
    showToast(err.message, 'error', 'Failed to load telemetry');
  }
}

function utilBar(value) {
  const num = Math.round(Number(value || 0));
  let statusClass = '';
  if (num >= 90) statusClass = 'critical';
  else if (num >= 75) statusClass = 'warning';

  return `
    <div class="util-bar-wrapper">
      <div class="util-bar-bg">
        <div class="util-bar-fill ${statusClass}" style="width: ${num}%"></div>
      </div>
      <span class="util-percent">${num}%</span>
    </div>
  `;
}

function serverRow(s) {
  return `
    <tr>
      <td>
        <div class="server-cell-title">${esc(s.name)}</div>
        <div class="server-cell-sub">${esc(s.hostname)}</div>
      </td>
      <td>${esc(s.platform)} · ${esc(s.arch)}</td>
      <td>
        <span class="status-pill ${s.status}">
          <span class="status-dot ${s.status}"></span>
          ${esc(s.status)}
        </span>
      </td>
      <td>${utilBar(s.cpu_percent)}</td>
      <td>${utilBar(s.memory_percent)}</td>
      <td>${utilBar(s.disk_percent)}</td>
      <td>${fmtTime(s.last_seen)}</td>
    </tr>
  `;
}

// Fleet View Loader & Search
async function loadFleet() {
  try {
    state.servers = await api('/api/servers');
    renderFleet();
  } catch (err) {
    showToast(err.message, 'error', 'Failed to load fleet');
  }
}

function renderFleet() {
  const q = ($('server-search')?.value || '').toLowerCase();
  const list = state.servers.filter(s => `${s.name} ${s.hostname} ${s.platform} ${s.arch} ${s.os_version}`.toLowerCase().includes(q));
  const fleetGrid = $('fleet-cards');
  if (!fleetGrid) return;

  if (list.length === 0) {
    fleetGrid.innerHTML = `<div class="muted" style="grid-column: 1/-1; padding: 32px; text-align: center; background: var(--surface-primary); border-radius: var(--radius-lg); border: 1px solid var(--border-muted);">No matching servers found.</div>`;
    return;
  }

  fleetGrid.innerHTML = list.map(serverCard).join('');
}

function serverCard(s) {
  return `
    <article class="server-card">
      <div class="server-card-head">
        <div class="server-card-title">
          <h4>${esc(s.name)}</h4>
          <div class="server-card-meta">${esc(s.hostname)} · ${esc(s.platform)} ${esc(s.arch)}</div>
        </div>
        <span class="status-pill ${s.status}">
          <span class="status-dot ${s.status}"></span>
          ${esc(s.status)}
        </span>
      </div>

      <div class="util-grid">
        <div class="util-item">
          <span class="util-item-label">CPU</span>
          <div class="util-item-val">${pct(s.cpu_percent)}</div>
        </div>
        <div class="util-item">
          <span class="util-item-label">Memory</span>
          <div class="util-item-val">${pct(s.memory_percent)}</div>
        </div>
        <div class="util-item">
          <span class="util-item-label">Disk</span>
          <div class="util-item-val">${pct(s.disk_percent)}</div>
        </div>
      </div>

      <div class="server-card-meta">Last seen ${fmtTime(s.last_seen)}</div>

      <div class="card-actions">
        <button class="btn btn-ghost" onclick="queueAction('${s.id}','refresh_inventory')">Refresh</button>
        <button class="btn btn-ghost" onclick="queueAction('${s.id}','collect_diagnostics')">Diagnostics</button>
        <button class="btn btn-ghost" onclick="queueAction('${s.id}','service_restart')">Restart Service</button>
        <button class="btn btn-ghost" onclick="queueAction('${s.id}','reboot')">Reboot Node</button>
      </div>
    </article>
  `;
}

// Jobs Loader & Filter
async function loadJobs() {
  try {
    state.jobs = await api('/api/jobs');
    renderJobs();
  } catch (err) {
    showToast(err.message, 'error', 'Failed to load operations');
  }
}

function renderJobs() {
  const q = ($('jobs-search')?.value || '').toLowerCase();
  const list = state.jobs.filter(j => {
    const sName = (state.servers.find(s => s.id === j.server_id) || {}).name || j.server_id;
    return `${j.action} ${sName} ${j.status}`.toLowerCase().includes(q);
  });

  const jobsTable = $('jobs-table');
  if (!jobsTable) return;

  if (list.length === 0) {
    jobsTable.innerHTML = `<tr><td colspan="5" class="muted text-center" style="padding: 28px;">No operations recorded in queue.</td></tr>`;
    return;
  }

  jobsTable.innerHTML = list.map((j, idx) => {
    const sName = (state.servers.find(s => s.id === j.server_id) || {}).name || j.server_id;
    return `
      <tr>
        <td><strong>${esc(j.action)}</strong></td>
        <td>${esc(sName)}</td>
        <td>
          <span class="status-pill ${j.status}">
            ${esc(j.status)}
          </span>
        </td>
        <td>${fmtTime(j.created_at)}</td>
        <td>
          <button class="btn btn-ghost btn-sm" onclick="showJobOutput(${idx})">
            View Output (${Object.keys(j.result || {}).length} keys)
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

window.showJobOutput = (idx) => {
  const job = state.jobs[idx];
  if (!job) return;
  showDetailModal('Job Output Data', job.result || {});
};

// Audit Loader & Filter
async function loadAudit() {
  try {
    state.audit = await api('/api/audit');
    renderAudit();
  } catch (err) {
    showToast(err.message, 'error', 'Failed to load audit events');
  }
}

function renderAudit() {
  const q = ($('audit-search')?.value || '').toLowerCase();
  const list = state.audit.filter(r => `${r.actor} ${r.action} ${r.target}`.toLowerCase().includes(q));

  const auditTable = $('audit-table');
  if (!auditTable) return;

  if (list.length === 0) {
    auditTable.innerHTML = `<tr><td colspan="5" class="muted text-center" style="padding: 28px;">No audit events found.</td></tr>`;
    return;
  }

  auditTable.innerHTML = list.map((r, idx) => {
    return `
      <tr>
        <td>${fmtTime(r.created_at)}</td>
        <td><strong>${esc(r.actor)}</strong></td>
        <td><code>${esc(r.action)}</code></td>
        <td>${esc(r.target)}</td>
        <td>
          <button class="btn btn-ghost btn-sm" onclick="showAuditPayload(${idx})">
            Inspect Payload
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

window.showAuditPayload = (idx) => {
  const item = state.audit[idx];
  if (!item) return;
  showDetailModal('Audit Event Payload', item.detail || {});
};

// Modal Detail Viewer
window.showDetailModal = (title, data) => {
  $('detail-modal-title').textContent = title;
  const jsonStr = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  $('detail-modal-code').textContent = jsonStr;
  $('detail-modal').classList.remove('hidden');
};

$('close-detail-modal')?.addEventListener('click', closeDetailModal);
$('close-detail-btn')?.addEventListener('click', closeDetailModal);

function closeDetailModal() {
  $('detail-modal').classList.add('hidden');
}

$('copy-detail-btn')?.addEventListener('click', () => {
  const text = $('detail-modal-code').textContent;
  navigator.clipboard.writeText(text).then(() => {
    showToast('JSON payload copied to clipboard.', 'success', 'Copied');
  });
});

// Event Listeners for Filters & Refresh
if ($('server-search')) $('server-search').addEventListener('input', renderFleet);
if ($('jobs-search')) $('jobs-search').addEventListener('input', renderJobs);
if ($('audit-search')) $('audit-search').addEventListener('input', renderAudit);

if ($('refresh-overview')) $('refresh-overview').addEventListener('click', loadOverview);
if ($('refresh-jobs')) $('refresh-jobs').addEventListener('click', loadJobs);
if ($('refresh-audit')) $('refresh-audit').addEventListener('click', loadAudit);

// Enrollment Modal
if ($('add-server')) {
  $('add-server').addEventListener('click', () => {
    $('server-modal').classList.remove('hidden');
    $('enrollment-output').classList.add('hidden');
  });
}

if ($('close-server-modal')) {
  $('close-server-modal').addEventListener('click', () => closeServerModal());
}

function closeServerModal() {
  $('server-modal').classList.add('hidden');
}

if ($('generate-token')) {
  $('generate-token').addEventListener('click', async () => {
    try {
      const r = await api('/api/enrollment-tokens', { method: 'POST' });
      $('enrollment-token').textContent = r.token;
      $('enrollment-expiry').textContent = `Expires ${fmtTime(r.expires_at)}`;
      $('enroll-command').textContent = `python -m agent --controller ${location.origin} --enrollment-token ${r.token} --name prod-node-01`;
      $('enrollment-output').classList.remove('hidden');
      showToast('Enrollment token generated.', 'success', 'Token Active');
    } catch (e) {
      showToast(e.message, 'error', 'Token Generation Failed');
    }
  });
}

if ($('copy-token-btn')) {
  $('copy-token-btn').addEventListener('click', () => {
    const tokenVal = $('enrollment-token').textContent;
    if (tokenVal) {
      navigator.clipboard.writeText(tokenVal).then(() => {
        showToast('Token copied to clipboard.', 'success', 'Copied');
      });
    }
  });
}

// Action Modal
if ($('close-action-modal')) $('close-action-modal').addEventListener('click', closeActionModal);
if ($('cancel-action')) $('cancel-action').addEventListener('click', closeActionModal);

document.querySelectorAll('.modal-backdrop').forEach(b => {
  b.addEventListener('click', () => {
    closeServerModal();
    closeActionModal();
    closeDetailModal();
  });
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeServerModal();
    closeActionModal();
    closeDetailModal();
  }
});

if ($('confirm-action')) {
  $('confirm-action').addEventListener('click', async () => {
    const p = state.pendingAction;
    if (!p) return;
    const params = {};
    if (p.action.startsWith('service_')) {
      const svcName = $('service-name').value.trim();
      if (!svcName) {
        showToast('Please enter a service name.', 'error', 'Validation Error');
        return;
      }
      params.service = svcName;
    }
    try {
      await api(`/api/servers/${p.id}/jobs`, {
        method: 'POST',
        body: { action: p.action, params }
      });
      showToast(`Operation queued for action: ${p.action}`, 'success', 'Action Queued');
      closeActionModal();
      await loadFleet();
      await loadOverview();
    } catch (e) {
      showToast(e.message, 'error', 'Action Execution Failed');
    }
  });
}

window.queueAction = (id, action) => {
  state.pendingAction = { id, action };
  $('action-title').textContent = action.replaceAll('_', ' ').toUpperCase();
  $('action-description').textContent = {
    reboot: 'Restart the target host server operating system via local agent.',
    shutdown: 'Power down the target host server via local agent.',
    service_restart: 'Restart a specific named system service.',
    service_start: 'Start a specific named system service.',
    service_stop: 'Stop a specific named system service.',
    refresh_inventory: 'Instruct agent to collect updated inventory metadata on next heartbeat.',
    collect_diagnostics: 'Gather diagnostic state snapshot and system logs.'
  }[action] || 'Queue a controlled operation against host.';

  $('service-field').classList.toggle('hidden', !action.startsWith('service_'));
  $('action-modal').classList.remove('hidden');
};

function closeActionModal() {
  state.pendingAction = null;
  $('service-field').classList.add('hidden');
  $('action-modal').classList.add('hidden');
}

// Utility Escaping Functions
function esc(v) {
  return String(v ?? '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}

// Initial Session Check
checkSession();
