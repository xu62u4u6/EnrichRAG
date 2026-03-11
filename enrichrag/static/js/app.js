/* enrichRAG — Frontend Application
   API_PREFIX is injected by the server via inline script in index.html */

const API_PREFIX = window.__API_PREFIX || '';
const MAX_HISTORY = 20;
let currentResult = null;
let currentView = 'input';

document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  renderHistory();
});

/* ---- Navigation ---- */

function switchView(name) {
  if (name === 'results' && !currentResult) return;
  currentView = name;
  document.querySelectorAll('.view, .loading-view').forEach(v => v.classList.remove('active'));
  const el = document.getElementById('view-' + name);
  if (el) el.classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.view === name);
  });
  // Close mobile nav
  const nav = document.querySelector('.sidebar nav');
  if (nav) nav.classList.remove('open');
  lucide.createIcons();
}

function showToast(msg, ms = 2500) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), ms);
}

/* ---- Pipeline State ---- */

function setPipelineState(nodeId, status) {
  const el = document.getElementById('node-' + nodeId);
  if (el) {
    el.dataset.status = status;
    const circle = el.querySelector('.node-circle');
    if (status === 'done') {
      circle.innerHTML = '<i data-lucide="check" style="width:18px;height:18px"></i>';
    } else if (status === 'active') {
      circle.innerHTML = '<i data-lucide="loader-2" style="width:18px;height:18px"></i>';
    }
    lucide.createIcons();
  }
}

function setLineState(lineId, status) {
  const el = document.getElementById(lineId);
  if (el) { el.className = 'pipe-line ' + status; }
}

const _nodeTimers = {};
const NODE_TIMEOUT_MS = 120000;

function resetPipeline() {
  ['enrichment','search','pubmed','extraction','llm','done'].forEach(n => {
    const el = document.getElementById('node-' + n);
    if (el) {
      el.dataset.status = 'pending';
      const timer = el.querySelector('.node-timer');
      if (timer) timer.textContent = '';
    }
    if (_nodeTimers[n]) { clearInterval(_nodeTimers[n].interval); delete _nodeTimers[n]; }
  });
  document.querySelectorAll('.pipe-line').forEach(l => l.className = 'pipe-line pending');
}

function startNodeTimer(name) {
  if (_nodeTimers[name]) return;
  const el = document.getElementById('node-' + name);
  const timerEl = el ? el.querySelector('.node-timer') : null;
  if (!timerEl) return;
  const start = Date.now();
  timerEl.textContent = '0.0s';
  _nodeTimers[name] = {
    start,
    interval: setInterval(() => {
      const elapsed = Date.now() - start;
      timerEl.textContent = (elapsed / 1000).toFixed(1) + 's';
      if (elapsed >= NODE_TIMEOUT_MS && el.dataset.status === 'active') {
        el.dataset.status = 'timeout';
        timerEl.textContent = 'timeout';
        clearInterval(_nodeTimers[name].interval);
      }
    }, 100),
  };
}

function stopNodeTimer(name) {
  if (!_nodeTimers[name]) return;
  clearInterval(_nodeTimers[name].interval);
  const elapsed = Date.now() - _nodeTimers[name].start;
  const el = document.getElementById('node-' + name);
  const timerEl = el ? el.querySelector('.node-timer') : null;
  if (timerEl) timerEl.textContent = (elapsed / 1000).toFixed(1) + 's';
  delete _nodeTimers[name];
}

function failNodeTimer(name) {
  if (_nodeTimers[name]) clearInterval(_nodeTimers[name].interval);
  const el = document.getElementById('node-' + name);
  if (el) el.dataset.status = 'failed';
  const timerEl = el ? el.querySelector('.node-timer') : null;
  if (timerEl && _nodeTimers[name]) {
    const elapsed = Date.now() - _nodeTimers[name].start;
    timerEl.textContent = (elapsed / 1000).toFixed(1) + 's — failed';
  } else if (timerEl) {
    timerEl.textContent = 'failed';
  }
  if (_nodeTimers[name]) delete _nodeTimers[name];
}

