import type { PipelineResult, SourceItem, ValidationRow } from '../types';
import { formatPval, formatTimestamp, normalizeResultShape } from './format';
import { renderMarkdownSafe } from './markdown';

// Import actual app CSS files so the export stays in sync automatically
import tokensRaw from '../styles/tokens.css?raw';
import baseRaw from '../styles/base.css?raw';
import surfacesRaw from '../styles/surfaces.css?raw';
import tabsRaw from '../styles/tabs.css?raw';
import tablesRaw from '../styles/tables.css?raw';
import resultsRaw from '../styles/results.css?raw';
import reportRaw from '../styles/report.css?raw';
import formsRaw from '../styles/forms.css?raw';
import genePillsRaw from '../styles/gene-pills.css?raw';
import graphRaw from '../styles/graph.css?raw';
import responsiveRaw from '../styles/responsive.css?raw';

// Export-only overrides: simulate the .main wrapper layout for standalone page
const EXPORT_OVERRIDES = `
  /* ---- Export-only layout ---- */
  .view {
    max-width: 1240px;
    margin: 0 auto;
    padding: 1.85rem 1.85rem 2.5rem 2.45rem;
    animation: none;
  }
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: var(--teal-600);
    box-shadow: 0 0 0 4px rgba(13, 148, 136, 0.12);
  }
  .result-action-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.55rem 0.72rem;
    border: 1px solid var(--gray-200);
    border-radius: var(--radius);
    background: var(--white);
    color: var(--gray-500);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    box-shadow: var(--shadow-xs);
  }
  /* In export, stat-icon uses text letters instead of SVG icons */
  .stat-card .stat-icon {
    font-size: 14px;
    font-weight: 800;
  }
  /* In export, source-icon uses text letters instead of SVG icons */
  .source-icon {
    font-size: 15px;
    font-weight: 800;
  }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  .network-summary {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  .network-card {
    padding: 1rem 1.1rem;
    background: var(--white);
    border: 1px solid var(--gray-200);
    border-radius: var(--radius);
  }
  .network-card .label {
    font-size: 10px;
    font-weight: 700;
    color: var(--gray-400);
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }
  .network-card .value {
    margin-top: 0.35rem;
    font-family: var(--font-mono);
    font-size: 1.2rem;
    color: var(--gray-900);
  }
  @media (max-width: 900px) {
    .network-summary { grid-template-columns: 1fr; }
  }
  @media (max-width: 720px) {
    .view { padding: 20px 12px 32px; }
  }
`;

const EXPORT_CSS = [
  tokensRaw,
  baseRaw,
  surfacesRaw,
  formsRaw,
  tabsRaw,
  tablesRaw,
  resultsRaw,
  reportRaw,
  genePillsRaw,
  graphRaw,
  responsiveRaw,
  EXPORT_OVERRIDES,
].join('\n');

const EXPORT_JS = `
  document.querySelectorAll('[data-tab-target]').forEach((button) => {
    button.addEventListener('click', () => {
      const target = button.getAttribute('data-tab-target');
      document.querySelectorAll('[data-tab-target]').forEach((el) => el.classList.remove('active'));
      document.querySelectorAll('[data-tab-panel]').forEach((el) => el.classList.remove('active'));
      button.classList.add('active');
      if (target) document.querySelector('[data-tab-panel="' + target + '"]')?.classList.add('active');
    });
  });

  document.querySelectorAll('[data-subtab-group]').forEach((group) => {
    group.querySelectorAll('[data-subtab-target]').forEach((button) => {
      button.addEventListener('click', () => {
        const target = button.getAttribute('data-subtab-target');
        const scope = button.closest('[data-subtab-scope]');
        if (!scope) return;
        scope.querySelectorAll('[data-subtab-target]').forEach((el) => el.classList.remove('active'));
        scope.querySelectorAll('[data-subtab-panel]').forEach((el) => el.classList.remove('active'));
        button.classList.add('active');
        if (target) scope.querySelector('[data-subtab-panel="' + target + '"]')?.classList.add('active');
      });
    });
  });
`;

