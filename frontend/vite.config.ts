import { defineConfig, type Plugin } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'node:path';
import { readFileSync } from 'node:fs';

// Read URL_PREFIX from root .env so the dev proxy matches the backend's routing
function readEnvPrefix(): string {
  try {
    const env = readFileSync(resolve(__dirname, '../.env'), 'utf-8');
    const match = env.match(/^URL_PREFIX=(.+)$/m);
    const raw = match?.[1]?.trim() ?? '';
    return raw ? `/${raw.replace(/^\//, '')}` : '';
  } catch {
    return '';
  }
}

const apiPrefix = readEnvPrefix(); // e.g. "/test0948395013"

// Replace __UI_BASE__ and __API_PREFIX__ in index.html during dev
// (in production FastAPI does this server-side)
const injectHtmlVars = (): Plugin => ({
  name: 'inject-html-vars',
  transformIndexHtml(html) {
    return html
      .replace('__UI_BASE__', '/')
      .replace('__API_PREFIX__', ''); // proxy handles prefix routing in dev
  },
});

export default defineConfig({
  plugins: [vue(), injectHtmlVars()],
  base: './',
  build: {
    outDir: resolve(__dirname, 'dist'),
    emptyOutDir: true,
  },
  server: {
    port: 6431,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:6432',
        changeOrigin: true,
        rewrite: apiPrefix ? (path) => `${apiPrefix}${path}` : undefined,
      },
    },
  },
});
