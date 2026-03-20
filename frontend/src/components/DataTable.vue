<template>
  <div class="table-card" :class="cardClass">
    <div v-if="searchable" class="table-search">
      <Search :size="14" class="table-search-icon" />
      <input
        v-model="globalFilter"
        type="text"
        :placeholder="searchPlaceholder || 'Search...'"
        class="table-search-input"
      />
    </div>
    <div ref="wrapRef" class="table-wrap" :class="{ 'has-scroll-right': hasScrollRight }" @scroll="checkScroll">
      <table>
        <thead>
          <tr>
            <th
              v-for="header in table.getFlatHeaders()"
              :key="header.id"
              :class="header.column.columnDef.meta?.thClass"
              @click="header.column.getToggleSortingHandler()?.($event)"
            >
              <span class="th-inner">
                <FlexRender :render="header.column.columnDef.header" :props="header.getContext()" />
                <span v-if="header.column.getIsSorted()" class="sort-indicator">
                  {{ header.column.getIsSorted() === 'asc' ? '↑' : '↓' }}
                </span>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in table.getRowModel().rows"
            :key="row.id"
            :class="rowClass?.(row.original)"
          >
            <td
              v-for="cell in row.getVisibleCells()"
              :key="cell.id"
              :class="cell.column.columnDef.meta?.tdClass"
            >
              <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts" generic="T">
import { ref, onMounted, onUnmounted } from 'vue';
import { Search } from 'lucide-vue-next';
import {
  useVueTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  FlexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/vue-table';

const props = withDefaults(defineProps<{
  data: T[];
  columns: ColumnDef<T, any>[];
  cardClass?: string;
  rowClass?: (row: T) => string;
  searchable?: boolean;
  searchPlaceholder?: string;
}>(), {
  searchable: false,
});

const sorting = ref<SortingState>([]);
const globalFilter = ref('');

const table = useVueTable({
  get data() { return props.data; },
  get columns() { return props.columns; },
  state: {
    get sorting() { return sorting.value; },
    get globalFilter() { return globalFilter.value; },
  },
  onSortingChange: (updater) => {
    sorting.value = typeof updater === 'function' ? updater(sorting.value) : updater;
  },
  onGlobalFilterChange: (updater) => {
    globalFilter.value = typeof updater === 'function' ? updater(globalFilter.value) : updater;
  },
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
});

// Scroll shadow detection
const wrapRef = ref<HTMLDivElement | null>(null);
const hasScrollRight = ref(false);

function checkScroll() {
  const el = wrapRef.value;
  if (!el) return;
  hasScrollRight.value = el.scrollWidth - el.scrollLeft - el.clientWidth > 1;
}

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  checkScroll();
  if (wrapRef.value) {
    resizeObserver = new ResizeObserver(checkScroll);
    resizeObserver.observe(wrapRef.value);
  }
});

onUnmounted(() => {
  resizeObserver?.disconnect();
});
</script>

<style scoped>
.th-inner {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
}

.sort-indicator {
  font-size: 0.7rem;
  opacity: 0.7;
}

.table-search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.table-search-icon {
  color: var(--gray-400);
  flex-shrink: 0;
}

.table-search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.84rem;
  color: var(--gray-800);
}

.table-search-input::placeholder {
  color: var(--gray-400);
}
</style>