function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'analysis';
}

function downloadFileName(result: PipelineResult): string {
  const disease = slugify(result.disease_context || 'analysis');
  const suffix = result.id ? `record-${result.id}` : String(Date.now());
  return `enrichRAG_${disease}_${suffix}.html`;
}

function normalizeGeneRows(result: PipelineResult): ValidationRow[] {
  return result.gene_validation?.rows || [];
}

function validationSummary(rows: ValidationRow[], result: PipelineResult) {
  const summary = result.gene_validation?.summary;
  if (summary) return summary;
  return {
    accepted: rows.filter((row) => row.status === 'accepted').length,
    remapped: rows.filter((row) => row.status === 'remapped').length,
    rejected: rows.filter((row) => row.status === 'rejected').length,
  };
}

function summarizeCounts(result: PipelineResult) {
  const enrichmentCount = Object.values(result.enrichment_results || {}).reduce(
    (sum, rows) => sum + rows.length,
    0,
  );
  return {
    genes: result.input_genes?.length || 0,
    enrichments: enrichmentCount,
    relations: result.gene_relations?.length || 0,
    sources: (result.sources?.web?.length || 0) + (result.sources?.pubmed?.length || 0),
  };
}

function renderEmpty(title: string, text: string): string {
  return `<div class="state-card"><h3>${escapeHtml(title)}</h3><p>${escapeHtml(text)}</p></div>`;
}

