<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <p class="eyebrow">Input Console</p>
        <h3>Configure analysis</h3>
      </div>
      <button class="ghost-button" @click="reset">Reset validation</button>
    </div>

    <label class="field">
      <span>Gene symbols</span>
      <textarea v-model="analysis.genes" rows="8" @input="analysis.resetValidation()"></textarea>
    </label>

    <div class="field-row">
      <label class="field">
        <span>Disease context</span>
        <input v-model="analysis.disease" @input="analysis.resetValidation()" />
      </label>
      <label class="field">
        <span>P-value threshold</span>
        <input v-model.number="analysis.pval" type="number" min="0" max="1" step="0.01" />
      </label>
    </div>

    <div class="button-row">
      <button class="secondary-button" :disabled="analysis.status === 'validating'" @click="validate">Validate genes</button>
      <button class="primary-button" :disabled="!analysis.canRun" @click="run">Run pipeline</button>
      <button v-if="analysis.running" class="ghost-button" @click="analysis.cancelRun()">Stop</button>
    </div>

    <p v-if="analysis.error" class="error-text">{{ analysis.error }}</p>

    <div v-if="analysis.validation" class="validation-grid">
      <article class="summary-card">
        <span>Accepted</span>
        <strong>{{ analysis.validation.accepted.length }}</strong>
      </article>
      <article class="summary-card">
        <span>Remapped</span>
        <strong>{{ analysis.validation.remapped.length }}</strong>
      </article>
      <article class="summary-card">
        <span>Rejected</span>
        <strong>{{ analysis.validation.rejected.length }}</strong>
      </article>
    </div>

    <div v-if="analysis.validation" class="table-shell">
      <table>
        <thead>
          <tr>
            <th>Input</th>
            <th>Normalized</th>
            <th>Status</th>
            <th>Info</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in analysis.validation.rows" :key="`${row.input_gene}-${row.status}`">
            <td>{{ row.input_gene }}</td>
            <td>{{ row.normalized_gene || row.normalized_symbol || '—' }}</td>
            <td>{{ row.status }}</td>
            <td>{{ row.description || row.official_name || row.gene_id || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useAnalysisStore } from '../stores/analysis';
import { useUiStore } from '../stores/ui';

const analysis = useAnalysisStore();
const ui = useUiStore();

async function validate() {
  await analysis.validateGenes();
  ui.showToast('Gene validation complete');
}

function run() {
  analysis.runAnalysis();
  ui.currentView = 'results';
  ui.showToast('Pipeline started');
}

function reset() {
  analysis.resetValidation();
}
</script>
