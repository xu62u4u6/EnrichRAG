<template>
  <div v-if="!geneRows.length" class="state-card state-card-compact">
    <h3>No validation details</h3>
    <p>This result does not contain gene validation metadata.</p>
  </div>
  <GeneValidationTable
    v-else
    :rows="geneRows"
    :summary="geneValidation.summary as { accepted: number; remapped: number; rejected: number } | undefined"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ValidationResponse } from '../../types';
import { useAnalysisStore } from '../../stores/analysis';
import GeneValidationTable from '../GeneValidationTable.vue';

const analysis = useAnalysisStore();

const geneValidation = computed(
  () => (analysis.result?.gene_validation || analysis.validation || {}) as Partial<ValidationResponse>,
);
const geneRows = computed(() => geneValidation.value.rows || []);
</script>
