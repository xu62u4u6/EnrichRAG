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
              <div v-if="source.pmid && pmidRelationsMap[source.pmid]?.length" class="source-relations">
                <div
                  v-for="(rel, i) in pmidRelationsMap[source.pmid!]"
                  :key="i"
                  class="source-relation-row"
                >
                  <span class="rel-node">{{ rel.source }}</span>
                  <span class="rel-arrow">—[{{ rel.relation }}]→</span>
                  <span class="rel-node">{{ rel.target }}</span>
                  <span v-if="rel.source_db" class="rel-db">{{ rel.source_db }}</span>
                </div>
              </div>
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

const pmidRelationsMap = computed(() => {
  const map: Record<string, { source: string; relation: string; target: string; source_db: string }[]> = {};
  for (const rel of analysis.result?.gene_relations || []) {
    const pmid = String(rel.pmid || '').replace(/^PMID:/i, '');
    if (!pmid) continue;
    if (!map[pmid]) map[pmid] = [];
    map[pmid].push({
      source: String(rel.source || ''),
      relation: String(rel.relation || ''),
      target: String(rel.target || ''),
      source_db: String(rel.source_db || ''),
    });
  }
  return map;
});

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

<style scoped>
.source-relations {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.source-relation-row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  font-family: var(--font-mono);
  flex-wrap: wrap;
}

.rel-node {
  font-weight: 600;
  color: var(--gray-800);
  background: var(--gray-100);
  padding: 0.1em 0.4em;
  border-radius: 3px;
}

.rel-arrow {
  color: var(--gray-400);
  font-size: 0.72rem;
}

.rel-db {
  font-size: 0.68rem;
  color: var(--gray-400);
  background: var(--teal-50);
  color: var(--teal-600);
  padding: 0.1em 0.35em;
  border-radius: 3px;
  margin-left: auto;
}
</style>
