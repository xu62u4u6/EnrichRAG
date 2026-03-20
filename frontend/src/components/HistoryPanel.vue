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

      <div v-if="history.loading" class="empty-state empty-state--padded">Loading history…</div>
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
          <button
            class="history-delete-btn"
            :class="{ 'history-delete-btn--confirm': pendingDelete === item.id }"
            @click="pendingDelete === item.id ? confirmDelete(item.id) : requestDelete(item.id)"
            :aria-label="pendingDelete === item.id ? 'Confirm delete' : 'Delete history item'"
          >
            <template v-if="pendingDelete === item.id">
              <AlertTriangle :size="12" /> Delete?
            </template>
            <template v-else>
              <Trash2 :size="14" />
            </template>
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
import { onMounted, ref } from 'vue';
import { Search, Trash2, ChevronRight, AlertTriangle } from 'lucide-vue-next';
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

const pendingDelete = ref<number | null>(null);

function requestDelete(id: number) {
  pendingDelete.value = id;
  setTimeout(() => { if (pendingDelete.value === id) pendingDelete.value = null; }, 3000);
}

async function confirmDelete(id: number) {
  await history.deleteItem(id);
  pendingDelete.value = null;
  ui.showToast('History item deleted');
}

async function clearAll() {
  if (!window.confirm('Clear all analysis history? This action cannot be undone.')) return;
  await history.clearAll();
  ui.showToast('History cleared');
}
</script>
