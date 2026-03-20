<template>
  <div class="view active" id="view-input" @keydown="handleKeydown">
    <div class="page-header page-header-compact">
      <h2>Configure Analysis</h2>
      <p>Provide gene sets to initiate the RAG enrichment pipeline.</p>
    </div>
    <div class="card">
      <div class="card-body">
        <div class="form-group">
          <label>Gene Symbols <span class="hint">(comma, space, or newline separated)</span></label>
          <textarea v-model="analysis.genes" rows="4" @input="analysis.resetValidation()" placeholder="BRCA1 BRCA2 RAD51 ATM..."></textarea>
        </div>
        <div class="form-row">
          <div class="form-group form-group--flush">
            <label>Disease Context</label>
            <input type="text" v-model="analysis.disease" @input="analysis.resetValidation()" placeholder="e.g. breast cancer" />
          </div>
          <div class="form-group form-group--flush">
            <label>P-value Threshold</label>
            <input v-model.number="analysis.pval" type="number" min="0" max="1" step="0.01" />
          </div>
        </div>
      </div>
      <div class="card-footer">
        <div class="hint-text"><CornerDownLeft :size="14" /> Press Enter to validate, or Ctrl+Enter to run</div>
        <div class="validation-actions">
          <button class="btn btn-secondary" :disabled="analysis.status === 'validating'" @click="validate">Validate Genes</button>
          <button class="btn btn-primary" :disabled="!analysis.canRun" @click="run">Run Pipeline</button>
          <button v-if="analysis.running" class="btn btn-danger" @click="analysis.cancelRun()"><Square :size="14" /> Stop</button>
        </div>
      </div>
    </div>

    <p v-if="analysis.error" class="error-text error-text--spaced">{{ analysis.error }}</p>

    <transition name="slide-down">
      <GeneValidationTable
        v-if="analysis.validation"
        :rows="analysis.validation.rows"
        :summary="{
          accepted: analysis.validation.accepted.length,
          remapped: analysis.validation.remapped.length,
          rejected: analysis.validation.rejected.length,
        }"
        :normalized-count="analysis.validation.normalized_genes.length"
      />
    </transition>
  </div>
</template>

<script setup lang="ts">
import { CornerDownLeft, Square } from 'lucide-vue-next';
import { useAnalysisStore } from '../stores/analysis';
import { useUiStore } from '../stores/ui';
import GeneValidationTable from './GeneValidationTable.vue';

const analysis = useAnalysisStore();
const ui = useUiStore();

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    if (analysis.canRun) run();
  } else if (e.key === 'Enter' && !e.shiftKey && (e.target as HTMLElement)?.tagName !== 'TEXTAREA') {
    e.preventDefault();
    validate();
  }
}

async function validate() {
  try {
    await analysis.validateGenes();
    ui.showToast('Gene validation complete');
  } catch (e) {
    ui.showToast('Validation failed');
  }
}

function run() {
  analysis.runAnalysis();
  ui.currentView = 'results';
  ui.showToast('Pipeline started');
}
</script>
