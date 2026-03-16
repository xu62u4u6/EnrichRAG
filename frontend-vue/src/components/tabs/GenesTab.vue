<template>
  <div v-if="!geneRows.length" class="state-card state-card-compact">
    <h3>No validation details</h3>
    <p>This result does not contain gene validation metadata.</p>
  </div>
  <div v-else class="validation-panel">
    <div class="validation-head">
      <div>
        <h3>Gene Validation</h3>
        <p>Resolved symbols used by the analysis pipeline.</p>
      </div>
      <div class="validation-badges">
        <span class="validation-badge accepted">Accepted {{ geneValidation.summary?.accepted || countByStatus('accepted') }}</span>
        <span class="validation-badge remapped">Remapped {{ geneValidation.summary?.remapped || countByStatus('remapped') }}</span>
        <span class="validation-badge rejected">Rejected {{ geneValidation.summary?.rejected || countByStatus('rejected') }}</span>
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
            <tr v-for="row in geneRows" :key="`${row.input_gene}-${row.status}`">
              <td class="cell-term">{{ row.input_gene }}</td>
              <td>
                <button v-if="row.normalized_gene" class="validation-gene-btn" @click="geneDrawer.openGene(row.normalized_gene)">{{ row.normalized_gene }}</button>
                <span v-else>{{ row.normalized_symbol || '—' }}</span>
              </td>
              <td><span class="status-pill" :class="row.status">{{ row.status }}</span></td>
              <td>{{ row.source || '—' }}</td>
              <td class="cell-overlap">{{ row.gene_id || '—' }}</td>
              <td>{{ row.official_name || row.description || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ValidationResponse } from '../../types';
import { useAnalysisStore } from '../../stores/analysis';
import { useGeneDrawerStore } from '../../stores/geneDrawer';

const analysis = useAnalysisStore();
const geneDrawer = useGeneDrawerStore();

const geneValidation = computed(
  () => (analysis.result?.gene_validation || analysis.validation || {}) as Partial<ValidationResponse>,
);
const geneRows = computed(() => geneValidation.value.rows || []);

function countByStatus(status: string) {
  return geneRows.value.filter((row) => row.status === status).length;
}
</script>
