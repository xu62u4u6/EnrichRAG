/// <reference types="vite/client" />

declare global {
  interface Window {
    __ENRICHRAG_VUE_BASE__?: string;
    __API_PREFIX?: string;
  }
}

export {};