function renderTable(headers: string[], rows: string[][], rowClasses?: string[]): string {
  return `
    <div class="table-card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${rows.map((row, index) => `
              <tr${rowClasses?.[index] ? ` class="${rowClasses[index]}"` : ''}>
                ${row.map((cell) => cell).join('')}
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderPipelineTab(result: PipelineResult): string {
  const counts = summarizeCounts(result);
  return `
    <div class="tab-panel" data-tab-panel="pipeline">
      <div class="network-summary">
        <div class="network-card">
          <div class="label">Timestamp</div>
          <div class="value">${escapeHtml(formatTimestamp(result.timestamp) || 'N/A')}</div>
        </div>
        <div class="network-card">
          <div class="label">Record ID</div>
          <div class="value">${escapeHtml(result.id ?? 'N/A')}</div>
        </div>
        <div class="network-card">
          <div class="label">Normalized Genes</div>
          <div class="value">${escapeHtml(result.gene_validation?.normalized_genes?.length || counts.genes)}</div>
        </div>
        <div class="network-card">
          <div class="label">LLM Report</div>
          <div class="value">${result.llm_insight ? 'Ready' : 'Unavailable'}</div>
        </div>
      </div>
      ${renderEmpty('Pipeline Export', 'This static export preserves the final result layout and record data, but does not replay the live pipeline animation.')}
    </div>
  `;
}

function renderGenesTab(result: PipelineResult): string {
  const rows = normalizeGeneRows(result);
  if (!rows.length) {
    return `<div class="tab-panel" data-tab-panel="genes">${renderEmpty('No validation details', 'This result does not contain gene validation metadata.')}</div>`;
  }

  const summary = validationSummary(rows, result);
  const tableRows = rows.map((row) => [
    `<td class="cell-term">${escapeHtml(row.input_gene || '—')}</td>`,
    `<td>${row.normalized_gene ? `<span class="gene-pill">${escapeHtml(row.normalized_gene)}</span>` : escapeHtml(row.normalized_symbol || '—')}</td>`,
    `<td><span class="status-pill ${escapeHtml(row.status || '')}">${escapeHtml(row.status || '—')}</span></td>`,
    `<td>${escapeHtml(row.source || '—')}</td>`,
    `<td class="cell-overlap">${escapeHtml(row.gene_id || '—')}</td>`,
    `<td>${escapeHtml(row.official_name || row.description || '—')}</td>`,
  ]);

  return `
    <div class="tab-panel" data-tab-panel="genes">
      <div class="validation-panel">
        <div class="validation-head">
          <div>
            <h3>Gene Validation</h3>
            <p>Resolved symbols used by the analysis pipeline.</p>
          </div>
          <div class="validation-badges">
            <span class="validation-badge accepted">Accepted ${escapeHtml(summary.accepted)}</span>
            <span class="validation-badge remapped">Remapped ${escapeHtml(summary.remapped)}</span>
            <span class="validation-badge rejected">Rejected ${escapeHtml(summary.rejected)}</span>
          </div>
        </div>
        ${renderTable(['Input Gene', 'Normalized Gene', 'Status', 'Source', 'Gene ID', 'Official Name'], tableRows)}
      </div>
    </div>
  `;
}

function renderEnrichmentTab(result: PipelineResult): string {
  const datasets = Object.entries(result.enrichment_results || {});
  if (!datasets.length) {
    return `<div class="tab-panel" data-tab-panel="enrichment">${renderEmpty('No enrichment results', 'No significant terms are available in the selected databases.')}</div>`;
  }

  const labels: Record<string, string> = { GO: 'GO Biological Process', KEGG: 'KEGG Pathways' };
  const firstKey = datasets[0][0];

  return `
    <div class="tab-panel" data-tab-panel="enrichment">
      <div data-subtab-scope>
        <div class="sub-tabs" data-subtab-group>
          ${datasets.map(([key, rows], index) => `
            <button class="sub-tab-btn${index === 0 ? ' active' : ''}" data-subtab-target="enrichment-${escapeHtml(key)}">
              ${escapeHtml(labels[key] || key)} ${escapeHtml(rows.length)}
            </button>
          `).join('')}
        </div>
        ${datasets.map(([key, rows]) => {
          const rowClasses = rows.map((item) => {
            const pValue = Number((item as Record<string, unknown>).p_adjusted ?? (item as Record<string, unknown>).p_value ?? 1);
            if (pValue < 0.001) return 'sig-high';
            if (pValue < 0.01) return 'sig-mid';
            return '';
          });
          const tableRows = rows.map((item) => {
            const row = item as Record<string, unknown>;
            return [
              `<td class="cell-term">${escapeHtml(row.term ?? '—')}</td>`,
              `<td class="cell-overlap">${escapeHtml(row.overlap ?? '—')}</td>`,
              `<td class="cell-pval">${escapeHtml(formatPval(row.p_value))}</td>`,
              `<td class="cell-pval">${escapeHtml(formatPval(row.p_adjusted))}</td>`,
              `<td class="cell-genes">${String(row.genes ?? '').split(/[;,]\\s*/).filter(Boolean).map((gene) => `<span class="gene-pill">${escapeHtml(gene)}</span>`).join(' ') || '—'}</td>`,
            ];
          });
          return `
            <div class="sub-panel${key === firstKey ? ' active' : ''}" data-subtab-panel="enrichment-${escapeHtml(key)}">
              ${renderTable(['Term', 'Overlap', 'P-value', 'Adj. P-value', 'Genes'], tableRows, rowClasses)}
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
}

function renderSourceItem(source: SourceItem, kind: 'pubmed' | 'web'): string {
  const href = source.url || (source.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(String(source.pmid))}/` : '');
  const title = escapeHtml(source.title || 'Untitled');
  return `
    <div class="source-item">
      <div class="source-icon ${kind}">${kind === 'pubmed' ? 'P' : 'W'}</div>
      <div class="source-body">
        ${href ? `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${title}</a>` : `<div>${title}</div>`}
        <div class="source-meta">
          ${source.pmid ? `<span class="source-meta-badge">PMID:${escapeHtml(source.pmid)}</span>` : ''}
          ${source.journal ? `<span class="source-meta-text">${escapeHtml(source.journal)}</span>` : ''}
          ${source.pub_date ? `<span class="source-meta-text">${escapeHtml(source.pub_date)}</span>` : ''}
          ${Array.isArray(source.authors) && source.authors.length ? `<span class="source-meta-text">${escapeHtml(source.authors.join(', '))}</span>` : ''}
        </div>
        ${source.url ? `<div class="source-url">${escapeHtml(source.url)}</div>` : ''}
        <div class="source-snippet">${escapeHtml(source.abstract || source.content || source.snippet || '')}</div>
      </div>
    </div>
  `;
}

function renderSourcesTab(result: PipelineResult): string {
  const pubmed = result.sources?.pubmed || [];
  const web = result.sources?.web || [];
  if (!pubmed.length && !web.length) {
    return `<div class="tab-panel" data-tab-panel="sources">${renderEmpty('No sources', 'No evidence sources were captured for this analysis.')}</div>`;
  }

  const defaultTab = pubmed.length ? 'pubmed' : 'web';
  return `
    <div class="tab-panel" data-tab-panel="sources">
      <div data-subtab-scope>
        <div class="sub-tabs" data-subtab-group>
          <button class="sub-tab-btn${defaultTab === 'pubmed' ? ' active' : ''}" data-subtab-target="sources-pubmed">PubMed ${escapeHtml(pubmed.length)}</button>
          <button class="sub-tab-btn${defaultTab === 'web' ? ' active' : ''}" data-subtab-target="sources-web">Web ${escapeHtml(web.length)}</button>
        </div>
        <div class="sub-panel${defaultTab === 'pubmed' ? ' active' : ''}" data-subtab-panel="sources-pubmed">
          <div class="table-card">${pubmed.length ? pubmed.map((item) => renderSourceItem(item, 'pubmed')).join('') : renderEmpty('No PubMed sources', 'No PubMed evidence was captured.')}</div>
        </div>
        <div class="sub-panel${defaultTab === 'web' ? ' active' : ''}" data-subtab-panel="sources-web">
          <div class="table-card">${web.length ? web.map((item) => renderSourceItem(item, 'web')).join('') : renderEmpty('No web sources', 'No web evidence was captured.')}</div>
        </div>
      </div>
    </div>
  `;
}

function renderNetworkTab(result: PipelineResult, svgSnapshot?: string): string {
  const nodes = result.graph?.nodes?.length || 0;
  const edges = result.graph?.edges?.length || 0;

  if (svgSnapshot) {
    return `
      <div class="tab-panel" data-tab-panel="network">
        <div class="table-card network-tab-card">
          <div class="network-tab-controls">
            <div class="network-controls-header">
              <div class="graph-status-bar source-meta-badge">
                ${escapeHtml(nodes)} nodes · ${escapeHtml(edges)} edges
              </div>
            </div>
          </div>
          <div class="graph-canvas">${svgSnapshot}</div>
        </div>
      </div>
    `;
  }

  return `
    <div class="tab-panel" data-tab-panel="network">
      ${renderEmpty('No network data', 'The interactive graph was not available at export time. View this analysis in enrichRAG to see the network visualization.')}
    </div>
  `;
}

function renderReportTab(result: PipelineResult): string {
  if (!result.llm_insight) {
    return `<div class="tab-panel active" data-tab-panel="report">${renderEmpty('No report', 'The report will appear after enrichment and evidence retrieval complete.')}</div>`;
  }
  return `
    <div class="tab-panel active" data-tab-panel="report">
      <div class="report-shell">
        <div class="report-banner">
          <div>Context: <b>${escapeHtml(result.disease_context || 'Analysis')}</b></div>
          <div><b>${escapeHtml(formatTimestamp(result.timestamp) || 'No timestamp')}</b></div>
        </div>
        <div class="report-content">${renderMarkdownSafe(result.llm_insight || '')}</div>
      </div>
    </div>
  `;
}

function buildTabButtons(result: PipelineResult): string {
  const counts = summarizeCounts(result);
  const geneRows = normalizeGeneRows(result);
  const graphNodes = result.graph?.nodes?.length || 0;
  const tabs = [
    { id: 'pipeline', label: 'Pipeline', count: '' },
    { id: 'genes', label: 'Genes', count: String(geneRows.length || counts.genes) },
    { id: 'enrichment', label: 'Enrichment', count: String(counts.enrichments) },
    { id: 'sources', label: 'Sources', count: String(counts.sources) },
    { id: 'network', label: 'Network', count: String(graphNodes) },
    { id: 'report', label: 'Insight Report', count: '' },
  ];
  return tabs.map((tab) => `
    <button class="tab-btn${tab.id === 'report' ? ' active' : ''}" data-tab-target="${tab.id}">
      ${escapeHtml(tab.label)}
      ${tab.count ? `<span class="tab-count">${escapeHtml(tab.count)}</span>` : ''}
    </button>
  `).join('');
}

/** Capture the live SVG from the network graph in the DOM, if present. */
export function captureNetworkSvg(): string | undefined {
  const svg = document.querySelector('.graph-canvas svg') as SVGSVGElement | null;
  if (!svg) return undefined;
  // Clone so we don't mutate the live DOM
  const clone = svg.cloneNode(true) as SVGSVGElement;
  // Ensure the SVG has explicit dimensions for the static export
  if (!clone.getAttribute('xmlns')) {
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  }
  return clone.outerHTML;
}

export function buildResultHtml(input: PipelineResult, svgSnapshot?: string): string {
  const result = normalizeResultShape(input);
  if (!result) return '';

  const counts = summarizeCounts(result);

  return `
    <!DOCTYPE html>
    <html lang="zh-Hant">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>${escapeHtml(result.disease_context || 'Analysis')} | enrichRAG export</title>
        <style>${EXPORT_CSS}</style>
      </head>
      <body>
        <div class="view active">
          <div class="results-header">
            <div class="status-badge"><span class="status-dot"></span> Analysis Complete</div>
            <div class="title-row">
              <div>
                <p class="results-context-label">Disease Context</p>
                <h2>${escapeHtml(result.disease_context || 'Analysis')}</h2>
                <p class="meta">Targeting <b>${escapeHtml(result.input_genes?.length || 0)}</b> genes</p>
              </div>
              <div class="results-actions">
                <span class="result-action-chip">Record ${escapeHtml(result.id ?? 'N/A')}</span>
                <span class="result-action-chip">${escapeHtml(downloadFileName(result))}</span>
              </div>
            </div>
          </div>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon teal">G</div>
              <div class="stat-number">${escapeHtml(counts.genes)}</div>
              <div class="stat-label">Input Genes</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon blue">E</div>
              <div class="stat-number">${escapeHtml(counts.enrichments)}</div>
              <div class="stat-label">Enriched Terms</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon amber">R</div>
              <div class="stat-number">${escapeHtml(counts.relations)}</div>
              <div class="stat-label">Relations</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon green">S</div>
              <div class="stat-number">${escapeHtml(counts.sources)}</div>
              <div class="stat-label">Sources</div>
            </div>
          </div>

          <div class="tabs-wrapper">
            <div class="tabs">${buildTabButtons(result)}</div>
          </div>

          ${renderPipelineTab(result)}
          ${renderGenesTab(result)}
          ${renderEnrichmentTab(result)}
          ${renderSourcesTab(result)}
          ${renderNetworkTab(result, svgSnapshot)}
          ${renderReportTab(result)}
        </div>
        <script>${EXPORT_JS}</script>
      </body>
    </html>
  `;
}

export function downloadResultHtml(input: PipelineResult): string {
  const result = normalizeResultShape(input);
  if (!result) throw new Error('No result available');

  const svgSnapshot = captureNetworkSvg();
  const filename = downloadFileName(result);
  const blob = new Blob([buildResultHtml(result, svgSnapshot)], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  return filename;
}
