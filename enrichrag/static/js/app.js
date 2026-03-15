/* enrichRAG — Frontend Application
   API_PREFIX is injected by the server via inline script in index.html */

const API_PREFIX = window.__API_PREFIX || '';
const MAX_HISTORY = 20;
const { esc, escAttr, renderMarkdownSafe, renderStateCard, safeUrl } = window.enrichRAGUI;
const appState = {
  currentResult: null,
  currentView: 'input',
  pipelineRunning: false,
  eventSource: null,
  currentValidation: null,
  isChatOpen: false,
  chatHistory: [],
  activeDrawer: null,
  lastFocusedElement: null,
  currentUser: null,
  historyItems: [],
  authMode: 'login',
};

const api = {
  validateGenes(genes) {
    return fetch(API_PREFIX + '/api/genes/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ genes }),
    });
  },

  fetchGeneProfile(symbol) {
    return fetch(API_PREFIX + '/api/genes/' + encodeURIComponent(symbol));
  },

  startAnalysisStream(params) {
    return new EventSource(API_PREFIX + '/api/analyze/stream?' + params);
  },

  chat(payload) {
    return fetch(`${API_PREFIX}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  login(payload) {
    return fetch(`${API_PREFIX}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  register(payload) {
    return fetch(`${API_PREFIX}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  logout() {
    return fetch(`${API_PREFIX}/api/auth/logout`, { method: 'POST' });
  },

  me() {
    return fetch(`${API_PREFIX}/api/auth/me`);
  },

  history() {
    return fetch(`${API_PREFIX}/api/history`);
  },

  loadHistoryItem(id) {
    return fetch(`${API_PREFIX}/api/history/${encodeURIComponent(id)}`);
  },

  deleteHistoryItem(id) {
    return fetch(`${API_PREFIX}/api/history/${encodeURIComponent(id)}`, { method: 'DELETE' });
  },

  clearHistory() {
    return fetch(`${API_PREFIX}/api/history`, { method: 'DELETE' });
  },
};

function getCurrentResult() {
  return appState.currentResult;
}

function setCurrentResult(result) {
  appState.currentResult = normalizeResultShape(result);
  return appState.currentResult;
}

function getCurrentValidation() {
  return appState.currentValidation;
}

function setCurrentValidation(validation) {
  appState.currentValidation = validation;
  return appState.currentValidation;
}

function resetChatHistory() {
  appState.chatHistory = [];
}

function getChatHistory() {
  return appState.chatHistory;
}

function pushChatHistory(message) {
  appState.chatHistory.push(message);
}

function normalizeResultShape(result) {
  if (!result) return null;
  const normalizedGenes = deriveInputGenes(result);
  return {
    input_genes: normalizedGenes,
    disease_context: result.disease_context || 'Analysis',
    enrichment_results: result.enrichment_results || {},
    llm_insight: result.llm_insight || '',
    sources: {
      web: result.sources?.web || result.web_sources || [],
      pubmed: result.sources?.pubmed || [],
    },
    gene_relations: result.gene_relations || [],
    graph: result.graph || { nodes: [], edges: [] },
    query_plan: result.query_plan || {},
    gene_validation: result.gene_validation || null,
    timestamp: result.timestamp || null,
  };
}

function deriveInputGenes(result) {
  if (!result) return [];
  if (Array.isArray(result.input_genes) && result.input_genes.length) return result.input_genes;
  if (Array.isArray(result.genes) && result.genes.length) return result.genes;
  const validation = result.gene_validation || null;
  if (Array.isArray(validation?.normalized_genes) && validation.normalized_genes.length) {
    return validation.normalized_genes;
  }
  if (Array.isArray(validation?.rows) && validation.rows.length) {
    const rows = validation.rows
      .filter((row) => row?.status !== 'rejected')
      .map((row) => row?.normalized_symbol || row?.canonical_symbol || row?.mapped_to || row?.input_gene)
      .filter(Boolean);
    if (rows.length) return rows;
  }
  if (Array.isArray(result.graph?.nodes) && result.graph.nodes.length) {
    const graphGenes = result.graph.nodes
      .map((node) => node?.id || node?.label || node?.name)
      .filter((value) => typeof value === 'string' && value.trim())
      .slice(0, 100);
    if (graphGenes.length) return graphGenes;
  }
  return [];
}

document.addEventListener('DOMContentLoaded', async () => {
  lucide.createIcons();
  initEventHandlers();
  await bootstrapAuth();
  ['genes', 'disease', 'pval'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', resetValidationUI);
  });
});

function initEventHandlers() {
  document.getElementById('loginForm')?.addEventListener('submit', handleLoginSubmit);
  document.getElementById('requestAccessForm')?.addEventListener('submit', handleRequestAccessSubmit);
  document.getElementById('showRequestAccessBtn')?.addEventListener('click', () => setAuthMode('request'));
  document.getElementById('backToLoginBtn')?.addEventListener('click', () => setAuthMode('login'));
  document.getElementById('signOutBtn')?.addEventListener('click', handleLogout);
  document.getElementById('mobileNavToggle')?.addEventListener('click', () => {
    document.querySelector('.sidebar nav')?.classList.toggle('open');
  });

  document.querySelectorAll('.nav-btn[data-view]').forEach((button) => {
    button.addEventListener('click', () => switchView(button.dataset.view));
  });

  document.getElementById('validateBtn')?.addEventListener('click', validateGenes);
  document.getElementById('runBtn')?.addEventListener('click', runAnalysis);
  document.getElementById('cancelBtn')?.addEventListener('click', cancelAnalysis);
  document.getElementById('openChatBtn')?.addEventListener('click', () => toggleChatDrawer());
  document.getElementById('copyReportBtn')?.addEventListener('click', copyReport);
  document.getElementById('downloadJsonBtn')?.addEventListener('click', downloadJSON);
  document.getElementById('chatBackdrop')?.addEventListener('click', () => toggleChatDrawer(false));
  document.getElementById('closeChatBtn')?.addEventListener('click', () => toggleChatDrawer(false));
  document.getElementById('drawerBackdrop')?.addEventListener('click', closeGeneDrawer);
  document.getElementById('closeGeneDrawerBtn')?.addEventListener('click', closeGeneDrawer);
  document.getElementById('chatForm')?.addEventListener('submit', handleChatSubmit);
  document.getElementById('disease')?.addEventListener('keydown', handlePrimaryActionKeydown);
  document.getElementById('pval')?.addEventListener('keydown', handlePrimaryActionKeydown);
  document.getElementById('genes')?.addEventListener('keydown', handleGenesKeydown);
  document.addEventListener('keydown', handleGlobalKeydown);
}

async function bootstrapAuth() {
  try {
    const response = await api.me();
    const user = await response.json();
    if (!user) throw new Error('unauthorized');
    applyAuthenticatedUser(user);
    await refreshHistory();
  } catch (err) {
    showAuthShell();
  }
}

function setAuthMode(mode) {
  appState.authMode = mode;
  document.getElementById('loginForm')?.classList.toggle('active', mode === 'login');
  document.getElementById('requestAccessForm')?.classList.toggle('active', mode === 'request');
  const label = document.getElementById('authModeLabel');
  if (label) {
    label.textContent = mode === 'login' ? 'Augmentation Protocol' : 'Account Provisioning';
  }
  setAuthError('');
  lucide.createIcons();
}

function setAuthError(message) {
  const el = document.getElementById('authError');
  if (el) el.textContent = message || '';
}

function formatApiError(payload, fallback) {
  const detail = payload?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const message = detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (!item || typeof item !== 'object') return '';
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : '';
        const prefix = field ? `${field}: ` : '';
        return `${prefix}${item.msg || 'Invalid value'}`;
      })
      .filter(Boolean)
      .join('; ');
    if (message) return message;
  }
  return fallback;
}

function showAuthShell() {
  appState.currentUser = null;
  document.getElementById('authShell')?.classList.add('active');
  setAuthMode('login');
  const username = document.getElementById('loginEmail');
  if (username) username.focus();
}

function hideAuthShell() {
  document.getElementById('authShell')?.classList.remove('active');
}

function applyAuthenticatedUser(user) {
  appState.currentUser = user;
  hideAuthShell();
  const nameEl = document.getElementById('sidebarUserName');
  const emailEl = document.getElementById('sidebarUsername');
  if (nameEl) nameEl.textContent = user.display_name || user.email;
  if (emailEl) emailEl.textContent = user.email;
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  setAuthError('');
  const submit = document.getElementById('loginSubmit');
  if (submit) submit.disabled = true;
  try {
    const response = await api.login({
      email: document.getElementById('loginEmail').value.trim(),
      password: document.getElementById('loginPassword').value,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(formatApiError(payload, 'Login failed'));
    }
    const user = await response.json();
    applyAuthenticatedUser(user);
    document.getElementById('loginPassword').value = '';
    await refreshHistory();
    showToast(`Signed in as ${user.email}`);
  } catch (err) {
    setAuthError(err.message || 'Login failed');
  } finally {
    if (submit) submit.disabled = false;
  }
}

function handleRequestAccessSubmit(event) {
  event.preventDefault();
  setAuthError('');
  api.register({
    display_name: document.getElementById('requestName').value.trim(),
    email: document.getElementById('requestEmail').value.trim(),
    password: document.getElementById('requestPassword').value,
  })
    .then(async (response) => {
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(formatApiError(payload, 'Registration failed'));
      }
      return response.json();
    })
    .then(async (user) => {
      applyAuthenticatedUser(user);
      await refreshHistory();
      showToast(`Account ready for ${user.email}`);
    })
    .catch((err) => {
      setAuthError(err.message || 'Registration failed');
    });
}

async function handleLogout() {
  try {
    await api.logout();
  } finally {
    appState.historyItems = [];
    appState.currentResult = null;
    renderHistory();
    resetValidationUI();
    showAuthShell();
  }
}

function handlePrimaryActionKeydown(event) {
  if (event.key !== 'Enter') return;
  event.preventDefault();
  submitPrimaryAction();
}

function handleGenesKeydown(event) {
  if (event.key !== 'Enter' || (!event.ctrlKey && !event.metaKey)) return;
  event.preventDefault();
  submitPrimaryAction(true);
}

function submitPrimaryAction(preferRun = false) {
  const runBtn = document.getElementById('runBtn');
  if (preferRun && runBtn && !runBtn.disabled) {
    runAnalysis();
    return;
  }
  const validation = getCurrentValidation();
  if (validation?.normalized_genes?.length && runBtn && !runBtn.disabled) {
    runAnalysis();
    return;
  }
  validateGenes();
}

function handleGlobalKeydown(event) {
  if (event.key === 'Escape') {
    if (appState.activeDrawer === 'chat') {
      toggleChatDrawer(false);
      return;
    }
    if (appState.activeDrawer === 'gene') {
      closeGeneDrawer();
      return;
    }
  }

  if (event.key !== 'Tab' || !appState.activeDrawer) return;
  trapDrawerFocus(event);
}

/* ---- Navigation ---- */

function switchView(name) {
  if (name === 'results' && !appState.currentResult && !appState.pipelineRunning) return;
  if (name === 'results' && appState.currentResult) {
    renderResultTabs(appState.currentResult);
  }
  appState.currentView = name;
  document.querySelectorAll('.view, .loading-view').forEach(v => v.classList.remove('active'));
  const el = document.getElementById('view-' + name);
  if (el) el.classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.view === name);
  });
  const nav = document.querySelector('.sidebar nav');
  if (nav) nav.classList.remove('open');
  if (name === 'results') {
    switchTab('pipeline');
  }
  lucide.createIcons();
}

function showToast(msg, ms = 2500) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), ms);
}

function resetValidationUI() {
  setCurrentValidation(null);
  const summary = document.getElementById('validationSummary');
  if (summary) summary.innerHTML = '';
  const runBtn = document.getElementById('runBtn');
  if (runBtn) runBtn.disabled = true;
}

async function validateGenes() {
  const genes = document.getElementById('genes').value.trim();
  const disease = document.getElementById('disease').value.trim();
  if (!genes) {
    showToast('Enter at least one gene');
    return;
  }

  const validateBtn = document.getElementById('validateBtn');
  const runBtn = document.getElementById('runBtn');
  validateBtn.disabled = true;
  runBtn.disabled = true;

  try {
    const response = await api.validateGenes(genes);
    if (!response.ok) throw new Error('Validation failed');
    const validation = await response.json();
    setCurrentValidation(validation);
    renderValidationSummary(validation);
    renderValidationResultsPreview(validation, disease);
    document.getElementById('navResults').disabled = false;
    runBtn.disabled = !validation.normalized_genes.length;
    showToast(`Validated ${validation.summary.total} genes`);
  } catch (err) {
    console.error(err);
    showToast('Gene validation failed');
  } finally {
    validateBtn.disabled = false;
  }
}

function renderValidationSummary(data) {
  const summary = document.getElementById('validationSummary');
  if (!summary) return;
  summary.innerHTML = renderValidationSummaryCard(data, false);
  lucide.createIcons();
}

function renderValidationResultsPreview(validationData, disease) {
  setCurrentResult({
    input_genes: validationData.normalized_genes || [],
    disease_context: disease || 'Analysis',
    enrichment_results: {},
    llm_insight: '',
    sources: { web: [], pubmed: [] },
    gene_relations: [],
    graph: { nodes: [], edges: [] },
    gene_validation: validationData,
  });
  resetChatSession();
  document.getElementById('statusBadge').innerHTML = '<i data-lucide="badge-check"></i> Validation Ready';
  document.getElementById('navResults').disabled = false;
}

async function openGeneDrawer(symbol) {
  const drawer = document.getElementById('geneDrawer');
  const backdrop = document.getElementById('drawerBackdrop');
  const title = document.getElementById('drawerTitle');
  const body = document.getElementById('drawerBody');
  title.textContent = symbol;
  body.innerHTML = renderStateCard({
    tone: 'waiting',
    icon: 'loader-2',
    title: 'Loading gene profile',
    description: 'Fetching canonical metadata and reference fields for this gene.',
    compact: true,
  });
  drawer.classList.add('open');
  backdrop.classList.add('open');
  drawer.setAttribute('aria-hidden', 'false');
  setActiveDrawer('gene', drawer);
  lucide.createIcons();

  try {
    const response = await api.fetchGeneProfile(symbol);
    if (!response.ok) throw new Error('Profile not found');
    const data = await response.json();
    title.textContent = data.canonical_symbol || symbol;
    body.innerHTML = renderGeneDrawer(data);
  } catch (err) {
    console.error(err);
    body.innerHTML = renderStateCard({
      icon: 'dna-off',
      title: 'Gene profile unavailable',
      description: 'This gene does not have a stored profile in the current dataset.',
      compact: true,
    });
  }
  lucide.createIcons();
}

function closeGeneDrawer() {
  const drawer = document.getElementById('geneDrawer');
  const backdrop = document.getElementById('drawerBackdrop');
  drawer.classList.remove('open');
  backdrop.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
  clearActiveDrawer('gene');
}

function renderGeneDrawer(data) {
  const ncbiLink = data.gene_id
    ? `<div class="drawer-section"><a class="drawer-link" href="https://www.ncbi.nlm.nih.gov/gene?Db=gene&Cmd=DetailsSearch&Term=${encodeURIComponent(data.gene_id)}" target="_blank" rel="noopener"><i data-lucide="external-link"></i> Open in NCBI Gene</a></div>`
    : '';
  return `
    <div class="drawer-section">
      <div class="drawer-grid">
        ${renderDrawerField('Symbol', data.canonical_symbol || '-')}
        ${renderDrawerField('Gene ID', data.gene_id || '-', true)}
        ${renderDrawerField('Official Symbol', data.official_symbol || '-')}
        ${renderDrawerField('Gene Type', data.type_of_gene || '-')}
        ${renderDrawerField('Chromosome', data.chromosome || '-')}
        ${renderDrawerField('Map Location', data.map_location || '-')}
      </div>
    </div>
    <div class="drawer-section">
      ${renderDrawerField('Official Name', data.official_full_name || '-', false, true)}
      ${renderDrawerField('Description', data.description || '-', false, true)}
      ${renderDrawerField('Synonyms', data.synonyms || '-', true, true)}
      ${renderDrawerField('dbXrefs', data.dbxrefs || '-', true, true)}
      ${renderDrawerField('Last Updated', data.modification_date || '-', true)}
    </div>
    ${ncbiLink}
  `;
}

function renderDrawerField(label, value, mono = false, full = false) {
  return `
    <div class="drawer-field${full ? ' drawer-field-full' : ''}">
      <label>${esc(label)}</label>
      <div class="drawer-field-value${mono ? ' mono' : ''}">${esc(value)}</div>
    </div>
  `;
}

/* ---- Pipeline State ---- */

function getPipelineNodeElements(nodeId) {
  return [
    document.getElementById('node-' + nodeId),
    document.getElementById('node-' + nodeId + '-mobile'),
  ].filter(Boolean);
}

function setPipelineState(nodeId, status) {
  getPipelineNodeElements(nodeId).forEach((el) => {
    el.dataset.status = status;
    const circle = el.querySelector('.node-circle');
    if (status === 'done') {
      circle.innerHTML = '<i data-lucide="check" style="width:18px;height:18px"></i>';
    } else if (status === 'active') {
      circle.innerHTML = '<i data-lucide="loader-2" style="width:18px;height:18px"></i>';
    } else if (status === 'cancelled') {
      circle.innerHTML = '<i data-lucide="minus" style="width:18px;height:18px"></i>';
    } else if (status === 'failed') {
      circle.innerHTML = '<i data-lucide="alert-triangle" style="width:18px;height:18px"></i>';
    } else if (status === 'timeout') {
      circle.innerHTML = '<i data-lucide="clock-3" style="width:18px;height:18px"></i>';
    } else {
      const fallbackIcons = {
        enrichment: 'network',
        planning: 'route',
        search: 'globe',
        pubmed: 'book-open',
        extraction: 'scan-search',
        llm: 'brain-circuit',
        done: 'file-text',
      };
      circle.innerHTML = `<i data-lucide="${fallbackIcons[nodeId] || 'circle'}" style="width:18px;height:18px"></i>`;
    }
  });
  lucide.createIcons();
}

function setLineState(lineId, status) {
  const el = document.getElementById(lineId);
  if (el) { el.className = 'pipe-line ' + status; }
}

const _nodeTimers = {};
const NODE_TIMEOUT_MS = 600000;

function resetPipeline() {
  ['enrichment','planning','search','pubmed','extraction','llm','done'].forEach(n => {
    getPipelineNodeElements(n).forEach((el) => {
      el.dataset.status = 'pending';
      const timer = el.querySelector('.node-timer');
      if (timer) timer.textContent = '';
      const sub = el.querySelector('.node-sub');
      if (sub) sub.textContent = _defaultSubs[n] || '';
    });
    if (_nodeTimers[n]) { clearInterval(_nodeTimers[n].interval); delete _nodeTimers[n]; }
  });
  document.querySelectorAll('.pipe-line').forEach(l => l.className = 'pipe-line pending');
  document.querySelectorAll('.mobile-link').forEach((link) => {
    link.dataset.linkStatus = 'pending';
  });
  lucide.createIcons();
}

const _defaultSubs = {
  enrichment: 'GO & KEGG',
  planning: 'Query Strategy',
  search: 'Tavily API',
  pubmed: 'Entrez API',
  extraction: 'Relations',
  llm: 'LLM Gen',
  done: 'Structuring',
};

function startNodeTimer(name) {
  if (_nodeTimers[name]) return;
  const nodes = getPipelineNodeElements(name);
  if (!nodes.length) return;
  const start = Date.now();
  nodes.forEach((el) => {
    const timerEl = el.querySelector('.node-timer');
    if (timerEl) timerEl.textContent = '0.0s';
  });
  _nodeTimers[name] = {
    start,
    interval: setInterval(() => {
      const elapsed = Date.now() - start;
      nodes.forEach((el) => {
        const timerEl = el.querySelector('.node-timer');
        if (timerEl) timerEl.textContent = (elapsed / 1000).toFixed(1) + 's';
      });
      if (elapsed >= NODE_TIMEOUT_MS && nodes.some((el) => el.dataset.status === 'active')) {
        nodes.forEach((el) => {
          el.dataset.status = 'timeout';
          const timerEl = el.querySelector('.node-timer');
          if (timerEl) timerEl.textContent = 'timeout';
        });
        clearInterval(_nodeTimers[name].interval);
      }
    }, 100),
  };
}

function stopNodeTimer(name) {
  if (!_nodeTimers[name]) return;
  clearInterval(_nodeTimers[name].interval);
  const elapsed = Date.now() - _nodeTimers[name].start;
  getPipelineNodeElements(name).forEach((el) => {
    const timerEl = el.querySelector('.node-timer');
    if (timerEl) timerEl.textContent = (elapsed / 1000).toFixed(1) + 's';
  });
  delete _nodeTimers[name];
}

function failNodeTimer(name) {
  if (_nodeTimers[name]) clearInterval(_nodeTimers[name].interval);
  const nodes = getPipelineNodeElements(name);
  nodes.forEach((el) => {
    el.dataset.status = 'failed';
    const timerEl = el.querySelector('.node-timer');
    if (timerEl && _nodeTimers[name]) {
      const elapsed = Date.now() - _nodeTimers[name].start;
      timerEl.textContent = (elapsed / 1000).toFixed(1) + 's — failed';
    } else if (timerEl) {
      timerEl.textContent = 'failed';
    }
  });
  if (_nodeTimers[name]) delete _nodeTimers[name];
  lucide.createIcons();
}

function setMobileLinks(statusMap = {}) {
  const mapping = {
    enrichment: ['node-enrichment-mobile'],
    planning: ['node-planning-mobile'],
    search: ['node-search-mobile'],
    pubmed: ['node-pubmed-mobile'],
    extraction: ['node-extraction-mobile'],
    llm: ['node-llm-mobile'],
    done: ['node-done-mobile'],
  };
  Object.entries(mapping).forEach(([key, ids]) => {
    ids.forEach((id) => {
      const node = document.getElementById(id);
      if (!node) return;
      const step = node.closest('.mobile-step');
      const link = step ? step.querySelector('.mobile-link') : null;
      if (link && statusMap[key]) link.dataset.linkStatus = statusMap[key];
    });
  });
}

function updatePipelineFromEvent(step, message) {
  // Update loading message in pipeline tab
  const msgEl = document.getElementById('loadingMsg');
  if (msgEl) msgEl.textContent = message;
  const isFail = /fail|error/i.test(message);

  if (step === 'enrichment' && message.includes('Running')) {
    setPipelineState('enrichment', 'active');
    startNodeTimer('enrichment');
    setMobileLinks({ enrichment: 'active' });
  } else if (step === 'enrichment' && message.includes('complete')) {
    setPipelineState('enrichment', 'done');
    stopNodeTimer('enrichment');
    setLineState('line-0-1', 'active');
    setMobileLinks({ enrichment: 'done', planning: 'active' });
  } else if (step === 'enrichment' && isFail) {
    failNodeTimer('enrichment');
  } else if (step === 'planning' && message.includes('Generating')) {
    setPipelineState('planning', 'active');
    startNodeTimer('planning');
    setLineState('line-0-1', 'done');
    setMobileLinks({ planning: 'active' });
  } else if (step === 'planning' && !isFail) {
    setPipelineState('planning', 'done');
    stopNodeTimer('planning');
    setLineState('line-1-2a', 'active');
    setLineState('line-1-2b', 'active');
    setMobileLinks({ planning: 'done', search: 'active', pubmed: 'active' });
  } else if (step === 'planning' && isFail) {
    failNodeTimer('planning');
  } else if (step === 'search' && (message.includes('Searching') || message.includes('Skipping web'))) {
    if (message.includes('Skipping')) {
      setPipelineState('search', 'done');
      setMobileLinks({ search: 'done' });
    } else {
      setPipelineState('search', 'active');
      startNodeTimer('search');
      setMobileLinks({ search: 'active' });
    }
    setPipelineState('pubmed', 'active');
    startNodeTimer('pubmed');
    setMobileLinks({ pubmed: 'active' });
  } else if (step === 'search' && message.includes('Found')) {
    setPipelineState('search', 'done');
    stopNodeTimer('search');
    setMobileLinks({ search: 'done' });
  } else if (step === 'search' && isFail) {
    failNodeTimer('search');
  } else if (step === 'pubmed' && message.includes('Fetching')) {
    setPipelineState('pubmed', 'active');
    startNodeTimer('pubmed');
    setMobileLinks({ pubmed: 'active' });
  } else if (step === 'pubmed' && (message.includes('Fetched') || message.includes('Skipping'))) {
    setPipelineState('pubmed', 'done');
    stopNodeTimer('pubmed');
    setMobileLinks({ pubmed: 'done' });
  } else if (step === 'pubmed' && isFail) {
    failNodeTimer('pubmed');
  } else if (step === 'search' && message.includes('All searches')) {
    setPipelineState('search', 'done');
    setPipelineState('pubmed', 'done');
    stopNodeTimer('search');
    stopNodeTimer('pubmed');
    setLineState('line-1-2a', 'done');
    setLineState('line-1-2b', 'done');
    setLineState('line-2a-3', 'active');
    setLineState('line-2b-3', 'active');
    setMobileLinks({ search: 'done', pubmed: 'done', extraction: 'active' });
  } else if (step === 'extraction' && message.includes('Extracting')) {
    setPipelineState('extraction', 'active');
    startNodeTimer('extraction');
    setLineState('line-2a-3', 'done');
    setLineState('line-2b-3', 'done');
    // Show progress in subtitle (e.g. "3/10")
    const match = message.match(/(\d+)\/(\d+)/);
    if (match) {
      getPipelineNodeElements('extraction').forEach((el) => {
        const sub = el.querySelector('.node-sub');
        if (sub) sub.textContent = `${match[1]} / ${match[2]}`;
      });
    }
  } else if (step === 'extraction' && (message.includes('Extracted') || message.includes('Skipping'))) {
    setPipelineState('extraction', 'done');
    stopNodeTimer('extraction');
    setLineState('line-3-4', 'active');
    // Show final count
    const match = message.match(/(\d+) relations/);
    if (match) {
      getPipelineNodeElements('extraction').forEach((el) => {
        const sub = el.querySelector('.node-sub');
        if (sub) sub.textContent = `${match[1]} relations`;
      });
    }
    setMobileLinks({ extraction: 'done', llm: 'active' });
  } else if (step === 'extraction' && isFail) {
    failNodeTimer('extraction');
    setLineState('line-3-4', 'active');
  } else if (step === 'llm' && message.includes('Generating')) {
    setPipelineState('extraction', 'done');
    stopNodeTimer('extraction');
    setLineState('line-3-4', 'done');
    setPipelineState('llm', 'active');
    startNodeTimer('llm');
    setMobileLinks({ extraction: 'done', llm: 'active' });
  } else if (step === 'llm' && (message.includes('generated') || message.includes('Skipping'))) {
    setPipelineState('llm', 'done');
    stopNodeTimer('llm');
    setLineState('line-4-5', 'active');
    setMobileLinks({ llm: 'done', done: 'active' });
  } else if (step === 'llm' && isFail) {
    failNodeTimer('llm');
    setLineState('line-4-5', 'active');
  } else if (step === 'done') {
    setPipelineState('done', 'done');
    stopNodeTimer('done');
    setLineState('line-4-5', 'done');
    setMobileLinks({ done: 'done' });
  }
}

/* ---- Progressive / Partial Data ---- */

function handlePartialData(data) {
  if (data.enrichment_results) {
    const er = data.enrichment_results;
    const panel = document.getElementById('panel-enrichment');
    if (!panel) return;

    const enrichKeys = Object.keys(er);
    const goCount = (er.GO || []).length;
    const keggCount = (er.KEGG || []).length;
    const subLabels = { GO: 'GO Biological Process', KEGG: 'KEGG Pathways' };

    let subTabsHtml = '<div class="sub-tabs">';
    let subPanelsHtml = '';
    enrichKeys.forEach((k, j) => {
      const subActive = j === 0 ? ' active' : '';
      subTabsHtml += `<button class="sub-tab-btn${subActive}" data-subtab="enrich-${k}" onclick="switchSubTab('enrichment','enrich-${k}')">${subLabels[k] || k}</button>`;
      subPanelsHtml += `<div class="sub-panel${subActive}" id="subpanel-enrich-${k}"><div class="table-card"><div class="table-wrap">${buildTable(er[k] || [])}</div></div></div>`;
    });
    subTabsHtml += '</div>';
    panel.innerHTML = enrichKeys.length ? subTabsHtml + subPanelsHtml : '<div class="no-data">No enrichment results.</div>';

    // Update enrichment tab count
    const tabBtn = document.querySelector('[data-tab="enrichment"]');
    if (tabBtn) {
      const count = goCount + keggCount;
      tabBtn.innerHTML = `<i data-lucide="bar-chart-3"></i> Enrichment <span class="tab-count">${count}</span>`;
    }
    lucide.createIcons();
  }

  const currentResult = getCurrentResult();
  const currentEnrichment = currentResult?.enrichment_results || {};
  const hasEnrichment = Object.values(currentEnrichment).some((rows) => Array.isArray(rows) && rows.length > 0);

  if (data.sources && hasEnrichment) {
    const sources = data.sources;
    const webSources = sources.web || [];
    const pubmedSources = sources.pubmed || [];
    const panel = document.getElementById('panel-sources');
    if (!panel) return;

    let subTabsHtml = '<div class="sub-tabs">';
    let subPanelsHtml = '';
    subTabsHtml += `<button class="sub-tab-btn active" data-subtab="src-pubmed" onclick="switchSubTab('sources','src-pubmed')">PubMed ${pubmedSources.length}</button>`;
    subPanelsHtml += `<div class="sub-panel active" id="subpanel-src-pubmed"><div class="table-card"><div class="sources-list">${renderPubmedSources(pubmedSources)}</div></div></div>`;
    subTabsHtml += `<button class="sub-tab-btn" data-subtab="src-web" onclick="switchSubTab('sources','src-web')">Web ${webSources.length}</button>`;
    subPanelsHtml += `<div class="sub-panel" id="subpanel-src-web"><div class="table-card"><div class="sources-list">${renderWebSources(webSources)}</div></div></div>`;
    subTabsHtml += '</div>';
    panel.innerHTML = subTabsHtml + subPanelsHtml;

    // Update sources tab count
    const tabBtn = document.querySelector('[data-tab="sources"]');
    if (tabBtn) {
      const total = webSources.length + pubmedSources.length;
      tabBtn.innerHTML = `<i data-lucide="book-open"></i> Sources <span class="tab-count">${total}</span>`;
    }
    lucide.createIcons();
  }
}

/* ---- Pipeline HTML (reusable in tab) ---- */

function getPipelineHTML() {
  return `
    <div class="pipeline-tab-wrap">
      <div class="loading-header">
        <h3>Pipeline Execution</h3>
        <p id="loadingMsg">Initializing pipeline...</p>
      </div>
      <div class="pipeline-canvas">
        <svg class="pipeline-desktop-map" viewBox="0 0 1020 280" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0">
          <path id="line-0-1" class="pipe-line pending" d="M 75 140 L 210 140" fill="none"/>
          <path id="line-1-2a" class="pipe-line pending" d="M 210 140 C 300 140, 300 65, 390 65" fill="none"/>
          <path id="line-1-2b" class="pipe-line pending" d="M 210 140 C 300 140, 300 215, 390 215" fill="none"/>
          <path id="line-2a-3" class="pipe-line pending" d="M 390 65 C 480 65, 480 140, 570 140" fill="none"/>
          <path id="line-2b-3" class="pipe-line pending" d="M 390 215 C 480 215, 480 140, 570 140" fill="none"/>
          <path id="line-3-4" class="pipe-line pending" d="M 570 140 L 730 140" fill="none"/>
          <path id="line-4-5" class="pipe-line pending" d="M 730 140 L 900 140" fill="none"/>
        </svg>
        <div class="pipe-node" data-status="pending" id="node-enrichment" style="left:75px;top:140px">
          <div class="node-circle"><i data-lucide="network"></i></div>
          <div class="node-label"><div class="node-title">Enrichment</div><div class="node-sub">GO & KEGG</div><div class="node-timer"></div></div>
        </div>
        <div class="pipe-node" data-status="pending" id="node-planning" style="left:210px;top:140px">
          <div class="node-circle"><i data-lucide="route"></i></div>
          <div class="node-label"><div class="node-title">Planning</div><div class="node-sub">Query Strategy</div><div class="node-timer"></div></div>
        </div>
        <div class="pipe-node" data-status="pending" id="node-search" style="left:390px;top:65px">
          <div class="node-circle"><i data-lucide="globe"></i></div>
          <div class="node-label"><div class="node-title">Web Search</div><div class="node-sub">Tavily API</div><div class="node-timer"></div></div>
        </div>
        <div class="pipe-node" data-status="pending" id="node-pubmed" style="left:390px;top:215px">
          <div class="node-circle"><i data-lucide="book-open"></i></div>
          <div class="node-label"><div class="node-title">PubMed</div><div class="node-sub">Entrez API</div><div class="node-timer"></div></div>
        </div>
        <div class="pipe-node" data-status="pending" id="node-extraction" style="left:570px;top:140px">
          <div class="node-circle"><i data-lucide="scan-search"></i></div>
          <div class="node-label"><div class="node-title">Extraction</div><div class="node-sub">Relations</div><div class="node-timer"></div></div>
        </div>
        <div class="pipe-node" data-status="pending" id="node-llm" style="left:730px;top:140px">
          <div class="node-circle"><i data-lucide="brain-circuit"></i></div>
          <div class="node-label"><div class="node-title">Synthesis</div><div class="node-sub">LLM Gen</div><div class="node-timer"></div></div>
        </div>
        <div class="pipe-node" data-status="pending" id="node-done" style="left:900px;top:140px">
          <div class="node-circle"><i data-lucide="file-text"></i></div>
          <div class="node-label"><div class="node-title">Report</div><div class="node-sub">Structuring</div><div class="node-timer"></div></div>
        </div>
        <div class="pipeline-mobile-rail">
          <div class="mobile-step" data-branch="single">
            <div class="mobile-link" data-link-status="pending"></div>
            <div class="pipe-node mobile-node" data-status="pending" id="node-enrichment-mobile">
              <div class="node-circle"><i data-lucide="network"></i></div>
              <div class="node-label"><div class="node-title">Enrichment</div><div class="node-sub">GO & KEGG</div><div class="node-timer"></div></div>
            </div>
          </div>
          <div class="mobile-step" data-branch="single">
            <div class="mobile-link" data-link-status="pending"></div>
            <div class="pipe-node mobile-node" data-status="pending" id="node-planning-mobile">
              <div class="node-circle"><i data-lucide="route"></i></div>
              <div class="node-label"><div class="node-title">Planning</div><div class="node-sub">Query Strategy</div><div class="node-timer"></div></div>
            </div>
          </div>
          <div class="mobile-branch-group">
            <div class="mobile-branch-head">
              <span class="branch-kicker">Parallel Retrieval</span>
              <span class="branch-rule"></span>
            </div>
            <div class="mobile-branch-grid">
              <div class="mobile-step" data-branch="left">
                <div class="mobile-link" data-link-status="pending"></div>
                <div class="pipe-node mobile-node" data-status="pending" id="node-search-mobile">
                  <div class="node-circle"><i data-lucide="globe"></i></div>
                  <div class="node-label"><div class="node-title">Web Search</div><div class="node-sub">Tavily API</div><div class="node-timer"></div></div>
                </div>
              </div>
              <div class="mobile-step" data-branch="right">
                <div class="mobile-link" data-link-status="pending"></div>
                <div class="pipe-node mobile-node" data-status="pending" id="node-pubmed-mobile">
                  <div class="node-circle"><i data-lucide="book-open"></i></div>
                  <div class="node-label"><div class="node-title">PubMed</div><div class="node-sub">Entrez API</div><div class="node-timer"></div></div>
                </div>
              </div>
            </div>
          </div>
          <div class="mobile-step mobile-merge" data-branch="single">
            <div class="mobile-link" data-link-status="pending"></div>
            <div class="pipe-node mobile-node" data-status="pending" id="node-extraction-mobile">
              <div class="node-circle"><i data-lucide="scan-search"></i></div>
              <div class="node-label"><div class="node-title">Extraction</div><div class="node-sub">Relations</div><div class="node-timer"></div></div>
            </div>
          </div>
          <div class="mobile-step" data-branch="single">
            <div class="mobile-link" data-link-status="pending"></div>
            <div class="pipe-node mobile-node" data-status="pending" id="node-llm-mobile">
              <div class="node-circle"><i data-lucide="brain-circuit"></i></div>
              <div class="node-label"><div class="node-title">Synthesis</div><div class="node-sub">LLM Gen</div><div class="node-timer"></div></div>
            </div>
          </div>
          <div class="mobile-step" data-branch="single">
            <div class="mobile-link" data-link-status="pending"></div>
            <div class="pipe-node mobile-node" data-status="pending" id="node-done-mobile">
              <div class="node-circle"><i data-lucide="file-text"></i></div>
              <div class="node-label"><div class="node-title">Report</div><div class="node-sub">Structuring</div><div class="node-timer"></div></div>
            </div>
          </div>
        </div>
      </div>
    </div>`;
}

/* ---- Analysis ---- */

function runAnalysis() {
  const validation = getCurrentValidation();
  const genes = validation && validation.normalized_genes.length
    ? validation.normalized_genes.join(' ')
    : document.getElementById('genes').value.trim();
  const disease = document.getElementById('disease').value.trim();
  const pval = document.getElementById('pval').value;
  if (!genes) return;
  if (!validation || !validation.normalized_genes.length) {
    showToast('Validate genes before running the pipeline');
    return;
  }

  appState.pipelineRunning = true;
  document.getElementById('runBtn').disabled = true;
  document.getElementById('validateBtn').disabled = true;

  // Set up results view immediately with pipeline tab
  document.getElementById('statusBadge').innerHTML = '<i data-lucide="loader-2"></i> Running...';
  document.getElementById('resultsTitle').textContent = disease || 'Analysis';
  const geneList = genes.split(/[,\s\n]+/).filter(g => g.trim());
  document.getElementById('resultsMeta').innerHTML = `Targeting <b>${geneList.length}</b> genes`;
  document.getElementById('statsGrid').innerHTML = '';
  document.getElementById('cancelBtn').style.display = '';

  // Build tabs: Pipeline first, others as placeholders
  document.getElementById('resultTabs').innerHTML =
    `<button class="tab-btn active" data-tab="pipeline" onclick="switchTab('pipeline')"><i data-lucide="activity"></i> Pipeline</button>` +
    `<button class="tab-btn" data-tab="genes" onclick="switchTab('genes')"><i data-lucide="list-tree"></i> Genes</button>` +
    `<button class="tab-btn" data-tab="enrichment" onclick="switchTab('enrichment')"><i data-lucide="bar-chart-3"></i> Enrichment</button>` +
    `<button class="tab-btn" data-tab="sources" onclick="switchTab('sources')"><i data-lucide="book-open"></i> Sources</button>` +
    `<button class="tab-btn" data-tab="network" onclick="switchTab('network')"><i data-lucide="share-2"></i> Network</button>` +
    `<button class="tab-btn" data-tab="report" onclick="switchTab('report')"><i data-lucide="file-text"></i> Insight Report</button>`;

  document.getElementById('tabPanels').innerHTML =
    `<div class="tab-panel active" id="panel-pipeline">${getPipelineHTML()}</div>` +
    `<div class="tab-panel" id="panel-genes">${renderStateCard({ tone: 'waiting', icon: 'loader-2', title: 'Waiting for validation details', description: 'Validate genes to review accepted, remapped, and rejected symbols.', compact: true })}</div>` +
    `<div class="tab-panel" id="panel-enrichment">${renderStateCard({ tone: 'waiting', icon: 'loader-2', title: 'Waiting for pipeline', description: 'Run the pipeline to populate enrichment tables and ranked terms.', compact: true })}</div>` +
    `<div class="tab-panel" id="panel-sources">${renderStateCard({ tone: 'waiting', icon: 'loader-2', title: 'Waiting for pipeline', description: 'Source articles and PubMed evidence will appear after analysis.', compact: true })}</div>` +
    `<div class="tab-panel" id="panel-network">${renderStateCard({ tone: 'waiting', icon: 'loader-2', title: 'Waiting for pipeline', description: 'The relation network is generated after extraction completes.', compact: true })}</div>` +
    `<div class="tab-panel" id="panel-report">${renderStateCard({ tone: 'waiting', icon: 'loader-2', title: 'Waiting for pipeline', description: 'A report will be generated once the analysis finishes.', compact: true })}</div>`;

  document.getElementById('navResults').disabled = false;
  switchView('results');
  lucide.createIcons();

  // Reset pipeline node states
  resetPipeline();

  const params = new URLSearchParams({ genes, disease, pval });
  const es = api.startAnalysisStream(params);
  appState.eventSource = es;

  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.event === 'result') {
      es.close();
      appState.eventSource = null;
      appState.pipelineRunning = false;
      if (validation) {
        msg.data.gene_validation = validation;
      }
      setCurrentResult(msg.data);
      resetChatSession();
      finishPipeline(msg.data, false);
    } else if (msg.event === 'error') {
      es.close();
      appState.eventSource = null;
      appState.pipelineRunning = false;
      document.getElementById('runBtn').disabled = false;
      document.getElementById('validateBtn').disabled = false;
      document.getElementById('cancelBtn').style.display = 'none';
      document.getElementById('statusBadge').innerHTML = '<i data-lucide="alert-circle"></i> Error';
      const msgEl = document.getElementById('loadingMsg');
      if (msgEl) msgEl.textContent = msg.message;
      lucide.createIcons();
    } else {
      updatePipelineFromEvent(msg.event, msg.message);
      // Handle partial data
      if (msg.data) handlePartialData(msg.data);
    }
  };

  es.onerror = () => {
    es.close();
    appState.eventSource = null;
    appState.pipelineRunning = false;
    document.getElementById('runBtn').disabled = false;
    document.getElementById('validateBtn').disabled = false;
    document.getElementById('cancelBtn').style.display = 'none';
    document.getElementById('statusBadge').innerHTML = '<i data-lucide="wifi-off"></i> Connection Lost';
    const msgEl = document.getElementById('loadingMsg');
    if (msgEl) msgEl.textContent = 'Connection lost.';
    lucide.createIcons();
  };
}

function cancelAnalysis() {
  if (appState.eventSource) {
    appState.eventSource.close();
    appState.eventSource = null;
  }
  appState.pipelineRunning = false;
  document.getElementById('runBtn').disabled = false;
  document.getElementById('validateBtn').disabled = false;
  document.getElementById('cancelBtn').style.display = 'none';

  // Mark active nodes as cancelled
  ['enrichment','planning','search','pubmed','extraction','llm','done'].forEach(n => {
    if (getPipelineNodeElements(n).some((el) => el.dataset.status === 'active')) {
      setPipelineState(n, 'cancelled');
      stopNodeTimer(n);
    }
  });

  document.getElementById('statusBadge').innerHTML = '<i data-lucide="circle-stop"></i> Stopped';
  const msgEl = document.getElementById('loadingMsg');
  if (msgEl) msgEl.textContent = 'Pipeline stopped by user.';
  lucide.createIcons();

  // Save partial result if we have anything from history context
  showToast('Pipeline stopped — partial results preserved');
}

function finishPipeline(data, wasCancelled) {
  document.getElementById('runBtn').disabled = false;
  document.getElementById('validateBtn').disabled = false;
  document.getElementById('cancelBtn').style.display = 'none';

  if (!wasCancelled) {
    document.getElementById('statusBadge').innerHTML = '<i data-lucide="check-circle-2"></i> Analysis Complete';
  }

  setCurrentResult(data);
  resetChatSession();
  renderResultTabs(getCurrentResult());
  refreshHistory().catch((err) => console.error(err));
  lucide.createIcons();
}

/* ---- Render Results ---- */

function renderResultTabs(data) {
  const er = data.enrichment_results || {};
  const sources = data.sources || {};
  const webSources = sources.web || data.web_sources || [];
  const pubmedSources = sources.pubmed || [];
  const goCount = (er.GO || []).length;
  const keggCount = (er.KEGG || []).length;
  const hasEnrichment = goCount > 0 || keggCount > 0;
  const totalSources = hasEnrichment ? (webSources.length + pubmedSources.length) : 0;
  const relationsCount = (data.gene_relations || []).length;
  const graphData = data.graph || { nodes: [], edges: [] };
  const geneValidation = data.gene_validation || getCurrentValidation() || {
    rows: [],
    summary: { accepted: data.input_genes.length, remapped: 0, rejected: 0, total: data.input_genes.length },
  };

  // Header
  document.getElementById('resultsTitle').textContent = data.disease_context || 'Analysis';
  document.getElementById('resultsMeta').innerHTML =
    `Targeting <b>${data.input_genes.length}</b> genes`;

  // Stats grid
  document.getElementById('statsGrid').innerHTML = `
    <div class="stat-card">
      <div class="stat-icon teal"><i data-lucide="dna"></i></div>
      <div class="stat-number">${data.input_genes.length}</div>
      <div class="stat-label">Input Genes</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon blue"><i data-lucide="git-branch"></i></div>
      <div class="stat-number">${goCount + keggCount}</div>
      <div class="stat-label">Enriched Terms</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon amber"><i data-lucide="scan-search"></i></div>
      <div class="stat-number">${relationsCount}</div>
      <div class="stat-label">Relations</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon green"><i data-lucide="book-open"></i></div>
      <div class="stat-number">${totalSources}</div>
      <div class="stat-label">Sources</div>
    </div>
  `;

  // Build tab buttons — keep pipeline, update counts
  const mainTabs = [
    { key: 'pipeline', label: 'Pipeline', icon: 'activity', count: null },
    { key: 'genes', label: 'Genes', icon: 'list-tree', count: (geneValidation.rows || []).length || data.input_genes.length },
    { key: 'enrichment', label: 'Enrichment', icon: 'bar-chart-3', count: goCount + keggCount },
    { key: 'sources', label: 'Sources', icon: 'book-open', count: totalSources },
    { key: 'network', label: 'Network', icon: 'share-2', count: graphData.nodes.length },
    { key: 'report', label: 'Insight Report', icon: 'file-text', count: null },
  ];

  let tabsHtml = '';
  let panelsHtml = '';

  mainTabs.forEach((tab, i) => {
    const active = tab.key === 'pipeline' ? ' active' : '';
    const countHtml = tab.count !== null ? `<span class="tab-count">${tab.count}</span>` : '';
    tabsHtml += `<button class="tab-btn${active}" data-tab="${tab.key}" onclick="switchTab('${tab.key}')"><i data-lucide="${tab.icon}"></i> ${tab.label} ${countHtml}</button>`;

    if (tab.key === 'pipeline') {
      // Preserve existing pipeline panel content (with timers)
      const existing = document.getElementById('panel-pipeline');
      if (existing) {
        panelsHtml += `<div class="tab-panel" id="panel-pipeline">${existing.innerHTML}</div>`;
      } else {
        panelsHtml += `<div class="tab-panel" id="panel-pipeline">${getPipelineHTML()}</div>`;
      }

    } else if (tab.key === 'genes') {
      panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">
        ${renderValidationSummaryCard(geneValidation, true)}
      </div>`;

    } else if (tab.key === 'enrichment') {
      const enrichKeys = Object.keys(er);
      const subLabels = { GO: 'GO Biological Process', KEGG: 'KEGG Pathways' };
      let subTabsHtml = '<div class="sub-tabs">';
      let subPanelsHtml = '';
      enrichKeys.forEach((k, j) => {
        const subActive = j === 0 ? ' active' : '';
        subTabsHtml += `<button class="sub-tab-btn${subActive}" data-subtab="enrich-${k}" onclick="switchSubTab('enrichment','enrich-${k}')">${subLabels[k] || k}</button>`;
        subPanelsHtml += `<div class="sub-panel${subActive}" id="subpanel-enrich-${k}"><div class="table-card"><div class="table-wrap">${buildTable(er[k] || [])}</div></div></div>`;
      });
      subTabsHtml += '</div>';
      panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">${enrichKeys.length ? subTabsHtml + subPanelsHtml : `<div class="table-card">${renderStateCard({
        icon: 'table-properties',
        title: 'No enrichment results',
        description: 'No significant terms are available in the selected databases.',
        compact: true,
      })}</div>`}</div>`;

    } else if (tab.key === 'network') {
      panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">${hasEnrichment
        ? `<div class="table-card" style="padding:0;position:relative">
            <div id="networkGraph" style="width:100%;height:520px;overflow:hidden"></div>
          </div>`
        : renderStateCard({
            tone: 'waiting',
            icon: 'loader-2',
            title: 'Waiting for enrichment results',
            description: 'The network view will appear after enrichment and relation extraction are ready.',
            compact: true,
          })}</div>`;

    } else if (tab.key === 'sources') {
      if (!hasEnrichment) {
        panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">${renderStateCard({
          tone: 'waiting',
          icon: 'loader-2',
          title: 'Waiting for enrichment results',
          description: 'Sources will be shown after GO or KEGG results are available.',
          compact: true,
        })}</div>`;
      } else {
        let subTabsHtml = '<div class="sub-tabs">';
        let subPanelsHtml = '';
        subTabsHtml += `<button class="sub-tab-btn active" data-subtab="src-pubmed" onclick="switchSubTab('sources','src-pubmed')">PubMed ${pubmedSources.length}</button>`;
        subPanelsHtml += `<div class="sub-panel active" id="subpanel-src-pubmed"><div class="table-card"><div class="sources-list">${renderPubmedSources(pubmedSources)}</div></div></div>`;
        subTabsHtml += `<button class="sub-tab-btn" data-subtab="src-web" onclick="switchSubTab('sources','src-web')">Web ${webSources.length}</button>`;
        subPanelsHtml += `<div class="sub-panel" id="subpanel-src-web"><div class="table-card"><div class="sources-list">${renderWebSources(webSources)}</div></div></div>`;
        subTabsHtml += '</div>';
        panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">${subTabsHtml}${subPanelsHtml}</div>`;
      }

    } else if (tab.key === 'report') {
      const ts = data.timestamp ? new Date(data.timestamp).toLocaleString() : new Date().toLocaleString();
      panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">${hasEnrichment
        ? `<div class="report-shell">
            <div class="report-banner">
              <div class="banner-item"><i data-lucide="flask-conical"></i> Context: <b>&nbsp;${esc(data.disease_context)}</b></div>
              <div class="banner-item"><i data-lucide="clock"></i> <b>&nbsp;${ts}</b></div>
            </div>
            <div class="report-content">${renderMarkdownSafe(data.llm_insight || '_No report generated._')}</div>
          </div>`
        : renderStateCard({
            tone: 'waiting',
            icon: 'loader-2',
            title: 'Waiting for enrichment results',
            description: 'The report will appear after enrichment and evidence retrieval complete.',
            compact: true,
          })}</div>`;
    }
  });

  document.getElementById('resultTabs').innerHTML = tabsHtml;
  document.getElementById('tabPanels').innerHTML = panelsHtml;
  lucide.createIcons();

  window._graphData = graphData;
}

// Keep old renderResult as alias for history loading
function renderResult(data) {
  document.getElementById('statusBadge').innerHTML = '<i data-lucide="check-circle-2"></i> Analysis Complete';
  document.getElementById('cancelBtn').style.display = 'none';
  renderResultTabs(data);
}

function renderValidationSummaryCard(data, inResults = false) {
  const rows = data.rows || [];
  if (!rows.length) {
    return renderStateCard({
      icon: 'shield-question',
      title: 'No validation details',
      description: 'This result does not contain gene validation metadata.',
      compact: true,
    });
  }

  const tableRows = rows.map((row) => {
    const normalized = row.normalized_gene
      ? `<button class="validation-gene-btn" onclick="openGeneDrawer('${escAttr(row.normalized_gene)}')">${esc(row.normalized_gene)}</button>`
      : '<span class="muted">-</span>';
    return `
      <tr>
        <td class="cell-term">${esc(row.input_gene)}</td>
        <td>${normalized}</td>
        <td><span class="status-pill ${escAttr(row.status)}">${esc(row.status)}</span></td>
        <td>${esc(row.source || '-')}</td>
        <td class="cell-overlap">${esc(row.gene_id || '-')}</td>
        <td>${esc(row.official_name || row.description || '-')}</td>
      </tr>
    `;
  }).join('');

  return `
    <div class="validation-panel${inResults ? ' validation-panel-results' : ''}">
      <div class="validation-head">
        <div>
          <h3>Gene Validation</h3>
          <p>Resolved symbols used by the analysis pipeline.</p>
        </div>
        <div class="validation-badges">
          <span class="validation-badge accepted">Accepted ${data.summary.accepted}</span>
          <span class="validation-badge remapped">Remapped ${data.summary.remapped}</span>
          <span class="validation-badge rejected">Rejected ${data.summary.rejected}</span>
        </div>
      </div>
      <div class="table-card table-card-flat">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Input Gene</th>
                <th>Normalized Gene</th>
                <th>Status</th>
                <th>Source</th>
                <th>Gene ID</th>
                <th>Official Name</th>
              </tr>
            </thead>
            <tbody>${tableRows}</tbody>
          </table>
        </div>
      </div>
      <div class="validation-note">
        Analysis ran with ${(data.normalized_genes || []).length || data.summary.accepted + data.summary.remapped} normalized genes.
      </div>
    </div>
  `;
}

/* ---- Network Graph (D3) ---- */

function renderNetworkGraph(graphData) {
  const container = document.getElementById('networkGraph');
  if (!container) return;
  container.innerHTML = '';

  const width = container.clientWidth || 900;
  const height = 520;

  const svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height)
    .attr('viewBox', [0, 0, width, height])
    .style('cursor', 'grab');

  const g = svg.append('g');
  const zoom = d3.zoom()
    .scaleExtent([0.3, 5])
    .on('zoom', (event) => { g.attr('transform', event.transform); });
  svg.call(zoom);

  const defs = svg.append('defs');
  ['relation','enrichment'].forEach(t => {
    defs.append('marker')
      .attr('id', 'arrow-' + t).attr('viewBox', '0 -4 8 8')
      .attr('refX', 20).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path').attr('d', 'M0,-3L7,0L0,3')
      .attr('fill', t === 'relation' ? '#98a2b3' : '#d0d5dd');
  });

  const nodes = graphData.nodes.map(d => ({...d}));
  const edges = graphData.edges.map(d => ({...d}));

  const typeColor = {
    gene: '#344054', go: '#667085', kegg: '#667085',
    disease: '#98a2b3', drug: '#98a2b3', pathway: '#667085', other: '#d0d5dd',
  };
  const typeRadius = {
    gene: 7, go: 5, kegg: 5,
    disease: 6, drug: 6, pathway: 5, other: 4,
  };

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => (typeRadius[d.type] || 5) + 6));

  const link = g.append('g')
    .selectAll('line').data(edges).join('line')
    .attr('stroke', d => d.type === 'relation' ? '#98a2b3' : '#e4e7ec')
    .attr('stroke-width', d => d.type === 'relation' ? 1.2 : 0.8)
    .attr('stroke-dasharray', d => d.type === 'enrichment' ? '3,3' : 'none')
    .attr('marker-end', d => d.type === 'relation' ? 'url(#arrow-relation)' : '');

  const node = g.append('g')
    .selectAll('g').data(nodes).join('g')
    .call(d3.drag()
      .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on('end', (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
    );

  node.append('circle')
    .attr('r', d => d.is_input ? (typeRadius[d.type] || 5) + 2 : (typeRadius[d.type] || 5))
    .attr('fill', d => d.is_input ? '#101828' : (typeColor[d.type] || '#d0d5dd'))
    .attr('stroke', d => d.is_input ? '#101828' : '#e4e7ec')
    .attr('stroke-width', d => d.is_input ? 2 : 1)
    .style('cursor', 'pointer');

  node.append('text')
    .text(d => d.label)
    .attr('x', 0).attr('y', d => -(typeRadius[d.type] || 5) - 5)
    .attr('text-anchor', 'middle')
    .attr('font-size', d => d.type === 'gene' ? '9px' : '8px')
    .attr('font-family', 'Manrope, sans-serif')
    .attr('font-weight', d => d.is_input ? '700' : '500')
    .attr('fill', d => d.is_input ? '#101828' : '#98a2b3')
    .style('pointer-events', 'none');

  node.on('mouseover', function(e, d) {
    const connected = new Set();
    connected.add(d.id);
    edges.forEach(edge => {
      if (edge.source.id === d.id) connected.add(edge.target.id);
      if (edge.target.id === d.id) connected.add(edge.source.id);
    });
    node.style('opacity', n => connected.has(n.id) ? 1 : 0.15);
    link.style('opacity', l => (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.06);
  }).on('mouseout', function() {
    node.style('opacity', 1);
    link.style('opacity', 1);
  });

  node.on('click', function(e, d) {
    const rels = (graphData.edges || []).filter(
      edge => edge.type === 'relation' && (edge.source === d.id || edge.target === d.id ||
        (edge.source.id || edge.source) === d.id || (edge.target.id || edge.target) === d.id)
    );
    if (rels.length > 0) {
      showToast(`${d.label}: ${rels.length} relations`, 3000);
    }
  });

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });
}

/* ---- Sources Rendering ---- */

function renderWebSources(sources) {
  if (!sources.length) return `<div class="table-card">${renderStateCard({
    icon: 'globe',
    title: 'No web sources',
    description: 'No web search results were captured for this analysis.',
    compact: true,
  })}</div>`;
  return sources.map(s =>
    `<div class="source-item">
      <div class="source-icon web"><i data-lucide="globe"></i></div>
      <div class="source-body">
        <a href="${escAttr(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">${esc(s.title || 'Untitled')}</a>
        <div class="source-url">${esc(s.url)}</div>
        <div class="source-snippet">${esc(s.content || '')}</div>
      </div>
    </div>`
  ).join('');
}

function renderPubmedSources(sources) {
  if (!sources.length) return `<div class="table-card">${renderStateCard({
    icon: 'book-open',
    title: 'No PubMed sources',
    description: 'No PubMed articles were retrieved for this analysis.',
    compact: true,
  })}</div>`;
  return sources.map(s => {
    const metaParts = [];
    if (s.pmid) metaParts.push(`<span class="source-meta-badge">PMID:${esc(s.pmid)}</span>`);
    if (s.journal) metaParts.push(`<span class="source-meta-text">${esc(s.journal)}</span>`);
    if (s.pub_date) metaParts.push(`<span class="source-meta-text">${esc(s.pub_date)}</span>`);
    if (s.authors) metaParts.push(`<span class="source-meta-text">${esc(s.authors)}</span>`);
    const pubmedHref = s.pmid
      ? `https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(String(s.pmid))}/`
      : '#';
    return `<div class="source-item">
      <div class="source-icon pubmed"><i data-lucide="graduation-cap"></i></div>
      <div class="source-body">
        <a href="${escAttr(pubmedHref)}" target="_blank" rel="noopener noreferrer">${esc(s.title || 'Untitled')}</a>
        <div class="source-meta">${metaParts.join('')}</div>
        <div class="source-snippet">${esc(s.abstract || '')}</div>
      </div>
    </div>`;
  }).join('');
}

/* ---- Tabs ---- */

function switchSubTab(parentKey, subKey) {
  const panel = document.getElementById('panel-' + parentKey);
  panel.querySelectorAll('.sub-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.subtab === subKey));
  panel.querySelectorAll('.sub-panel').forEach(p => p.classList.toggle('active', p.id === 'subpanel-' + subKey));
}

function switchTab(key) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === key));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + key));
  if (key === 'network' && window._graphData && window._graphData.nodes.length > 0) {
    const container = document.getElementById('networkGraph');
    if (container && !container.querySelector('svg')) {
      setTimeout(() => renderNetworkGraph(window._graphData), 50);
    }
  }
}

/* ---- Table ---- */

const COL_DEFS = [
  { key: 'term', label: 'Term', cls: 'cell-term' },
  { key: 'overlap', label: 'Overlap', cls: 'cell-overlap' },
  { key: 'p_value', label: 'P-value', cls: 'cell-pval' },
  { key: 'p_adjusted', label: 'Adj. P-value', cls: 'cell-pval' },
  { key: 'genes', label: 'Genes', cls: 'cell-genes' },
];

function buildTable(rows) {
  if (!rows.length) return renderStateCard({
    icon: 'table-properties',
    title: 'No significant results',
    description: 'No rows passed the current significance threshold.',
    compact: true,
  });
  let html = '<table><thead><tr>';
  COL_DEFS.forEach((c, i) => {
    html += `<th onclick="sortTableCol(this, ${i}, '${c.key}')">${c.label}<span class="sort-icon"><i data-lucide="chevron-up" style="width:12px;height:12px;"></i></span></th>`;
  });
  html += '</tr></thead><tbody>';
  rows.forEach(r => {
    const pv = r.p_adjusted ?? r.p_value ?? 1;
    const sigClass = pv < 0.001 ? ' sig-high' : pv < 0.01 ? ' sig-mid' : '';
    html += `<tr class="${sigClass}">`;
    COL_DEFS.forEach(c => {
      let v = r[c.key];
      if (c.key === 'genes' && typeof v === 'string') {
        const genes = v.split(/[;,]\s*/);
        const pills = genes.map(g => `<span class="gene-pill">${esc(g.trim())}</span>`).join('');
        html += `<td class="${c.cls || ''}">${pills}</td>`;
      } else {
        if (typeof v === 'number') v = v < 0.001 ? v.toExponential(2) : parseFloat(v.toFixed(4));
        html += `<td class="${c.cls || ''}">${v ?? ''}</td>`;
      }
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  return html;
}

function sortTableCol(th, colIdx, key) {
  const table = th.closest('table');
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.rows);
  const asc = th.dataset.asc !== '1';

  table.querySelectorAll('th').forEach(h => { h.classList.remove('sorted'); h.dataset.asc = ''; });
  th.classList.add('sorted');
  th.dataset.asc = asc ? '1' : '0';

  rows.sort((a, b) => {
    let va = a.cells[colIdx].textContent, vb = b.cells[colIdx].textContent;
    if (key === 'overlap') {
      const ra = va.split('/'), rb = vb.split('/');
      const na = parseInt(ra[0]) / (parseInt(ra[1]) || 1);
      const nb = parseInt(rb[0]) / (parseInt(rb[1]) || 1);
      return asc ? na - nb : nb - na;
    }
    const na = parseFloat(va), nb = parseFloat(vb);
    if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
    return asc ? va.localeCompare(vb) : vb.localeCompare(va);
  });
  rows.forEach(r => tbody.appendChild(r));
}

/* ---- Export ---- */

function downloadJSON() {
  const currentResult = getCurrentResult();
  if (!currentResult) return;
  const blob = new Blob([JSON.stringify(currentResult, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `enrichRAG_${currentResult.disease_context || 'result'}_${Date.now()}.json`;
  a.click();
  showToast('JSON downloaded');
}

function copyReport() {
  const currentResult = getCurrentResult();
  if (!currentResult) return;
  navigator.clipboard.writeText(currentResult.llm_insight || '')
    .then(() => showToast('Report copied'))
    .catch(() => showToast('Copy failed in this browser context', 3000));
}

/* ---- History ---- */

let historySearchTerm = '';

function getHistory() {
  return appState.historyItems.slice(0, MAX_HISTORY);
}

async function refreshHistory() {
  if (!appState.currentUser) {
    appState.historyItems = [];
    renderHistory();
    return;
  }
  const response = await api.history();
  if (!response.ok) {
    if (response.status === 401) {
      showAuthShell();
      return;
    }
    throw new Error('Failed to load history');
  }
  const payload = await response.json();
  appState.historyItems = payload.items || [];
  renderHistory();
}

async function deleteHistoryItem(id) {
  const response = await api.deleteHistoryItem(id);
  if (!response.ok) {
    showToast('Failed to delete history item', 3000);
    return;
  }
  await refreshHistory();
  showToast('History item deleted');
}

async function clearHistory() {
  const confirmed = window.confirm('確定要清除所有歷史紀錄嗎？');
  if (!confirmed) return;
  const response = await api.clearHistory();
  if (!response.ok) {
    showToast('Failed to clear history', 3000);
    return;
  }
  historySearchTerm = '';
  await refreshHistory();
  showToast('History cleared');
}

function getFilteredHistory(hist, searchTerm) {
  return hist
    .map((h, i) => ({ h, i }))
    .filter(({ h }) => {
      if (!searchTerm) return true;
      const genes = h.input_genes || [];
      const disease = h.disease_context || '';
      const haystack = `${disease} ${genes.join(' ')}`.toLowerCase();
      return haystack.includes(String(searchTerm).trim().toLowerCase());
    });
}

function renderHistoryList(hist, searchTerm = historySearchTerm) {
  const list = document.getElementById('historyList');
  if (!list) return;
  const filtered = getFilteredHistory(hist, searchTerm);
  let html = '';
  filtered.forEach(({ h, i }) => {
    const genes = h.input_genes || [];
    const disease = h.disease_context || '';
    const time = new Date(h.created_at).toLocaleString();
    const geneText = genes.length ? genes.join(', ') : 'Stored analysis without gene inputs';
    html += `<li class="history-item">
      <button class="history-load-btn" type="button" onclick="loadHistory(${h.id})">
        <div class="hist-info">
          <div class="hist-title">
            <span class="hist-disease">${esc(disease)}</span>
            <span class="hist-gene-badge">${genes.length} genes</span>
          </div>
          <div class="hist-genes">${esc(geneText)}</div>
        </div>
        <div class="hist-actions">
          <span class="hist-time">${time}</span>
          <span class="hist-arrow" aria-hidden="true"><i data-lucide="chevron-right"></i></span>
        </div>
      </button>
      <button class="history-delete-btn" type="button" onclick="deleteHistoryItem(${h.id})" aria-label="Delete history item">
        <i data-lucide="trash-2"></i>
      </button>
    </li>`;
  });
  if (!filtered.length) {
    html += `<li class="history-empty-row">
      <div class="history-empty-copy">No analysis history found.</div>
    </li>`;
  }
  list.innerHTML = html;
  lucide.createIcons();
}

function handleHistorySearchInput(value) {
  const input = document.getElementById('historySearchInput');
  const start = input ? input.selectionStart : null;
  const end = input ? input.selectionEnd : null;
  historySearchTerm = value;
  renderHistoryList(getHistory(), historySearchTerm);
  const nextInput = document.getElementById('historySearchInput');
  if (nextInput) {
    nextInput.focus();
    if (start !== null && end !== null) {
      nextInput.setSelectionRange(start, end);
    }
  }
}

function renderHistory() {
  const hist = getHistory();
  document.getElementById('historyBadge').textContent = hist.length;
  if (!hist.length) {
    document.getElementById('historyCard').innerHTML = `
      ${renderStateCard({
        icon: 'clock-3',
        title: 'No analyses yet',
        description: 'Run your first enrichment analysis to see saved results here.',
      })}`;
    lucide.createIcons();
    return;
  }
  document.getElementById('historyCard').innerHTML = `
    <div class="history-toolbar">
      <div class="history-toolbar-meta">
        <div class="history-toolbar-copy">${hist.length} saved result${hist.length > 1 ? 's' : ''}</div>
        <label class="history-search-shell" aria-label="Search history">
          <i data-lucide="search"></i>
          <input type="text" id="historySearchInput" class="history-search-input" placeholder="Search...">
        </label>
      </div>
      <button class="history-clear-btn" type="button" onclick="clearHistory()">
        <i data-lucide="trash-2"></i> Clear History
      </button>
    </div>
    <ul class="history-list" id="historyList"></ul>`;
  const input = document.getElementById('historySearchInput');
  if (input) {
    input.value = historySearchTerm;
    input.addEventListener('input', (event) => handleHistorySearchInput(event.target.value));
  }
  renderHistoryList(hist, historySearchTerm);
}

function loadHistory(idx) {
  api.loadHistoryItem(idx)
    .then((response) => {
      if (!response.ok) throw new Error('Failed to load saved result');
      return response.json();
    })
    .then((data) => {
      setCurrentResult(data);
      setCurrentValidation(data?.gene_validation || null);
      if (getCurrentValidation()) {
        renderValidationSummary(getCurrentValidation());
        document.getElementById('runBtn').disabled = !(getCurrentValidation().normalized_genes || []).length;
      } else {
        resetValidationUI();
      }
      resetChatSession();
      const currentResult = getCurrentResult();
      document.getElementById('genes').value = deriveInputGenes(currentResult).join(', ');
      document.getElementById('disease').value = currentResult.disease_context || '';
      document.getElementById('navResults').disabled = false;
      renderResult(currentResult);
      switchView('results');
      showToast('History loaded');
    })
    .catch((err) => {
      console.error(err);
      showToast('Failed to load history', 3000);
    });
}

/* ---- Chat ---- */

function resetChatSession() {
  resetChatHistory();
  const body = document.getElementById('chatBody');
  if (!body) return;
  body.innerHTML = `
    <div class="chat-message assistant chat-message-intro">
      <div class="msg-content">
        ${renderStateCard({
          icon: 'message-square-text',
          title: 'EnrichRAG Assistant',
          description: 'Ask about the current analysis result, report, sources, or relations.',
          compact: true,
        })}
        <div class="chat-welcome-rule"></div>
        <div class="chat-suggestions" id="chatSuggestions"></div>
      </div>
    </div>`;
  renderChatSuggestions();
  lucide.createIcons();
}

function toggleChatDrawer(forceOpen) {
  const drawer = document.getElementById('chatDrawer');
  const backdrop = document.getElementById('chatBackdrop');
  if (!drawer || !backdrop) return;
  appState.isChatOpen = forceOpen !== undefined ? forceOpen : !appState.isChatOpen;
  drawer.classList.toggle('open', appState.isChatOpen);
  drawer.setAttribute('aria-hidden', appState.isChatOpen ? 'false' : 'true');
  backdrop.classList.toggle('open', appState.isChatOpen);
  if (appState.isChatOpen) {
    setActiveDrawer('chat', drawer);
    setTimeout(() => {
      const input = document.getElementById('chatInput');
      if (input) input.focus();
    }, 150);
  } else {
    clearActiveDrawer('chat');
  }
}

function appendChatMessage(role, text, isStreaming = false) {
  const body = document.getElementById('chatBody');
  if (!body) return null;

  let msgDiv = null;
  if (isStreaming && body.lastElementChild?.dataset?.streaming === 'true') {
    msgDiv = body.lastElementChild;
    const contentDiv = msgDiv.querySelector('.msg-content');
    if (text === '...typing...') {
      contentDiv.innerHTML = '<span class="typing-indicator">...</span>';
    } else {
      msgDiv.dataset.raw = (msgDiv.dataset.raw || '') + text;
      contentDiv.innerHTML = renderMarkdownSafe(msgDiv.dataset.raw);
    }
  } else {
    msgDiv = document.createElement('div');
    msgDiv.className = `chat-message ${role}`;
    msgDiv.dataset.streaming = isStreaming ? 'true' : 'false';
    msgDiv.dataset.raw = text === '...typing...' ? '' : text;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';
    contentDiv.innerHTML = text === '...typing...'
      ? '<span class="typing-indicator">...</span>'
      : renderMarkdownSafe(text);
    msgDiv.appendChild(contentDiv);
    if (role === 'assistant' && !msgDiv.classList.contains('chat-message-intro')) {
      msgDiv.appendChild(buildChatActionBar());
    }
    body.appendChild(msgDiv);
  }

  body.scrollTop = body.scrollHeight;
  return msgDiv;
}

function buildChatActionBar() {
  const bar = document.createElement('div');
  bar.className = 'chat-action-bar';
  bar.innerHTML = `
    <button type="button" class="chat-action-btn" title="Copy response" onclick="copyChatMessage(this)">
      <svg class="chat-action-icon" xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect>
        <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path>
      </svg>
      <span>Copy</span>
    </button>`;
  return bar;
}

function copyChatMessage(button) {
  const message = button.closest('.chat-message');
  const raw = message?.dataset?.raw || '';
  if (!raw) {
    showToast('Nothing to copy', 2000);
    return;
  }
  navigator.clipboard.writeText(raw)
    .then(() => showToast('Response copied'))
    .catch(() => showToast('Copy failed in this browser context', 3000));
}

function finishChatStream() {
  const body = document.getElementById('chatBody');
  if (body?.lastElementChild) {
    body.lastElementChild.dataset.streaming = 'false';
  }
}

function getSuggestedQuestions(result) {
  if (!result) {
    return [
      'What does this analysis show?',
      'Which pathways are most enriched?',
      'What genes stand out in this result?',
    ];
  }

  const suggestions = [];
  const disease = result.disease_context || 'this disease context';
  const queryPlan = result.query_plan || {};
  const topGenes = (queryPlan.top_genes || []).filter(Boolean).slice(0, 3);
  const goRows = (result.enrichment_results?.GO || []).slice(0, 2);
  const keggRows = (result.enrichment_results?.KEGG || []).slice(0, 2);
  const relations = result.gene_relations || [];
  const sources = result.sources || {};
  const validation = result.gene_validation || {};
  const remapped = validation.summary?.remapped || 0;
  const accepted = validation.summary?.accepted || result.input_genes?.length || 0;
  const graphNodes = result.graph?.nodes || [];
  const report = result.llm_insight || '';
  const topRelation = relations[0];
  const topPubmed = (sources.pubmed || [])[0];

  suggestions.push(`What is the main biological story of this ${disease} analysis?`);

  if (goRows.length > 0) {
    suggestions.push(`Why is "${goRows[0].term}" enriched in this gene set?`);
    suggestions.push(`Which genes appear to drive "${goRows[0].term}" most strongly?`);
  }
  if (keggRows.length > 0) {
    suggestions.push(`Which KEGG pathways matter most here, and why?`);
    suggestions.push(`How should I interpret ${keggRows[0].term} in the context of ${disease}?`);
  }
  if (topGenes.length > 0) {
    suggestions.push(`Which of ${topGenes.join(', ')} appear most central in the result?`);
  }
  if (topRelation) {
    const relGenes = [topRelation.gene_a, topRelation.gene_b].filter(Boolean).slice(0, 2);
    if (relGenes.length === 2) {
      suggestions.push(`What evidence links ${relGenes[0]} and ${relGenes[1]} in this analysis?`);
    }
    suggestions.push('What relationships in the extracted evidence look most important?');
  }
  if (remapped > 0) {
    suggestions.push('Did any validated genes get remapped, and does that affect interpretation?');
  }
  if (topPubmed?.title) {
    suggestions.push(`Which source best supports the conclusion, starting with "${topPubmed.title}"?`);
  } else if ((sources.pubmed || []).length > 0) {
    suggestions.push('Which PubMed sources best support the current conclusion?');
  }
  if (accepted > 0 && accepted <= 20) {
    suggestions.push('How would you break these genes into functional modules?');
  }
  if (graphNodes.length > 0) {
    suggestions.push('What does the network structure suggest about the most connected genes?');
  }
  if (report) {
    suggestions.push('Can you summarize the report into the three most important takeaways?');
  }

  return Array.from(new Set(suggestions)).slice(0, 4);
}

function renderChatSuggestions() {
  const container = document.getElementById('chatSuggestions');
  if (!container) return;
  const questions = getSuggestedQuestions(getCurrentResult());
  if (!questions.length) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML =
    `<p class="chat-suggestions-label">Suggested Questions</p>` +
    questions.map((question) => (
      `<button type="button" class="chat-suggestion-btn" onclick="submitSuggestedQuestion('${escAttr(question)}')">` +
      `<i data-lucide="arrow-right"></i>${esc(question)}</button>`
    )).join('');
}

function submitSuggestedQuestion(question) {
  const input = document.getElementById('chatInput');
  if (!input) return;
  input.value = question;
  handleChatSubmit({
    preventDefault() {},
  });
}

async function handleChatSubmit(e) {
  e.preventDefault();
  const currentResult = getCurrentResult();
  if (!currentResult) {
    showToast('No analysis results available to query.', 3000);
    return;
  }

  const inputEl = document.getElementById('chatInput');
  const query = inputEl.value.trim();
  if (!query) return;

  inputEl.value = '';
  inputEl.disabled = true;

  appendChatMessage('user', query);
  appendChatMessage('assistant', '...typing...', true);

  const payload = {
    query,
    result: currentResult,
    history: getChatHistory(),
  };

  try {
    const response = await api.chat(payload);

    if (!response.ok) {
      throw new Error('Chat API returned ' + response.status);
    }

    const body = document.getElementById('chatBody');
    if (body.lastElementChild?.dataset?.streaming === 'true') {
      body.lastElementChild.dataset.raw = '';
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let assistantReply = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const chunk of parts) {
        if (!chunk.startsWith('data: ')) continue;
        const dataStr = chunk.slice(6).trim();
        if (!dataStr) continue;
        const data = JSON.parse(dataStr);
        if (data.event === 'chunk') {
          assistantReply += data.data;
          appendChatMessage('assistant', data.data, true);
        } else if (data.event === 'done') {
          finishChatStream();
        } else if (data.event === 'error') {
          finishChatStream();
          appendChatMessage('assistant', `*Error: ${data.message}*`);
          throw new Error(data.message);
        }
      }
    }

    pushChatHistory({ role: 'user', content: query });
    pushChatHistory({ role: 'assistant', content: assistantReply });
  } catch (err) {
    finishChatStream();
    appendChatMessage('assistant', `*Failed to fetch response: ${err.message}*`);
  } finally {
    inputEl.disabled = false;
    inputEl.focus();
  }
}

function setActiveDrawer(name, drawerEl) {
  appState.activeDrawer = name;
  appState.lastFocusedElement = document.activeElement;
  document.body.classList.add('drawer-open');
  document.body.style.overflow = 'hidden';
  drawerEl.dataset.drawer = name;
}

function clearActiveDrawer(name) {
  if (appState.activeDrawer !== name) return;
  appState.activeDrawer = null;
  document.body.classList.remove('drawer-open');
  document.body.style.overflow = '';
  if (appState.lastFocusedElement instanceof HTMLElement) {
    appState.lastFocusedElement.focus();
  }
  appState.lastFocusedElement = null;
}

function trapDrawerFocus(event) {
  const drawerId = appState.activeDrawer === 'chat' ? 'chatDrawer' : 'geneDrawer';
  const drawer = document.getElementById(drawerId);
  if (!drawer) return;

  const focusable = Array.from(drawer.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )).filter((el) => !el.hasAttribute('disabled') && el.offsetParent !== null);

  if (!focusable.length) return;

  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  if (!drawer.contains(document.activeElement)) {
    event.preventDefault();
    first.focus();
    return;
  }

  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
    return;
  }

  if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
