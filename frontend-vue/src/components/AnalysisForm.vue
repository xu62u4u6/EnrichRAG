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

    <div v-if="analysis.validation" class="validation-panel">
      <div class="validation-head">
        <div>
          <h3>Gene Validation</h3>
          <p>Resolved symbols used by the analysis pipeline.</p>
        </div>
        <div class="validation-badges">
          <span class="validation-badge accepted">Accepted {{ analysis.validation.accepted.length }}</span>
          <span class="validation-badge remapped">Remapped {{ analysis.validation.remapped.length }}</span>
          <span class="validation-badge rejected">Rejected {{ analysis.validation.rejected.length }}</span>
        </div>
      </div>
      <div class="table-card table-card-flat">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Input Gene</th>
                <th>Normalized Gene</th>
                <th>Status</th>
                <th>Source</th>
                <th>Gene ID</th>
                <th>Official Name</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in analysis.validation.rows" :key="`${row.input_gene}-${row.status}`">
                <td class="cell-term">{{ row.input_gene }}</td>
                <td>{{ row.normalized_gene || row.normalized_symbol || '—' }}</td>
                <td><span class="status-pill" :class="row.status">{{ row.status }}</span></td>
                <td>{{ row.source || '—' }}</td>
                <td class="cell-overlap">{{ row.gene_id || '—' }}</td>
                <td>{{ row.official_name || row.description || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="validation-note">Analysis ran with {{ analysis.validation.normalized_genes.length }} normalized genes.</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CornerDownLeft, Square } from 'lucide-vue-next';
import { useAnalysisStore } from '../stores/analysis';
import { useUiStore } from '../stores/ui';

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
  await analysis.validateGenes();
  ui.showToast('Gene validation complete');
}

function run() {
  analysis.runAnalysis();
  ui.currentView = 'results';
  ui.showToast('Pipeline started');
}
</script>
