import { defineStore } from 'pinia';
import { api } from '../utils/api';
import type { HistoryItem, PipelineResult } from '../types';

export const useHistoryStore = defineStore('history', {
  state: () => ({
    items: [] as HistoryItem[],
    searchTerm: '',
    loading: false,
  }),
  getters: {
    filteredItems(state) {
      const term = state.searchTerm.trim().toLowerCase();
      if (!term) return state.items;
      return state.items.filter((item) =>
        `${item.disease_context} ${item.input_genes.join(' ')}`.toLowerCase().includes(term),
      );
    },
  },
  actions: {
    async refresh() {
      this.loading = true;
      try {
        const response = await api.history();
        const payload = await api.parseJson<{ items: HistoryItem[] }>(response);
        this.items = payload.items || [];
      } finally {
        this.loading = false;
      }
    },
    async load(id: number) {
      const response = await api.historyItem(id);
      return api.parseJson<PipelineResult>(response);
    },
    async deleteItem(id: number) {
      const response = await api.deleteHistoryItem(id);
      await api.parseJson(response);
      this.items = this.items.filter((item) => item.id !== id);
    },
    async clearAll() {
      const response = await api.clearHistory();
      await api.parseJson(response);
      this.items = [];
    },
  },
});
