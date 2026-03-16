<template>
  <div class="view active" id="view-results">
    <div class="results-header">
      <div class="status-badge">
        <template v-if="analysis.running"><Loader2 :size="13" class="spin" /> Running...</template>
        <template v-else-if="analysis.status === 'error'"><AlertCircle :size="13" /> Error</template>
        <template v-else><CheckCircle2 :size="13" /> Analysis Complete</template>
      </div>
      <div class="title-row">
        <div>
          <h2>{{ analysis.result?.disease_context || 'No analysis loaded' }}</h2>
          <p class="meta">Targeting <b>{{ analysis.result?.input_genes?.length || 0 }}</b> genes</p>
        </div>
        <div class="results-actions">
          <button v-if="analysis.running" class="btn btn-danger" @click="analysis.cancelRun()"><Square :size="14" /> Stop</button>
          <button class="btn btn-secondary" :disabled="!analysis.result" @click="chat.open = true"><MessageSquare :size="14" /> Ask Assistant</button>
          <button class="btn btn-secondary" :disabled="!analysis.result" @click="copyReport"><Clipboard :size="14" /> Copy</button>
          <button class="btn btn-secondary" :disabled="!analysis.result" @click="downloadJson"><Download :size="14" /> JSON</button>
        </div>
      </div>
    </div>

    <div v-if="!analysis.result" class="empty-state">
      Run an analysis or load one from history to populate results.
    </div>

    <template v-else>
      <!-- Stats Grid with icons -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon teal"><Dna :size="14" /></div>
          <div class="stat-number">{{ analysis.result.input_genes?.length || 0 }}</div>
          <div class="stat-label">Input Genes</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon blue"><GitBranch :size="14" /></div>
          <div class="stat-number">{{ enrichedTermCount }}</div>
          <div class="stat-label">Enriched Terms</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon amber"><ScanSearch :size="14" /></div>
          <div class="stat-number">{{ relations.length }}</div>
          <div class="stat-label">Relations</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon green"><BookOpen :size="14" /></div>
          <div class="stat-number">{{ totalSources }}</div>
          <div class="stat-label">Sources</div>
        </div>
      </div>

      <!-- Tabs — same order as original -->
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <component :is="tab.icon" :size="15" />
          {{ tab.label }}
          <span v-if="tab.count != null" class="tab-count">{{ tab.count }}</span>
        </button>
      </div>

      <!-- Pipeline tab -->
      <PipelineViz v-if="activeTab === 'pipeline'" />

      <!-- Genes tab -->
      <div v-if="activeTab === 'genes'">
        <div v-if="!geneRows.length" class="state-card state-card-compact">
          <h3>No validation details</h3>
          <p>This result does not contain gene validation metadata.</p>
        </div>
        <div v-else class="validation-panel">
          <div class="validation-head">
            <div>
              <h3>Gene Validation</h3>
              <p>Resolved symbols used by the analysis pipeline.</p>
            </div>
            <div class="validation-badges">
              <span class="validation-badge accepted">Accepted {{ geneValidation.summary?.accepted || countByStatus('accepted') }}</span>
              <span class="validation-badge remapped">Remapped {{ geneValidation.summary?.remapped || countByStatus('remapped') }}</span>
              <span class="validation-badge rejected">Rejected {{ geneValidation.summary?.rejected || countByStatus('rejected') }}</span>
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
                <tbody>
                  <tr v-for="row in geneRows" :key="`${row.input_gene}-${row.status}`">
                    <td class="cell-term">{{ row.input_gene }}</td>
                    <td>
                      <button v-if="row.normalized_gene" class="validation-gene-btn" @click="openGene(row.normalized_gene)">{{ row.normalized_gene }}</button>
                      <span v-else>{{ row.normalized_symbol || '—' }}</span>
                    </td>
                    <td><span class="status-pill" :class="row.status">{{ row.status }}</span></td>
                    <td>{{ row.source || '—' }}</td>
                    <td class="cell-overlap">{{ row.gene_id || '—' }}</td>
                    <td>{{ row.official_name || row.description || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- Enrichment tab with sub-tabs -->
      <div v-if="activeTab === 'enrichment'">
        <div v-if="!enrichmentKeys.length" class="table-card">
          <div class="state-card state-card-compact">
            <h3>No enrichment results</h3>
            <p>No significant terms are available in the selected databases.</p>
          </div>
        </div>
        <template v-else>
          <div class="sub-tabs">
            <button
              v-for="(key, i) in enrichmentKeys"
              :key="key"
              class="sub-tab-btn"
              :class="{ active: activeEnrichSub === key }"
              @click="activeEnrichSub = key"
            >
              {{ enrichSubLabel(key) }} {{ (analysis.result.enrichment_results![key] || []).length }}
            </button>
          </div>
          <div v-for="key in enrichmentKeys" :key="key" class="sub-panel" :class="{ active: activeEnrichSub === key }">
            <div class="table-card">
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Term</th>
                      <th>Overlap</th>
                      <th>P-value</th>
                      <th>Adj. P-value</th>
                      <th>Genes</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(row, idx) in (analysis.result.enrichment_results![key] || [])"
                      :key="idx"
                      :class="sigClass(row as any)"
                    >
                      <td class="cell-term">{{ (row as any).term }}</td>
                      <td class="cell-overlap">{{ (row as any).overlap }}</td>
                      <td class="cell-pval">{{ formatPval((row as any).p_value) }}</td>
                      <td class="cell-pval">{{ formatPval((row as any).p_adjusted) }}</td>
                      <td class="cell-genes">
                        <template v-if="typeof (row as any).genes === 'string'">
                          <span v-for="g in (row as any).genes.split(/[;,]\s*/)" :key="g" class="gene-pill">{{ g.trim() }}</span>
                        </template>
                        <template v-else>{{ (row as any).genes }}</template>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Sources tab with sub-tabs -->
      <div v-if="activeTab === 'sources'">
        <div v-if="!totalSources" class="table-card">
          <div class="state-card state-card-compact">
            <h3>No sources</h3>
            <p>No evidence sources were captured for this analysis.</p>
          </div>
        </div>
        <template v-else>
          <div class="sub-tabs">
            <button class="sub-tab-btn" :class="{ active: activeSourceSub === 'pubmed' }" @click="activeSourceSub = 'pubmed'">PubMed {{ pubmedSources.length }}</button>
            <button class="sub-tab-btn" :class="{ active: activeSourceSub === 'web' }" @click="activeSourceSub = 'web'">Web {{ webSources.length }}</button>
          </div>
          <!-- PubMed sub-panel -->
          <div class="sub-panel" :class="{ active: activeSourceSub === 'pubmed' }">
            <div class="table-card">
              <div class="sources-list">
                <div v-for="s in pubmedSources" :key="s.pmid || s.title" class="source-item">
                  <div class="source-icon pubmed"><GraduationCap :size="15" /></div>
                  <div class="source-body">
                    <a :href="s.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${s.pmid}/` : '#'" target="_blank" rel="noopener noreferrer">{{ s.title || 'Untitled' }}</a>
                    <div class="source-meta">
                      <span v-if="s.pmid" class="source-meta-badge">PMID:{{ s.pmid }}</span>
                      <span v-if="s.journal" class="source-meta-text">{{ s.journal }}</span>
                      <span v-if="s.pub_date" class="source-meta-text">{{ s.pub_date }}</span>
                      <span v-if="s.authors" class="source-meta-text">{{ s.authors }}</span>
                    </div>
                    <div class="source-snippet">{{ s.abstract || '' }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <!-- Web sub-panel -->
          <div class="sub-panel" :class="{ active: activeSourceSub === 'web' }">
            <div class="table-card">
              <div class="sources-list">
                <div v-for="s in webSources" :key="s.url || s.title" class="source-item">
                  <div class="source-icon web"><Globe :size="15" /></div>
                  <div class="source-body">
                    <a v-if="s.url" :href="s.url" target="_blank" rel="noopener noreferrer">{{ s.title || 'Untitled' }}</a>
                    <div v-else>{{ s.title || 'Untitled' }}</div>
                    <div class="source-url">{{ s.url || '' }}</div>
                    <div class="source-snippet">{{ s.content || s.snippet || '' }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Network tab -->
      <div v-if="activeTab === 'network'" class="table-card" style="padding: 0; position: relative">
        <div v-if="!(analysis.result.graph?.nodes?.length)" class="state-card state-card-compact">
          <h3>No network data</h3>
          <p>The relation network is generated after extraction completes.</p>
        </div>
        <NetworkGraph v-else :nodes="analysis.result.graph.nodes" :edges="analysis.result.graph.edges || []" @node-click="openGene" />
      </div>

      <!-- Report tab -->
      <div v-if="activeTab === 'report'">
        <div v-if="!analysis.result.llm_insight" class="state-card state-card-compact">
          <h3>No report</h3>
          <p>The report will appear after enrichment and evidence retrieval complete.</p>
        </div>
        <div v-else class="report-shell">
          <div class="report-banner">
            <div class="banner-item"><FlaskConical :size="13" /> Context: <b>&nbsp;{{ analysis.result.disease_context }}</b></div>
            <div class="banner-item"><Clock :size="13" /> <b>&nbsp;{{ formatTimestamp(analysis.result.timestamp) }}</b></div>
          </div>
          <div class="report-content" v-html="reportHtml"></div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import {
  CheckCircle2, Square, MessageSquare, Clipboard, Download,
  Dna, GitBranch, ScanSearch, BookOpen, Globe,
  Activity, ListTree, BarChart3, Share2, FileText,
  FlaskConical, Clock, Loader2, AlertCircle,
} from 'lucide-vue-next';
import { useAnalysisStore } from '../stores/analysis';
import { useChatStore } from '../stores/chat';
import { useUiStore } from '../stores/ui';
import { renderMarkdownSafe } from '../utils/markdown';
import NetworkGraph from './NetworkGraph.vue';
import PipelineViz from './PipelineViz.vue';

const analysis = useAnalysisStore();
const chat = useChatStore();
const ui = useUiStore();

const activeTab = ref<string>('pipeline');
const activeEnrichSub = ref('');
const activeSourceSub = ref('pubmed');

// When result loads, init enrichment sub-tab
watch(() => analysis.result, (r) => {
  if (r) {
    const keys = Object.keys(r.enrichment_results || {});
    if (keys.length && !activeEnrichSub.value) activeEnrichSub.value = keys[0];
  }
}, { immediate: true });

// Tab config — same order as original
const enrichmentKeys = computed(() => Object.keys(analysis.result?.enrichment_results || {}));
const enrichedTermCount = computed(() =>
  enrichmentKeys.value.reduce((sum, k) => sum + (analysis.result?.enrichment_results?.[k]?.length || 0), 0)
);
const pubmedSources = computed(() => analysis.result?.sources?.pubmed || []);
const webSources = computed(() => analysis.result?.sources?.web || []);
const totalSources = computed(() => pubmedSources.value.length + webSources.value.length);
const relations = computed(() => analysis.result?.gene_relations || []);
const geneValidation = computed(() => analysis.result?.gene_validation || analysis.validation || {} as Partial<import('../types').ValidationResponse>);
const geneRows = computed(() => geneValidation.value.rows || []);
const graphNodes = computed(() => analysis.result?.graph?.nodes || []);

const tabs = computed(() => [
  { id: 'pipeline', label: 'Pipeline', icon: Activity, count: null },
  { id: 'genes', label: 'Genes', icon: ListTree, count: geneRows.value.length || analysis.result?.input_genes?.length || 0 },
  { id: 'enrichment', label: 'Enrichment', icon: BarChart3, count: enrichedTermCount.value },
  { id: 'sources', label: 'Sources', icon: BookOpen, count: totalSources.value },
  { id: 'network', label: 'Network', icon: Share2, count: graphNodes.value.length },
  { id: 'report', label: 'Insight Report', icon: FileText, count: null },
]);

const reportHtml = computed(() => renderMarkdownSafe(analysis.result?.llm_insight || ''));

const enrichSubLabels: Record<string, string> = { GO: 'GO Biological Process', KEGG: 'KEGG Pathways' };
function enrichSubLabel(key: string) {
  return enrichSubLabels[key] || key;
}

function countByStatus(status: string) {
  return geneRows.value.filter((r: { status: string }) => r.status === status).length;
}

function formatPval(v: unknown) {
  if (v == null) return '—';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  return n < 0.001 ? n.toExponential(2) : parseFloat(n.toFixed(4)).toString();
}

function sigClass(row: { p_adjusted?: number; p_value?: number }) {
  const pv = row.p_adjusted ?? row.p_value ?? 1;
  if (pv < 0.001) return 'sig-high';
  if (pv < 0.01) return 'sig-mid';
  return '';
}

function formatTimestamp(ts: string | null | undefined) {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return ts; }
}

async function openGene(symbol: string) {
  await analysis.openGene(symbol);
}

async function copyReport() {
  await navigator.clipboard.writeText(analysis.result?.llm_insight || '');
  ui.showToast('Report copied');
}

function downloadJson() {
  const blob = new Blob([JSON.stringify(analysis.result, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'enrichrag-result.json';
  anchor.click();
  URL.revokeObjectURL(url);
  ui.showToast('JSON exported');
}
</script>
