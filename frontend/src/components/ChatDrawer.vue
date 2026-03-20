<template>
    <aside class="chat-drawer" :class="{ open: chat.open }">
      <div class="drawer-header">
        <div>
          <div class="drawer-kicker">Analysis QA</div>
          <h3>EnrichRAG Assistant</h3>
          <p class="chat-header-note">Context-aware analysis grounded in the current pipeline result.</p>
        </div>
        <button class="drawer-close" @click="chat.open = false" aria-label="Close chat">
          <X :size="18" />
        </button>
      </div>

      <div ref="chatBody" class="chat-body">
        <div v-if="!chat.messages.length && !chat.loading" class="chat-message assistant chat-message-intro">
          <div class="msg-content">
            <div class="state-card state-card-empty state-card-compact">
              <h3>EnrichRAG Assistant</h3>
              <p>Ask about the current analysis result, report, sources, or relations.</p>
            </div>
            <div class="chat-welcome-rule"></div>
            <div class="chat-suggestions">
              <p class="chat-suggestions-label">Suggested Questions</p>
              <button v-for="suggestion in suggestions" :key="suggestion" class="chat-suggestion-btn" @click="submitSuggestion(suggestion)">
                <ArrowRight :size="17" />
                {{ suggestion }}
              </button>
            </div>
          </div>
        </div>
        <article v-for="(message, index) in chat.messages" :key="index" class="chat-message" :class="[message.role, { pending: isPendingAssistantMessage(message, index) }]">
          <div class="chat-message-meta">
            {{ message.role === 'user' ? 'You' : 'Assistant' }}
          </div>
          <div class="msg-content">
            <template v-if="isPendingAssistantMessage(message, index)">
              <span class="typing-indicator">...</span>
            </template>
            <div v-else v-html="renderMarkdownSafe(message.content)"></div>
          </div>
          <div v-if="message.role === 'assistant' && message.content" class="chat-action-bar">
            <button class="chat-action-btn" title="Copy response" @click="copyMessage(message.content)">
              <Copy :size="13" />
              <span>Copy</span>
            </button>
          </div>
        </article>
      </div>

      <div class="chat-footer">
        <form id="chatForm" @submit.prevent="submit">
          <input v-model="query" type="text" placeholder="Ask about this analysis..." autocomplete="off" :disabled="chat.loading" />
          <button type="submit" class="chat-send-btn" :disabled="chat.loading || !analysis.result || !query.trim()" aria-label="Send message">
            <Send :size="16" />
          </button>
        </form>
        <div class="chat-footer-meta">EnrichRAG Assistant v1.0</div>
      </div>
    </aside>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import { X, Send, ArrowRight, Copy } from 'lucide-vue-next';
import { useAnalysisStore } from '../stores/analysis';
import { useChatStore } from '../stores/chat';
import { useUiStore } from '../stores/ui';
import { renderMarkdownSafe } from '../utils/markdown';

const chat = useChatStore();
const analysis = useAnalysisStore();
const ui = useUiStore();
const query = ref('');
const chatBody = ref<HTMLDivElement | null>(null);

const suggestions = computed(() => {
  const r = analysis.result;
  if (!r) return ['Summarize the key findings'];
  const items: string[] = [];
  const disease = r.disease_context || 'this';
  items.push(`What is the main biological story of this ${disease} analysis?`);
  const enrichKeys = Object.keys(r.enrichment_results || {});
  if (enrichKeys.includes('GO')) items.push('Why are the top GO terms enriched in this gene set?');
  if (enrichKeys.includes('KEGG')) items.push('Which KEGG pathways matter most here, and why?');
  if ((r.gene_relations?.length || 0) > 0) items.push('What are the most important gene-disease relations found?');
  if ((r.sources?.pubmed?.length || 0) > 0) items.push('Summarize the key evidence from the PubMed sources');
  if (items.length < 4) items.push('Which genes are most significant?');
  return items.slice(0, 4);
});

// Auto-scroll on new messages or loading change
watch(
  () => [chat.messages.length, chat.loading],
  async () => {
    await nextTick();
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight;
  },
);

async function submitSuggestion(text: string) {
  if (!analysis.result) return;
  await chat.send(text, analysis.result);
}

async function submit() {
  if (!query.value.trim() || !analysis.result) return;
  const value = query.value;
  query.value = '';
  await chat.send(value, analysis.result);
}

function copyMessage(content: string) {
  navigator.clipboard.writeText(content)
    .then(() => ui.showToast('Response copied'))
    .catch(() => ui.showToast('Copy failed'));
}

function isPendingAssistantMessage(message: { role: string; content: string }, index: number) {
  return chat.loading && message.role === 'assistant' && !message.content && index === chat.messages.length - 1;
}
</script>
