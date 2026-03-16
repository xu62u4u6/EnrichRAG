<template>
  <div v-if="!analysis.result?.llm_insight" class="state-card state-card-compact">
    <h3>No report</h3>
    <p>The report will appear after enrichment and evidence retrieval complete.</p>
  </div>
  <div v-else class="report-shell">
    <div class="report-banner">
      <div class="banner-item"><FlaskConical :size="13" /> Context: <b>&nbsp;{{ analysis.result.disease_context }}</b></div>
      <div class="banner-item"><Clock :size="13" /> <b>&nbsp;{{ formatTimestamp(analysis.result.timestamp) }}</b></div>
    </div>
    <div class="report-content" v-html="reportHtml"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Clock, FlaskConical } from 'lucide-vue-next';
import { useAnalysisStore } from '../../stores/analysis';
import { formatTimestamp } from '../../utils/format';
import { renderMarkdownSafe } from '../../utils/markdown';

const analysis = useAnalysisStore();
const reportHtml = computed(() => renderMarkdownSafe(analysis.result?.llm_insight || ''));
</script>
