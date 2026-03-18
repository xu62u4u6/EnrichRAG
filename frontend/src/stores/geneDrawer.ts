import { defineStore } from 'pinia';
import type { GeneProfile } from '../types';
import { api } from '../utils/api';

export const useGeneDrawerStore = defineStore('geneDrawer', {
  state: () => ({
    activeGeneProfile: null as GeneProfile | null,
  }),
  actions: {
    async openGene(symbol: string) {
      const response = await api.geneProfile(symbol);
      this.activeGeneProfile = await api.parseJson<GeneProfile>(response);
      return this.activeGeneProfile;
    },
    closeGene() {
      this.activeGeneProfile = null;
    },
  },
});
