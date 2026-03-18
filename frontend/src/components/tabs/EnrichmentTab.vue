<template>
  <div v-if="!enrichmentKeys.length" class="table-card">
    <div class="state-card state-card-compact">
      <h3>No enrichment results</h3>
      <p>No significant terms are available in the selected databases.</p>
    </div>
  </div>
  <template v-else>
    <div class="sub-tabs">
      <button
        v-for="key in enrichmentKeys"
        :key="key"
        class="sub-tab-btn"
        :class="{ active: activeEnrichSub === key }"
        @click="activeEnrichSub = key"
      >
        {{ enrichSubLabel(key) }} {{ (analysis.result?.enrichment_results?.[key] || []).length }}
      </button>
    </div>
    <div v-for="key in enrichmentKeys" :key="key" class="sub-panel" :class="{ active: activeEnrichSub === key }">
      <div class="table-card">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Term</th>
                <th>Overlap</th>
                <th>P-value</th>
                <th>Adj. P-value</th>
                <th>Genes</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, idx) in (analysis.result?.enrichment_results?.[key] || [])"
                :key="idx"
                :class="sigClass(row as { p_adjusted?: number; p_value?: number })"
              >
                <td class="cell-term">{{ (row as Record<string, unknown>).term }}</td>
                <td class="cell-overlap">{{ (row as Record<string, unknown>).overlap }}</td>
                <td class="cell-pval">{{ formatPval((row as Record<string, unknown>).p_value) }}</td>
                <td class="cell-pval">{{ formatPval((row as Record<string, unknown>).p_adjusted) }}</td>
                <td class="cell-genes">
                  <template v-if="typeof (row as Record<string, unknown>).genes === 'string'">
                    <span
                      v-for="gene in ((row as Record<string, unknown>).genes as string).split(/[;,]\s*/)"
                      :key="gene"
                      class="gene-pill"
                    >
                      {{ gene.trim() }}
                    </span>
                  </template>
                  <template v-else>{{ (row as Record<string, unknown>).genes }}</template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </template>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useAnalysisStore } from '../../stores/analysis';
import { formatPval, sigClass } from '../../utils/format';

const analysis = useAnalysisStore();
const activeEnrichSub = ref('');
const enrichmentKeys = computed(() => Object.keys(analysis.result?.enrichment_results || {}));

watch(
  enrichmentKeys,
  (keys) => {
    if (!keys.length) {
      activeEnrichSub.value = '';
      return;
    }
    if (!keys.includes(activeEnrichSub.value)) {
      activeEnrichSub.value = keys[0];
    }
  },
  { immediate: true },
);

const enrichSubLabels: Record<string, string> = {
  GO: 'GO Biological Process',
  KEGG: 'KEGG Pathways',
};

function enrichSubLabel(key: string) {
  return enrichSubLabels[key] || key;
}
</script>
