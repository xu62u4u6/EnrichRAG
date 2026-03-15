<template>
  <section class="panel result-shell">
    <div class="panel-header">
      <div>
        <p class="eyebrow">Result Atlas</p>
        <h3>{{ analysis.result?.disease_context || 'No analysis loaded' }}</h3>
        <p class="panel-copy">{{ timestamp }}</p>
      </div>
      <div class="button-row">
        <button class="secondary-button" :disabled="!analysis.result" @click="copyReport">Copy report</button>
        <button class="secondary-button" :disabled="!analysis.result" @click="downloadJson">Download JSON</button>
        <button class="primary-button" :disabled="!analysis.result" @click="chat.open = true">Ask assistant</button>
      </div>
    </div>

    <div v-if="!analysis.result" class="empty-state">
      Run an analysis or load one from history to populate the Vue results workspace.
    </div>

    <template v-else>
      <div class="tab-row">
        <button v-for="item in tabs" :key="item.id" class="tab-button" :class="{ active: activeTab === item.id }" @click="activeTab = item.id">
          {{ item.label }}
        </button>
      </div>

      <div v-if="activeTab === 'report'" class="markdown-card" v-html="reportHtml"></div>

      <div v-if="activeTab === 'enrichment'" class="table-shell">
        <div v-for="(rows, key) in enrichmentEntries" :key="key" class="dataset-block">
          <div class="dataset-title">{{ key }}</div>
          <table>
            <thead>
              <tr>
                <th v-for="header in tableHeaders(rows)" :key="header">{{ header }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in rows.slice(0, 12)" :key="index">
                <td v-for="header in tableHeaders(rows)" :key="header">{{ valueOf(row, header) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="activeTab === 'sources'" class="source-grid">
        <article v-for="item in allSources" :key="`${item.title}-${item.url}`" class="source-card">
          <p class="source-label">{{ item.source || item.journal || 'Source' }}</p>
          <h4>{{ item.title || item.url || 'Untitled source' }}</h4>
          <p>{{ item.snippet || 'No snippet available.' }}</p>
          <a v-if="item.url" :href="item.url" target="_blank" rel="noopener noreferrer">Open source</a>
        </article>
      </div>

      <div v-if="activeTab === 'relations'" class="table-shell">
        <table>
          <thead>
            <tr>
              <th v-for="header in relationHeaders" :key="header">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in relations" :key="index">
              <td v-for="header in relationHeaders" :key="header">{{ valueOf(row, header) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="activeTab === 'graph'" class="graph-stage">
        <NetworkGraph :nodes="analysis.result.graph?.nodes || []" :edges="analysis.result.graph?.edges || []" @node-click="openGene" />
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useAnalysisStore } from '../stores/analysis';
import { useChatStore } from '../stores/chat';
import { useUiStore } from '../stores/ui';
import { formatDate } from '../utils/format';
import { renderMarkdownSafe } from '../utils/markdown';
import NetworkGraph from './NetworkGraph.vue';

const analysis = useAnalysisStore();
const chat = useChatStore();
const ui = useUiStore();
const activeTab = ref<'report' | 'enrichment' | 'sources' | 'relations' | 'graph'>('report');
const tabs = [
  { id: 'report', label: 'Report' },
  { id: 'enrichment', label: 'Enrichment' },
  { id: 'sources', label: 'Sources' },
  { id: 'relations', label: 'Relations' },
  { id: 'graph', label: 'Graph' },
] as const;

const reportHtml = computed(() => renderMarkdownSafe(analysis.result?.llm_insight || ''));
const enrichmentEntries = computed(() => Object.entries(analysis.result?.enrichment_results || {}));
const allSources = computed(() => [...(analysis.result?.sources?.web || []), ...(analysis.result?.sources?.pubmed || [])]);
const relations = computed(() => analysis.result?.gene_relations || []);
const relationHeaders = computed(() => {
  const first = relations.value[0];
  return first ? Object.keys(first) : ['No relations'];
});
const timestamp = computed(() => formatDate(analysis.result?.timestamp));

function tableHeaders(rows: unknown[]) {
  const first = rows[0];
  return first && typeof first === 'object' ? Object.keys(first as Record<string, unknown>) : ['value'];
}

function valueOf(row: unknown, header: string) {
  if (!row || typeof row !== 'object') return row;
  const value = (row as Record<string, unknown>)[header];
  return Array.isArray(value) ? value.join(', ') : String(value ?? '—');
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
