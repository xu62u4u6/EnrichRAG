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
      <DataTable
        :data="(analysis.result?.enrichment_results?.[key] || []) as EnrichRow[]"
        :columns="enrichColumns"
        :row-class="(row: EnrichRow) => sigClass(row)"
        searchable
        search-placeholder="Search terms or genes..."
      />
    </div>
  </template>
</template>

<script setup lang="ts">
import { computed, ref, watch, h } from 'vue';
import type { ColumnDef } from '@tanstack/vue-table';
import { useAnalysisStore } from '../../stores/analysis';
import { formatPval, sigClass } from '../../utils/format';
import DataTable from '../DataTable.vue';

interface EnrichRow {
  term?: string;
  overlap?: string;
  p_value?: number;
  p_adjusted?: number;
  genes?: string;
}

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

const enrichColumns: ColumnDef<EnrichRow, any>[] = [
  {
    accessorKey: 'term',
    header: 'Term',
    meta: { tdClass: 'cell-term' },
  },
  {
    accessorKey: 'overlap',
    header: 'Overlap',
    meta: { tdClass: 'cell-overlap' },
  },
  {
    accessorKey: 'p_value',
    header: 'P-value',
    cell: (info) => formatPval(info.getValue()),
    meta: { tdClass: 'cell-pval' },
    sortingFn: 'basic',
  },
  {
    accessorKey: 'p_adjusted',
    header: 'Adj. P-value',
    cell: (info) => formatPval(info.getValue()),
    meta: { tdClass: 'cell-pval' },
    sortingFn: 'basic',
  },
  {
    accessorKey: 'genes',
    header: 'Genes',
    meta: { tdClass: 'cell-genes' },
    enableSorting: false,
    cell: (info) => {
      const val = info.getValue() as string | undefined;
      if (typeof val !== 'string') return val ?? '';
      const genes = val.split(/[;,]\s*/);
      return h('span', {}, genes.map((gene) =>
        h('span', { class: 'gene-pill', key: gene }, gene.trim()),
      ));
    },
  },
];
</script>
