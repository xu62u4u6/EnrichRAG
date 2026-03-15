import { defineStore } from 'pinia';
import type { GeneProfile, PipelineResult, ValidationResponse } from '../types';
import { api } from '../utils/api';
import { normalizeResultShape } from '../utils/format';
import { useHistoryStore } from './history';

interface ProgressEvent {
  event: string;
  message?: string;
  data?: unknown;
}

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    genes: 'BRCA1 BRCA2 RAD51 RAD52 ATM ATR CHEK1 CHEK2 MLH1 MSH2 MSH6 PMS2',
    disease: 'cancer',
    pval: 0.05,
    validation: null as ValidationResponse | null,
    result: null as PipelineResult | null,
    progress: [] as ProgressEvent[],
    running: false,
    stream: null as EventSource | null,
    status: 'idle' as 'idle' | 'validating' | 'running' | 'done' | 'error',
    error: '',
    activeGeneProfile: null as GeneProfile | null,
  }),
  getters: {
    canRun: (state) => Boolean(state.validation?.normalized_genes?.length) && !state.running,
    resultStats: (state) => {
      const result = state.result;
      if (!result) return [];
      return [
        { label: 'Genes', value: String(result.input_genes?.length || 0) },
        { label: 'Relations', value: String(result.gene_relations?.length || 0) },
        { label: 'Web Sources', value: String(result.sources?.web?.length || 0) },
        { label: 'PubMed', value: String(result.sources?.pubmed?.length || 0) },
      ];
    },
  },
  actions: {
    resetValidation() {
      this.validation = null;
    },
    async validateGenes() {
      this.status = 'validating';
      this.error = '';
      const response = await api.validateGenes(this.genes);
      this.validation = await api.parseJson<ValidationResponse>(response);
      this.status = 'idle';
      return this.validation;
    },
    runAnalysis() {
      if (this.stream) this.stream.close();
      this.running = true;
      this.status = 'running';
      this.error = '';
      this.progress = [];
      const params = new URLSearchParams({
        genes: this.genes,
        disease: this.disease,
        pval: String(this.pval),
      });
      const stream = api.analyzeStream(params.toString());
      this.stream = stream;
      stream.onmessage = async (message) => {
        const payload = JSON.parse(message.data) as ProgressEvent;
        if (payload.event === 'result') {
          this.result = normalizeResultShape(payload.data as PipelineResult);
          this.running = false;
          this.status = 'done';
          stream.close();
          this.stream = null;
          const historyStore = useHistoryStore();
          await historyStore.refresh();
          return;
        }
        if (payload.event === 'error') {
          this.error = payload.message || 'Pipeline failed';
          this.running = false;
          this.status = 'error';
          stream.close();
          this.stream = null;
          return;
        }
        this.progress.push(payload);
      };
      stream.onerror = () => {
        this.error = 'Stream disconnected';
        this.running = false;
        this.status = 'error';
        stream.close();
        this.stream = null;
      };
    },
    cancelRun() {
      this.stream?.close();
      this.stream = null;
      this.running = false;
      this.status = 'idle';
    },
    setResult(result: PipelineResult | null) {
      this.result = normalizeResultShape(result);
      this.status = result ? 'done' : 'idle';
    },
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
