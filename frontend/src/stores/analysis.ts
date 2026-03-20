import { defineStore } from 'pinia';
import type { PipelineResult, ValidationResponse } from '../types';
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
      try {
        const response = await api.validateGenes(this.genes);
        this.validation = await api.parseJson<ValidationResponse>(response);
        return this.validation;
      } catch (e) {
        this.error = e instanceof Error ? e.message : 'Validation failed';
        throw e;
      } finally {
        if (this.status === 'validating') this.status = 'idle';
      }
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
        pval: parseFloat(this.pval.toFixed(4)).toString(),
      });
      const stream = api.analyzeStream(params.toString());
      this.stream = stream;
      stream.onmessage = async (message) => {
        let payload: ProgressEvent;
        try {
          payload = JSON.parse(message.data) as ProgressEvent;
        } catch {
          console.warn('[enrichRAG] malformed SSE data:', message.data);
          return;
        }
        if (payload.event !== 'graph_update' && payload.event !== 'result') {
          console.debug('[enrichRAG pipeline]', payload.event, payload.message || '', payload.data);
        }
        if (payload.event === 'graph_update') {
          const graphData = payload.data as { graph: PipelineResult['graph']; phase: string };
          if (!this.result) {
            this.result = normalizeResultShape({ graph: graphData.graph } as PipelineResult);
          } else {
            this.result = { ...this.result, graph: graphData.graph };
          }
          this.progress.push(payload);
          return;
        }
        if (payload.event === 'result') {
          const raw = payload.data as PipelineResult;
          if (!raw.gene_validation && this.validation) {
            raw.gene_validation = this.validation;
          }
          this.result = normalizeResultShape(raw);
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
      if (result?.gene_validation) {
        this.validation = result.gene_validation;
      }
    },
  },
});
