<template>
  <div class="view active" id="view-history">
    <div class="page-header">
      <h2>Analysis History</h2>
      <p>Review your past enrichment analyses.</p>
    </div>
    <div class="card">
      <div class="history-toolbar">
        <div class="history-toolbar-meta">
          <div class="history-toolbar-copy">{{ history.items.length }} saved results</div>
          <label class="history-search-shell">
            <Search :size="14" />
            <input v-model="history.searchTerm" class="history-search-input" placeholder="Search..." />
          </label>
        </div>
        <button class="history-clear-btn" :disabled="!history.items.length" @click="clearAll">
          <Trash2 :size="12" /> Clear History
        </button>
      </div>

      <div v-if="history.loading" class="empty-state" style="padding: 1.5rem">Loading history…</div>
      <ul v-else-if="history.filteredItems.length" class="history-list">
        <li v-for="item in history.filteredItems" :key="item.id" class="history-item">
          <button class="history-load-btn" @click="load(item.id)">
            <div class="hist-info">
              <div class="hist-title">
                <span class="hist-disease">{{ item.disease_context }}</span>
                <span class="hist-gene-badge">{{ item.gene_count }} genes</span>
              </div>
              <div class="hist-genes">{{ item.input_genes.slice(0, 8).join(', ') }}</div>
            </div>
            <div class="hist-actions">
              <span class="hist-time">{{ formatTime(item.created_at) }}</span>
              <span class="hist-arrow"><ChevronRight :size="15" /></span>
            </div>
          </button>
          <button class="history-delete-btn" @click="remove(item.id)" aria-label="Delete history item">
            <Trash2 :size="14" />
          </button>
        </li>
      </ul>
      <div v-else class="history-empty-row">
        <div class="history-empty-copy">No analysis history found.</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { Search, Trash2, ChevronRight } from 'lucide-vue-next';
import { useAnalysisStore } from '../stores/analysis';
import { useHistoryStore } from '../stores/history';
import { useUiStore } from '../stores/ui';

const analysis = useAnalysisStore();
const history = useHistoryStore();
const ui = useUiStore();

onMounted(async () => {
  if (!history.items.length) await history.refresh();
});

function formatTime(ts: string | undefined) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch { return ts; }
}

async function load(id: number) {
  const result = await history.load(id);
  analysis.setResult(result);
  ui.currentView = 'results';
  ui.showToast('History item loaded');
}

async function remove(id: number) {
  await history.deleteItem(id);
  ui.showToast('History item deleted');
}

async function clearAll() {
  await history.clearAll();
  ui.showToast('History cleared');
}
</script>
