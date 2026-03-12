/* enrichRAG — Frontend Application
   API_PREFIX is injected by the server via inline script in index.html */

const API_PREFIX = window.__API_PREFIX || '';
const MAX_HISTORY = 20;
let currentResult = null;
let currentView = 'input';
let _eventSource = null;
let _pipelineRunning = false;
let currentValidation = null;

document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  renderHistory();
  ['genes', 'disease', 'pval'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', resetValidationUI);
  });
});

/* ---- Navigation ---- */

function switchView(name) {
  if (name === 'results' && !currentResult && !_pipelineRunning) return;
  if (name === 'results' && currentResult) {
    renderResultTabs(currentResult);
  }
  currentView = name;
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
  currentValidation = null;
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
    const response = await fetch(API_PREFIX + '/api/genes/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ genes }),
    });
    if (!response.ok) throw new Error('Validation failed');
    currentValidation = await response.json();
    renderValidationSummary(currentValidation);
    renderValidationResultsPreview(currentValidation, disease);
    document.getElementById('navResults').disabled = false;
    runBtn.disabled = !currentValidation.normalized_genes.length;
    showToast(`Validated ${currentValidation.summary.total} genes`);
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
  currentResult = {
    input_genes: validationData.normalized_genes || [],
    disease_context: disease || 'Analysis',
    enrichment_results: {},
    llm_insight: '',
    sources: { web: [], pubmed: [] },
    gene_relations: [],
    graph: { nodes: [], edges: [] },
    gene_validation: validationData,
  };
  document.getElementById('statusBadge').innerHTML = '<i data-lucide="badge-check"></i> Validation Ready';
  document.getElementById('navResults').disabled = false;
}

async function openGeneDrawer(symbol) {
  const drawer = document.getElementById('geneDrawer');
  const backdrop = document.getElementById('drawerBackdrop');
  const title = document.getElementById('drawerTitle');
  const body = document.getElementById('drawerBody');
  title.textContent = symbol;
  body.innerHTML = '<div class="no-data waiting-hint"><i data-lucide="loader-2" class="spin-icon"></i> Loading gene profile...</div>';
  drawer.classList.add('open');
  backdrop.classList.add('open');
  drawer.setAttribute('aria-hidden', 'false');
  lucide.createIcons();

  try {
    const response = await fetch(API_PREFIX + '/api/genes/' + encodeURIComponent(symbol));
    if (!response.ok) throw new Error('Profile not found');
    const data = await response.json();
    title.textContent = data.canonical_symbol || symbol;
    body.innerHTML = renderGeneDrawer(data);
  } catch (err) {
    console.error(err);
    body.innerHTML = '<div class="no-data">Gene profile not found.</div>';
  }
  lucide.createIcons();
}

