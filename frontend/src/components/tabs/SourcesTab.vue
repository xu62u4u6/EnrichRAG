<template>
  <div v-if="!totalSources" class="table-card">
    <div class="state-card state-card-compact">
      <h3>No sources</h3>
      <p>No evidence sources were captured for this analysis.</p>
    </div>
  </div>
  <template v-else>
    <div class="sub-tabs">
      <button class="sub-tab-btn" :class="{ active: activeSourceSub === 'pubmed' }" @click="activeSourceSub = 'pubmed'">PubMed {{ pubmedSources.length }}</button>
      <button class="sub-tab-btn" :class="{ active: activeSourceSub === 'web' }" @click="activeSourceSub = 'web'">Web {{ webSources.length }}</button>
    </div>
    <div class="sub-panel" :class="{ active: activeSourceSub === 'pubmed' }">
      <div class="table-card">
        <div class="sources-list">
          <div v-for="source in pubmedSources" :key="source.pmid || source.title" class="source-item">
            <div class="source-icon pubmed"><GraduationCap :size="15" /></div>
            <div class="source-body">
              <a :href="source.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${source.pmid}/` : '#'" target="_blank" rel="noopener noreferrer">{{ source.title || 'Untitled' }}</a>
              <div class="source-meta">
                <span v-if="source.pmid" class="source-meta-badge">PMID:{{ source.pmid }}</span>
                <span v-if="source.journal" class="source-meta-text">{{ source.journal }}</span>
                <span v-if="source.pub_date" class="source-meta-text">{{ source.pub_date }}</span>
                <span v-if="source.authors" class="source-meta-text">{{ source.authors }}</span>
              </div>
              <div class="source-snippet">{{ source.abstract || '' }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="sub-panel" :class="{ active: activeSourceSub === 'web' }">
      <div class="table-card">
        <div class="sources-list">
          <div v-for="source in webSources" :key="source.url || source.title" class="source-item">
            <div class="source-icon web"><Globe :size="15" /></div>
            <div class="source-body">
              <a v-if="source.url" :href="source.url" target="_blank" rel="noopener noreferrer">{{ source.title || 'Untitled' }}</a>
              <div v-else>{{ source.title || 'Untitled' }}</div>
              <div class="source-url">{{ source.url || '' }}</div>
              <div class="source-snippet">{{ source.content || source.snippet || '' }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Globe, GraduationCap } from 'lucide-vue-next';
import { useAnalysisStore } from '../../stores/analysis';

const analysis = useAnalysisStore();
const activeSourceSub = ref<'pubmed' | 'web'>('pubmed');
const pubmedSources = computed(() => analysis.result?.sources?.pubmed || []);
const webSources = computed(() => analysis.result?.sources?.web || []);
const totalSources = computed(() => pubmedSources.value.length + webSources.value.length);

watch(
  totalSources,
  () => {
    if (pubmedSources.value.length || !webSources.value.length) {
      activeSourceSub.value = 'pubmed';
      return;
    }
    activeSourceSub.value = 'web';
  },
  { immediate: true },
);
</script>