function updatePipelineFromEvent(step, message) {
  document.getElementById('loadingMsg').textContent = message;
  const isFail = /fail|error/i.test(message);

  if (step === 'enrichment' && message.includes('Running')) {
    setPipelineState('enrichment', 'active');
    startNodeTimer('enrichment');
  } else if (step === 'enrichment' && message.includes('complete')) {
    setPipelineState('enrichment', 'done');
    stopNodeTimer('enrichment');
    setLineState('line-1-2a', 'active');
    setLineState('line-1-2b', 'active');
  } else if (step === 'enrichment' && isFail) {
    failNodeTimer('enrichment');
  } else if (step === 'search' && (message.includes('Searching') || message.includes('Skipping web'))) {
    if (message.includes('Skipping')) {
      setPipelineState('search', 'done');
    } else {
      setPipelineState('search', 'active');
      startNodeTimer('search');
    }
    setPipelineState('pubmed', 'active');
    startNodeTimer('pubmed');
  } else if (step === 'search' && message.includes('Found')) {
    setPipelineState('search', 'done');
    stopNodeTimer('search');
  } else if (step === 'search' && isFail) {
    failNodeTimer('search');
  } else if (step === 'pubmed' && message.includes('Fetching')) {
    setPipelineState('pubmed', 'active');
    startNodeTimer('pubmed');
  } else if (step === 'pubmed' && (message.includes('Fetched') || message.includes('Skipping'))) {
    setPipelineState('pubmed', 'done');
    stopNodeTimer('pubmed');
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
  } else if (step === 'extraction' && message.includes('Extracting')) {
    setPipelineState('extraction', 'active');
    startNodeTimer('extraction');
    setLineState('line-2a-3', 'done');
    setLineState('line-2b-3', 'done');
  } else if (step === 'extraction' && (message.includes('Extracted') || message.includes('Skipping'))) {
    setPipelineState('extraction', 'done');
    stopNodeTimer('extraction');
    setLineState('line-3-4', 'active');
  } else if (step === 'extraction' && isFail) {
    failNodeTimer('extraction');
    setLineState('line-3-4', 'active');
  } else if (step === 'llm' && message.includes('Generating')) {
    setPipelineState('extraction', 'done');
    stopNodeTimer('extraction');
    setLineState('line-3-4', 'done');
    setPipelineState('llm', 'active');
    startNodeTimer('llm');
  } else if (step === 'llm' && (message.includes('generated') || message.includes('Skipping'))) {
    setPipelineState('llm', 'done');
    stopNodeTimer('llm');
    setLineState('line-4-5', 'active');
  } else if (step === 'llm' && isFail) {
    failNodeTimer('llm');
    setLineState('line-4-5', 'active');
  } else if (step === 'done') {
    setPipelineState('done', 'done');
    stopNodeTimer('done');
    setLineState('line-4-5', 'done');
  }
}

/* ---- Analysis ---- */

function runAnalysis() {
  const genes = document.getElementById('genes').value.trim();
  const disease = document.getElementById('disease').value.trim();
  const pval = document.getElementById('pval').value;
  if (!genes) return;

  resetPipeline();
  switchView('loading');
  lucide.createIcons();
  document.getElementById('loadingMsg').textContent = 'Initializing...';
  document.getElementById('runBtn').disabled = true;

  const params = new URLSearchParams({ genes, disease, pval });
  const es = new EventSource(API_PREFIX + '/api/analyze/stream?' + params);

  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.event === 'result') {
      es.close();
      currentResult = msg.data;
      renderResult(msg.data);
      saveHistory(msg.data);
      document.getElementById('runBtn').disabled = false;
      document.getElementById('navResults').disabled = false;
      switchView('results');
    } else if (msg.event === 'error') {
      es.close();
      document.getElementById('runBtn').disabled = false;
      document.getElementById('loadingMsg').textContent = msg.message;
      setTimeout(() => switchView('input'), 2000);
    } else {
      updatePipelineFromEvent(msg.event, msg.message);
    }
  };

  es.onerror = () => {
    es.close();
    document.getElementById('runBtn').disabled = false;
    document.getElementById('loadingMsg').textContent = 'Connection lost.';
    setTimeout(() => switchView('input'), 2000);
  };
}

