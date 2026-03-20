<template>
  <div class="validation-panel">
    <div class="validation-head">
      <div>
        <h3>Gene Validation</h3>
        <p>Resolved symbols used by the analysis pipeline.</p>
      </div>
      <div class="validation-badges">
        <span class="validation-badge accepted">Accepted {{ summaryData.accepted }}</span>
        <span class="validation-badge remapped">Remapped {{ summaryData.remapped }}</span>
        <span class="validation-badge rejected">Rejected {{ summaryData.rejected }}</span>
      </div>
    </div>
    <DataTable
      :data="rows"
      :columns="validationColumns"
      card-class="table-card-flat"
      searchable
      search-placeholder="Search genes..."
    />
    <div v-if="(normalizedCount ?? 0) > 0" class="validation-note">
      Analysis ran with {{ normalizedCount }} normalized genes.
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue';
import type { ColumnDef } from '@tanstack/vue-table';
import type { ValidationRow } from '../types';
import { useGeneDrawerStore } from '../stores/geneDrawer';
import DataTable from './DataTable.vue';

const props = defineProps<{
  rows: ValidationRow[];
  summary?: { accepted: number; remapped: number; rejected: number };
  normalizedCount?: number;
}>();

const geneDrawer = useGeneDrawerStore();

const summaryData = computed(() => {
  if (props.summary) return props.summary;
  return {
    accepted: props.rows.filter((r) => r.status === 'accepted').length,
    remapped: props.rows.filter((r) => r.status === 'remapped').length,
    rejected: props.rows.filter((r) => r.status === 'rejected').length,
  };
});

const validationColumns: ColumnDef<ValidationRow, any>[] = [
  {
    accessorKey: 'input_gene',
    header: 'Input Gene',
    meta: { tdClass: 'cell-term' },
  },
  {
    accessorKey: 'normalized_gene',
    header: 'Normalized Gene',
    cell: (info) => {
      const row = info.row.original;
      if (row.normalized_gene) {
        return h('button', {
          class: 'gene-pill gene-pill-btn',
          onClick: () => geneDrawer.openGene(row.normalized_gene!),
        }, row.normalized_gene);
      }
      return h('span', { class: 'gene-pill gene-pill-muted' }, row.normalized_symbol || '—');
    },
    enableSorting: false,
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: (info) => {
      const status = info.getValue() as string;
      return h('span', { class: `status-pill ${status}` }, status);
    },
  },
  {
    accessorFn: (row) => row.source || '—',
    header: 'Source',
  },
  {
    accessorFn: (row) => row.gene_id || '—',
    header: 'Gene ID',
    meta: { tdClass: 'cell-overlap' },
  },
  {
    accessorFn: (row) => row.official_name || row.description || '—',
    header: 'Official Name',
  },
];
</script>
