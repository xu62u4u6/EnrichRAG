<template>
  <transition name="slide">
    <aside v-if="analysis.activeGeneProfile" class="drawer drawer-gene">
      <div class="drawer-header">
        <div>
          <p class="eyebrow">Gene profile</p>
          <h3>{{ analysis.activeGeneProfile.canonical_symbol }}</h3>
        </div>
        <button class="ghost-button" @click="analysis.closeGene()">Close</button>
      </div>
      <dl class="gene-grid">
        <template v-for="(value, key) in details" :key="key">
          <dt>{{ key }}</dt>
          <dd>{{ value }}</dd>
        </template>
      </dl>
    </aside>
  </transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAnalysisStore } from '../stores/analysis';

const analysis = useAnalysisStore();

const details = computed(() => {
  const profile = analysis.activeGeneProfile;
  if (!profile) return {};
  return {
    Symbol: profile.official_symbol || profile.canonical_symbol,
    Name: profile.official_full_name || '—',
    Description: profile.description || '—',
    Synonyms: profile.synonyms || '—',
    Chromosome: profile.chromosome || '—',
    MapLocation: profile.map_location || '—',
    GeneID: profile.gene_id || '—',
    Type: profile.type_of_gene || '—',
  };
});
</script>