/* ---- Render Results ---- */

function renderResult(data) {
  const er = data.enrichment_results || {};
  const sources = data.sources || {};
  const webSources = sources.web || data.web_sources || [];
  const pubmedSources = sources.pubmed || [];

  // Header
  document.getElementById('resultsTitle').textContent = data.disease_context || 'Analysis';
  document.getElementById('resultsMeta').innerHTML =
    `Targeting <b>${data.input_genes.length}</b> genes`;

  // Stats grid
  const goCount = (er.GO || []).length;
  const keggCount = (er.KEGG || []).length;
  const totalSources = webSources.length + pubmedSources.length;
  const relationsCount = (data.gene_relations || []).length;
  const graphData = data.graph || { nodes: [], edges: [] };
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

  // Main tabs
  const mainTabs = [
    { key: 'enrichment', label: 'Enrichment', icon: 'bar-chart-3', count: goCount + keggCount },
    { key: 'network', label: 'Network', icon: 'share-2', count: graphData.nodes.length },
    { key: 'sources', label: 'Sources', icon: 'book-open', count: totalSources },
    { key: 'report', label: 'Insight Report', icon: 'file-text', count: null },
  ];

  let tabsHtml = '';
  let panelsHtml = '';

  mainTabs.forEach((tab, i) => {
    const active = i === 0 ? ' active' : '';
    const countHtml = tab.count !== null ? `<span class="tab-count">${tab.count}</span>` : '';
    tabsHtml += `<button class="tab-btn${active}" data-tab="${tab.key}" onclick="switchTab('${tab.key}')"><i data-lucide="${tab.icon}"></i> ${tab.label} ${countHtml}</button>`;

    if (tab.key === 'enrichment') {
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
      panelsHtml += `<div class="tab-panel${active}" id="panel-${tab.key}">${subTabsHtml}${subPanelsHtml}</div>`;

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

  // Store graph data for lazy rendering when Network tab is shown
  window._graphData = graphData;
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

  // Zoom & pan
  const g = svg.append('g');
  const zoom = d3.zoom()
    .scaleExtent([0.3, 5])
    .on('zoom', (event) => { g.attr('transform', event.transform); });
  svg.call(zoom);

  // Defs for arrow markers
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

  // Color and size by type
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

  // Edges
  const link = g.append('g')
    .selectAll('line').data(edges).join('line')
    .attr('stroke', d => d.type === 'relation' ? '#98a2b3' : '#e4e7ec')
    .attr('stroke-width', d => d.type === 'relation' ? 1.2 : 0.8)
    .attr('stroke-dasharray', d => d.type === 'enrichment' ? '3,3' : 'none')
    .attr('marker-end', d => d.type === 'relation' ? 'url(#arrow-relation)' : '');

  // Nodes
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

  // Hover interaction
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

  // Tooltip on click
  node.on('click', function(e, d) {
    const rels = (graphData.edges || []).filter(
      edge => edge.type === 'relation' && (edge.source === d.id || edge.target === d.id ||
        (edge.source.id || edge.source) === d.id || (edge.target.id || edge.target) === d.id)
    );
    if (rels.length > 0) {
      const info = rels.map(r => `${r.source.label || r.source} → ${r.target.label || r.target} [${r.relation}]`).join('\n');
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
  // Lazy-render D3 graph when Network tab is first shown
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
