<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <p class="eyebrow">Archive</p>
        <h3>Analysis history</h3>
      </div>
      <div class="button-row">
        <input v-model="history.searchTerm" class="search-input" placeholder="Search disease or genes" />
        <button class="ghost-button" :disabled="!history.items.length" @click="clearAll">Clear history</button>
      </div>
    </div>

    <div v-if="history.loading" class="empty-state">Loading history…</div>
    <div v-else-if="!history.filteredItems.length" class="empty-state">No saved analyses found.</div>
    <div v-else class="history-list">
      <article v-for="item in history.filteredItems" :key="item.id" class="history-card">
        <div>
          <p class="eyebrow">{{ item.gene_count }} genes</p>
          <h4>{{ item.disease_context }}</h4>
          <p>{{ item.input_genes.slice(0, 8).join(', ') }}</p>
        </div>
        <div class="button-row">
          <button class="secondary-button" @click="load(item.id)">Load</button>
          <button class="ghost-button" @click="remove(item.id)">Delete</button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useAnalysisStore } from '../stores/analysis';
import { useHistoryStore } from '../stores/history';
import { useUiStore } from '../stores/ui';

const analysis = useAnalysisStore();
const history = useHistoryStore();
const ui = useUiStore();

onMounted(async () => {
  if (!history.items.length) await history.refresh();
});

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
