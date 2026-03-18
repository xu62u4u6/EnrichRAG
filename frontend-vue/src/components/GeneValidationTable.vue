<template>
  <div class="validation-panel">
    <div class="validation-head">
      <div>
        <h3>Gene Validation</h3>
        <p>Resolved symbols used by the analysis pipeline.</p>
      </div>
      <div class="validation-badges">
        <span class="validation-badge accepted">Accepted {{ summary.accepted }}</span>
        <span class="validation-badge remapped">Remapped {{ summary.remapped }}</span>
        <span class="validation-badge rejected">Rejected {{ summary.rejected }}</span>
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
            <tr v-for="row in rows" :key="`${row.input_gene}-${row.status}`">
              <td class="cell-term">{{ row.input_gene }}</td>
              <td>
                <button
                  v-if="row.normalized_gene"
                  class="gene-pill gene-pill-btn"
                  @click="geneDrawer.openGene(row.normalized_gene)"
                >{{ row.normalized_gene }}</button>
                <span v-else class="gene-pill gene-pill-muted">{{ row.normalized_symbol || '—' }}</span>
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
    <div v-if="(normalizedCount ?? 0) > 0" class="validation-note">
      Analysis ran with {{ normalizedCount }} normalized genes.
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ValidationRow } from '../types';
import { useGeneDrawerStore } from '../stores/geneDrawer';

const props = defineProps<{
  rows: ValidationRow[];
  summary?: { accepted: number; remapped: number; rejected: number };
  normalizedCount?: number;
}>();

const geneDrawer = useGeneDrawerStore();

const summary = computed(() => {
  if (props.summary) return props.summary;
  return {
    accepted: props.rows.filter((r) => r.status === 'accepted').length,
    remapped: props.rows.filter((r) => r.status === 'remapped').length,
    rejected: props.rows.filter((r) => r.status === 'rejected').length,
  };
});
</script>
