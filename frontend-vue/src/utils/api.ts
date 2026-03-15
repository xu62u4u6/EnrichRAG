const rawBase = window.__ENRICHRAG_VUE_BASE__ || '/ui-vue';

export const UI_BASE = rawBase.replace(/\/$/, '');
export const API_PREFIX = (window.__API_PREFIX || '').replace(/\/$/, '');

function buildUrl(path: string) {
  return `${API_PREFIX}${path}`;
}

async function parseJson<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray((payload as { detail?: unknown }).detail)
      ? (payload as { detail: Array<{ msg?: string }> }).detail.map((item) => item.msg).join('; ')
      : (payload as { detail?: string }).detail;
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return payload as T;
}

export const api = {
  me: () => fetch(buildUrl('/api/auth/me'), { credentials: 'same-origin' }),
  login: (payload: { email: string; password: string }) =>
    fetch(buildUrl('/api/auth/login'), {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  register: (payload: { email: string; password: string; display_name: string }) =>
    fetch(buildUrl('/api/auth/register'), {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  logout: () =>
    fetch(buildUrl('/api/auth/logout'), {
      method: 'POST',
      credentials: 'same-origin',
    }),
  history: () => fetch(buildUrl('/api/history'), { credentials: 'same-origin' }),
  historyItem: (id: number) => fetch(buildUrl(`/api/history/${encodeURIComponent(String(id))}`), { credentials: 'same-origin' }),
  deleteHistoryItem: (id: number) =>
    fetch(buildUrl(`/api/history/${encodeURIComponent(String(id))}`), {
      method: 'DELETE',
      credentials: 'same-origin',
    }),
  clearHistory: () =>
    fetch(buildUrl('/api/history'), {
      method: 'DELETE',
      credentials: 'same-origin',
    }),
  validateGenes: (genes: string) =>
    fetch(buildUrl('/api/genes/validate'), {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ genes }),
    }),
  geneProfile: (symbol: string) => fetch(buildUrl(`/api/genes/${encodeURIComponent(symbol)}`), { credentials: 'same-origin' }),
  chat: (payload: { query: string; result: unknown; history: Array<{ role: string; content: string }> }) =>
    fetch(buildUrl('/api/chat'), {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  analyzeStream: (query: string) => new EventSource(buildUrl(`/api/analyze/stream?${query}`)),
  parseJson,
};
