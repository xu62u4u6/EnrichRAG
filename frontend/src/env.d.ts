/// <reference types="vite/client" />

declare global {
  interface Window {
    __ENRICHRAG_VUE_BASE__?: string;
    __API_PREFIX?: string;
  }
}

declare module '@tanstack/vue-table' {
  interface ColumnMeta<TData, TValue> {
    thClass?: string;
    tdClass?: string;
  }
}

export {};