function closeGeneDrawer() {
  const drawer = document.getElementById('geneDrawer');
  const backdrop = document.getElementById('drawerBackdrop');
  drawer.classList.remove('open');
  backdrop.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
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

  if (data.sources) {
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
  const genes = currentValidation && currentValidation.normalized_genes.length
    ? currentValidation.normalized_genes.join(' ')
    : document.getElementById('genes').value.trim();
  const disease = document.getElementById('disease').value.trim();
  const pval = document.getElementById('pval').value;
  if (!genes) return;
  if (!currentValidation || !currentValidation.normalized_genes.length) {
    showToast('Validate genes before running the pipeline');
    return;
  }

  _pipelineRunning = true;
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
    `<div class="tab-panel" id="panel-genes"><div class="no-data waiting-hint"><i data-lucide="loader-2" class="spin-icon"></i> Waiting for validation details...</div></div>` +
    `<div class="tab-panel" id="panel-enrichment"><div class="no-data waiting-hint"><i data-lucide="loader-2" class="spin-icon"></i> Waiting for pipeline...</div></div>` +
    `<div class="tab-panel" id="panel-sources"><div class="no-data waiting-hint"><i data-lucide="loader-2" class="spin-icon"></i> Waiting for pipeline...</div></div>` +
    `<div class="tab-panel" id="panel-network"><div class="no-data waiting-hint"><i data-lucide="loader-2" class="spin-icon"></i> Waiting for pipeline...</div></div>` +
    `<div class="tab-panel" id="panel-report"><div class="no-data waiting-hint"><i data-lucide="loader-2" class="spin-icon"></i> Waiting for pipeline...</div></div>`;

  document.getElementById('navResults').disabled = false;
  switchView('results');
  lucide.createIcons();

  // Reset pipeline node states
  resetPipeline();

  const params = new URLSearchParams({ genes, disease, pval });
  const es = new EventSource(API_PREFIX + '/api/analyze/stream?' + params);
  _eventSource = es;

  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.event === 'result') {
      es.close();
      _eventSource = null;
      _pipelineRunning = false;
      if (currentValidation) {
        msg.data.gene_validation = currentValidation;
      }
      currentResult = msg.data;
      finishPipeline(msg.data, false);
    } else if (msg.event === 'error') {
      es.close();
      _eventSource = null;
      _pipelineRunning = false;
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
    _eventSource = null;
    _pipelineRunning = false;
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
  if (_eventSource) {
    _eventSource.close();
    _eventSource = null;
  }
  _pipelineRunning = false;
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

  currentResult = data;
  renderResultTabs(data);
  saveHistory(data);
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
  const totalSources = webSources.length + pubmedSources.length;
  const relationsCount = (data.gene_relations || []).length;
  const graphData = data.graph || { nodes: [], edges: [] };
  const geneValidation = data.gene_validation || currentValidation || {
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
      panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">${enrichKeys.length ? subTabsHtml + subPanelsHtml : '<div class="no-data">No enrichment results.</div>'}</div>`;

    } else if (tab.key === 'network') {
      panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">
        <div class="table-card" style="padding:0;position:relative">
          <div id="networkGraph" style="width:100%;height:520px;overflow:hidden"></div>
        </div>
      </div>`;

    } else if (tab.key === 'sources') {
      let subTabsHtml = '<div class="sub-tabs">';
      let subPanelsHtml = '';
      subTabsHtml += `<button class="sub-tab-btn active" data-subtab="src-pubmed" onclick="switchSubTab('sources','src-pubmed')">PubMed ${pubmedSources.length}</button>`;
      subPanelsHtml += `<div class="sub-panel active" id="subpanel-src-pubmed"><div class="table-card"><div class="sources-list">${renderPubmedSources(pubmedSources)}</div></div></div>`;
      subTabsHtml += `<button class="sub-tab-btn" data-subtab="src-web" onclick="switchSubTab('sources','src-web')">Web ${webSources.length}</button>`;
      subPanelsHtml += `<div class="sub-panel" id="subpanel-src-web"><div class="table-card"><div class="sources-list">${renderWebSources(webSources)}</div></div></div>`;
      subTabsHtml += '</div>';
      panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">${subTabsHtml}${subPanelsHtml}</div>`;

    } else if (tab.key === 'report') {
      const ts = data.timestamp ? new Date(data.timestamp).toLocaleString() : new Date().toLocaleString();
      panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">
        <div class="table-card">
          <div class="report-banner">
            <div class="banner-item"><i data-lucide="flask-conical"></i> Context: <b>&nbsp;${esc(data.disease_context)}</b></div>
            <div class="banner-item"><i data-lucide="clock"></i> <b>&nbsp;${ts}</b></div>
          </div>
          <div class="report-content">${marked.parse(data.llm_insight || '_No report generated._')}</div>
        </div>
      </div>`;
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
    return '<div class="no-data">No gene validation details available.</div>';
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
      <div class="table-card" style="border:none;border-radius:0;box-shadow:none;">
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
  if (!sources.length) return '<div class="no-data">No web search results.</div>';
  return sources.map(s =>
    `<div class="source-item">
      <div class="source-icon web"><i data-lucide="globe"></i></div>
      <div class="source-body">
        <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title || 'Untitled')}</a>
        <div class="source-url">${esc(s.url)}</div>
        <div class="source-snippet">${esc(s.content || '')}</div>
      </div>
    </div>`
  ).join('');
}

function renderPubmedSources(sources) {
  if (!sources.length) return '<div class="no-data">No PubMed results.</div>';
  return sources.map(s => {
    const metaParts = [];
    if (s.pmid) metaParts.push(`<span class="source-meta-badge">PMID:${esc(s.pmid)}</span>`);
    if (s.journal) metaParts.push(`<span class="source-meta-text">${esc(s.journal)}</span>`);
    if (s.pub_date) metaParts.push(`<span class="source-meta-text">${esc(s.pub_date)}</span>`);
    if (s.authors) metaParts.push(`<span class="source-meta-text">${esc(s.authors)}</span>`);
    return `<div class="source-item">
      <div class="source-icon pubmed"><i data-lucide="graduation-cap"></i></div>
      <div class="source-body">
        <a href="https://pubmed.ncbi.nlm.nih.gov/${esc(s.pmid)}/" target="_blank" rel="noopener">${esc(s.title || 'Untitled')}</a>
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
  if (!rows.length) return '<div class="no-data">No significant results found.</div>';
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
  if (!currentResult) return;
  const blob = new Blob([JSON.stringify(currentResult, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `enrichRAG_${currentResult.disease_context || 'result'}_${Date.now()}.json`;
  a.click();
  showToast('JSON downloaded');
}

function copyReport() {
  if (!currentResult) return;
  navigator.clipboard.writeText(currentResult.llm_insight || '').then(() => showToast('Report copied'));
}

/* ---- History ---- */

function getHistory() { return JSON.parse(localStorage.getItem('enrichrag_history_v2') || '[]'); }

function saveHistory(data) {
  const hist = getHistory();
  hist.unshift({ ts: new Date().toISOString(), input_genes: data.input_genes, disease_context: data.disease_context, data });
  if (hist.length > MAX_HISTORY) hist.length = MAX_HISTORY;
  localStorage.setItem('enrichrag_history_v2', JSON.stringify(hist));
  renderHistory();
}

function renderHistory() {
  const hist = getHistory();
  document.getElementById('historyBadge').textContent = hist.length;
  if (!hist.length) {
    document.getElementById('historyCard').innerHTML = `
      <div class="empty-state">
        <div class="empty-icon"><i data-lucide="clock"></i></div>
        <h3>No analyses yet</h3>
        <p>Run your first enrichment analysis to see results here.</p>
      </div>`;
    lucide.createIcons();
    return;
  }
  let html = '<ul class="history-list">';
  hist.forEach((h, i) => {
    const genes = h.input_genes || h.data?.input_genes || [];
    const disease = h.disease_context || h.data?.disease_context || '';
    const time = new Date(h.ts).toLocaleString();
    html += `<li><button onclick="loadHistory(${i})">
      <div class="hist-info">
        <div class="hist-title">
          <span class="hist-disease">${esc(disease)}</span>
          <span class="hist-gene-badge">${genes.length} genes</span>
        </div>
        <div class="hist-genes">${esc(genes.join(', '))}</div>
      </div>
      <span class="hist-time">${time} <i data-lucide="chevron-right"></i></span>
    </button></li>`;
  });
  html += '</ul>';
  document.getElementById('historyCard').innerHTML = html;
  lucide.createIcons();
}

function loadHistory(idx) {
  const hist = getHistory();
  if (!hist[idx]) return;
  currentResult = hist[idx].data;
  document.getElementById('genes').value = (currentResult.input_genes || []).join(', ');
  document.getElementById('disease').value = currentResult.disease_context || '';
  document.getElementById('navResults').disabled = false;
  renderResult(currentResult);
  switchView('results');
  showToast('History loaded');
}

/* ---- Utilities ---- */

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function escAttr(s) {
  return String(s).replace(/&/g, '&amp;').replace(/'/g, '&#39;').replace(/"/g, '&quot;');
}
