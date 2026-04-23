<template>
  <div class="view active" id="view-results">
    <!-- Empty state: no result and not running -->
    <div v-if="!analysis.result && !analysis.running" class="empty-state-full">
      <div class="empty-state-icon">
        <Inbox :size="36" />
      </div>
      <h3>No Analysis Loaded</h3>
      <p>Run a new analysis or select one from your history to view results.</p>
      <div class="empty-state-cta">
        <button class="btn btn-primary" @click="ui.currentView = 'input'"><FlaskConical :size="14" /> New Analysis</button>
        <button class="btn btn-secondary" @click="ui.currentView = 'history'"><History :size="14" /> View History</button>
      </div>
    </div>

    <!-- Active state: running or has result -->
    <template v-else>
    <div class="results-header">
      <div class="status-badge">
        <template v-if="analysis.running"><Loader2 :size="13" class="spin" /> Running...</template>
        <template v-else-if="analysis.status === 'error'"><AlertCircle :size="13" /> Error</template>
        <template v-else><CheckCircle2 :size="13" /> Analysis Complete</template>
      </div>
      <div class="title-row">
        <div>
          <p class="results-context-label">Disease Context</p>
          <h2>{{ analysis.result?.disease_context || (analysis.running ? analysis.disease : 'No analysis loaded') }}</h2>
          <p class="meta">Targeting <b>{{ analysis.result?.input_genes?.length || (analysis.running ? analysis.genes.trim().split(/[\s,;]+/).length : 0) }}</b> genes</p>
        </div>
        <div class="results-actions">
          <button v-if="analysis.running" class="btn btn-danger" @click="analysis.cancelRun()"><Square :size="14" /> Stop</button>
          <button class="btn btn-secondary" :disabled="!analysis.result" @click="chat.open = true"><MessageSquare :size="14" /> Ask Assistant</button>
          <button ref="copyBtn" class="btn btn-secondary" :disabled="!analysis.result" @click="copyReport"><component :is="copyIcon" :size="14" /> {{ copyLabel }}</button>
          <button ref="htmlBtn" class="btn btn-secondary" :disabled="!analysis.result" @click="downloadHtml"><component :is="htmlIcon" :size="14" /> {{ htmlLabel }}</button>
          <button ref="jsonBtn" class="btn btn-secondary" :disabled="!analysis.result" @click="downloadJson"><component :is="jsonIcon" :size="14" /> {{ jsonLabel }}</button>
        </div>
      </div>
    </div>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon teal"><Dna :size="14" /></div>
          <div class="stat-number">{{ analysis.result?.input_genes?.length || 0 }}</div>
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

      <div ref="tabsWrapper" class="tabs-wrapper">
        <div ref="tabsEl" class="tabs" @scroll="checkTabOverflow">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="tab-btn"
            :class="{ active: activeTab === tab.id }"
            :disabled="analysis.running && !analysis.result && tab.id !== 'pipeline'"
            @click="activeTab = tab.id"
          >
            <component :is="tab.icon" :size="15" />
            {{ tab.label }}
            <span v-if="tab.count != null" class="tab-count">{{ tab.count }}</span>
          </button>
        </div>
      </div>

      <PipelineViz v-show="activeTab === 'pipeline'" />
      <GenesTab v-if="activeTab === 'genes'" />
      <EnrichmentTab v-if="activeTab === 'enrichment'" />
      <SourcesTab v-if="activeTab === 'sources'" />
      <NetworkTab v-if="activeTab === 'network'" />
      <ReportTab v-if="activeTab === 'report'" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue';
import {
  CheckCircle2,
  Square,
  MessageSquare,
  Clipboard,
  Check,
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
  Inbox,
  FlaskConical,
  History,
} from 'lucide-vue-next';
import { useAnalysisStore } from '../stores/analysis';
import { useChatStore } from '../stores/chat';
import { useUiStore } from '../stores/ui';
import { downloadResultHtml } from '../utils/exportHtml';
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

// Tab overflow detection for fade mask
const tabsWrapper = ref<HTMLElement | null>(null);
const tabsEl = ref<HTMLElement | null>(null);

function checkTabOverflow() {
  const wrapper = tabsWrapper.value;
  const tabs = tabsEl.value;
  if (!wrapper || !tabs) return;
  const hasMore = tabs.scrollWidth - tabs.scrollLeft - tabs.clientWidth > 1;
  wrapper.classList.toggle('has-overflow', hasMore);
}

onMounted(() => {
  nextTick(checkTabOverflow);
  window.addEventListener('resize', checkTabOverflow);
});
onUnmounted(() => {
  window.removeEventListener('resize', checkTabOverflow);
});

// Re-check when result arrives (tabs appear via v-else)
watch(() => analysis.result, () => nextTick(checkTabOverflow));

watch(
  () => analysis.running,
  (running) => {
    if (running && !analysis.result) activeTab.value = 'pipeline';
  },
);

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

// Copy / JSON button feedback
const copyLabel = ref('Copy');
const copyIcon = ref(Clipboard);
const htmlLabel = ref('HTML');
const htmlIcon = ref(Download);
const jsonLabel = ref('JSON');
const jsonIcon = ref(Download);

function flashButton(labelRef: typeof copyLabel, iconRef: typeof copyIcon, text: string, originalText: string, originalIcon: typeof Clipboard) {
  labelRef.value = text;
  iconRef.value = Check;
  setTimeout(() => {
    labelRef.value = originalText;
    iconRef.value = originalIcon;
  }, 1200);
}

async function copyReport() {
  const text = (analysis.result?.llm_insight || '').trim();
  if (!text) { ui.showToast('No report to copy'); return; }
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
  flashButton(copyLabel, copyIcon, 'Copied', 'Copy', Clipboard);
  ui.showToast('Report copied');
}

function downloadJson() {
  if (!analysis.result) { ui.showToast('No analysis loaded'); return; }
  const blob = new Blob([JSON.stringify(analysis.result, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  const disease = (analysis.result.disease_context || 'result').replace(/\s+/g, '_');
  anchor.download = `enrichRAG_${disease}_${Date.now()}.json`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  flashButton(jsonLabel, jsonIcon, 'Downloaded', 'JSON', Download);
  ui.showToast('JSON downloaded');
}

function downloadHtml() {
  if (!analysis.result) { ui.showToast('No analysis loaded'); return; }
  const filename = downloadResultHtml(analysis.result);
  flashButton(htmlLabel, htmlIcon, 'Downloaded', 'HTML', Download);
  ui.showToast(`${filename} downloaded`);
}
</script>
