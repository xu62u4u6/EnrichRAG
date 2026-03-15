import { defineStore } from 'pinia';

export const useUiStore = defineStore('ui', {
  state: () => ({
    currentView: 'input' as 'input' | 'results' | 'history',
    toast: '',
  }),
  actions: {
    showToast(message: string) {
      this.toast = message;
      window.setTimeout(() => {
        if (this.toast === message) this.toast = '';
      }, 2500);
    },
  },
});
