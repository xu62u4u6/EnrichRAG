import { defineStore } from 'pinia';
import type { ChatMessage, PipelineResult } from '../types';
import { api } from '../utils/api';

async function* readSseLikeStream(response: Response) {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n');
    buffer = chunks.pop() || '';
    for (const chunk of chunks) {
      const lines = chunk.split('\n').filter((line) => line.startsWith('data: '));
      for (const line of lines) {
        yield JSON.parse(line.slice(6));
      }
    }
  }
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [] as ChatMessage[],
    open: false,
    loading: false,
  }),
  actions: {
    reset() {
      this.messages = [];
    },
    async send(query: string, result: PipelineResult) {
      this.loading = true;
      const assistantMessage: ChatMessage = { role: 'assistant', content: '' };
      this.messages.push({ role: 'user', content: query });
      this.messages.push(assistantMessage);
      try {
        const response = await api.chat({ query, result, history: this.messages.slice(0, -1) });
        if (!response.ok) throw new Error('Chat request failed');
        for await (const event of readSseLikeStream(response)) {
          if (event.event === 'chunk') assistantMessage.content += event.data || '';
          if (event.event === 'error') throw new Error(event.message || 'Chat stream failed');
        }
      } catch (error) {
        assistantMessage.content = `Error: ${error instanceof Error ? error.message : 'Unknown error'}`;
        throw error;
      } finally {
        this.loading = false;
      }
    },
  },
});
