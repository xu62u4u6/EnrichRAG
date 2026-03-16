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
          <div class="stat-number">{{ relationCount }}</div>
          <div class="stat-label">Relations</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon green"><BookOpen :size="14" /></div>
          <div class="stat-number">{{ totalSources }}</div>
          <div class="stat-label">Sources</div>
        </div>
      </div>

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

      <PipelineViz v-if="activeTab === 'pipeline'" />
      <GenesTab v-else-if="activeTab === 'genes'" />
      <EnrichmentTab v-else-if="activeTab === 'enrichment'" />
      <SourcesTab v-else-if="activeTab === 'sources'" />
      <NetworkTab v-else-if="activeTab === 'network'" />
      <ReportTab v-else-if="activeTab === 'report'" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import {
  CheckCircle2,
  Square,
  MessageSquare,
  Clipboard,
  Download,
  Dna,
  GitBranch,
  ScanSearch,
  BookOpen,
  Activity,
  ListTree,
  BarChart3,
  Share2,
  FileText,
  Loader2,
  AlertCircle,
} from 'lucide-vue-next';
import { useAnalysisStore } from '../stores/analysis';
import { useChatStore } from '../stores/chat';
import { useUiStore } from '../stores/ui';
import EnrichmentTab from './tabs/EnrichmentTab.vue';
import GenesTab from './tabs/GenesTab.vue';
import NetworkTab from './tabs/NetworkTab.vue';
import PipelineViz from './PipelineViz.vue';
import ReportTab from './tabs/ReportTab.vue';
import SourcesTab from './tabs/SourcesTab.vue';

const analysis = useAnalysisStore();
const chat = useChatStore();
const ui = useUiStore();

const activeTab = ref<string>('pipeline');

const enrichmentKeys = computed(() => Object.keys(analysis.result?.enrichment_results || {}));
const enrichedTermCount = computed(() =>
  enrichmentKeys.value.reduce((sum, key) => sum + (analysis.result?.enrichment_results?.[key]?.length || 0), 0),
);
const totalSources = computed(() => (analysis.result?.sources?.pubmed?.length || 0) + (analysis.result?.sources?.web?.length || 0));
const relationCount = computed(() => analysis.result?.gene_relations?.length || 0);
const geneCount = computed(
  () => analysis.result?.gene_validation?.rows?.length || analysis.validation?.rows?.length || analysis.result?.input_genes?.length || 0,
);
const graphNodeCount = computed(() => analysis.result?.graph?.nodes?.length || 0);

const tabs = computed(() => [
  { id: 'pipeline', label: 'Pipeline', icon: Activity, count: null },
  { id: 'genes', label: 'Genes', icon: ListTree, count: geneCount.value },
  { id: 'enrichment', label: 'Enrichment', icon: BarChart3, count: enrichedTermCount.value },
  { id: 'sources', label: 'Sources', icon: BookOpen, count: totalSources.value },
  { id: 'network', label: 'Network', icon: Share2, count: graphNodeCount.value },
  { id: 'report', label: 'Insight Report', icon: FileText, count: null },
]);

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
