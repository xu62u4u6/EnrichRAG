<template>
  <transition name="slide">
    <aside v-if="chat.open" class="drawer">
      <div class="drawer-header">
        <div>
          <p class="eyebrow">Analysis QA</p>
          <h3>EnrichRAG assistant</h3>
        </div>
        <button class="ghost-button" @click="chat.open = false">Close</button>
      </div>

      <div class="chat-stream">
        <article v-for="(message, index) in chat.messages" :key="index" class="chat-bubble" :class="message.role">
          <strong>{{ message.role }}</strong>
          <div v-html="renderMarkdownSafe(message.content)"></div>
        </article>
      </div>

      <form class="chat-form" @submit.prevent="submit">
        <input v-model="query" placeholder="Ask about this analysis…" />
        <button class="primary-button" :disabled="chat.loading || !analysis.result">Send</button>
      </form>
    </aside>
  </transition>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useAnalysisStore } from '../stores/analysis';
import { useChatStore } from '../stores/chat';
import { renderMarkdownSafe } from '../utils/markdown';

const chat = useChatStore();
const analysis = useAnalysisStore();
const query = ref('');

async function submit() {
  if (!query.value.trim() || !analysis.result) return;
  const value = query.value;
  query.value = '';
  await chat.send(value, analysis.result);
}
</script>
