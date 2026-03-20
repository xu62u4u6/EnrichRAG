<template>
    <aside class="gene-drawer" :class="{ open: !!geneDrawer.activeGeneProfile }">
      <div class="drawer-header">
        <div>
          <div class="drawer-kicker">Gene Profile</div>
          <h3>{{ geneDrawer.activeGeneProfile?.canonical_symbol }}</h3>
        </div>
        <button class="drawer-close" @click="geneDrawer.closeGene()" aria-label="Close gene info">
          <X :size="18" />
        </button>
      </div>
      <div class="drawer-body">
        <div class="drawer-section">
          <div class="drawer-grid">
            <div class="drawer-field">
              <label>Symbol</label>
              <div class="drawer-field-value">{{ profile.canonical_symbol || '—' }}</div>
            </div>
            <div class="drawer-field">
              <label>Gene ID</label>
              <div class="drawer-field-value mono">{{ profile.gene_id || '—' }}</div>
            </div>
            <div class="drawer-field">
              <label>Official Symbol</label>
              <div class="drawer-field-value">{{ profile.official_symbol || '—' }}</div>
            </div>
            <div class="drawer-field">
              <label>Gene Type</label>
              <div class="drawer-field-value">{{ profile.type_of_gene || '—' }}</div>
            </div>
            <div class="drawer-field">
              <label>Chromosome</label>
              <div class="drawer-field-value">{{ profile.chromosome || '—' }}</div>
            </div>
            <div class="drawer-field">
              <label>Map Location</label>
              <div class="drawer-field-value">{{ profile.map_location || '—' }}</div>
            </div>
          </div>
        </div>
        <div class="drawer-section">
          <div class="drawer-field drawer-field-full">
            <label>Official Name</label>
            <div class="drawer-field-value">{{ profile.official_full_name || '—' }}</div>
          </div>
          <div class="drawer-field drawer-field-full">
            <label>Description</label>
            <div class="drawer-field-value">{{ profile.description || '—' }}</div>
          </div>
          <div class="drawer-field drawer-field-full">
            <label>Synonyms</label>
            <div class="drawer-field-value mono">{{ profile.synonyms || '—' }}</div>
          </div>
          <div class="drawer-field drawer-field-full">
            <label>dbXrefs</label>
            <div class="drawer-field-value mono">{{ profile.dbxrefs || '—' }}</div>
          </div>
          <div class="drawer-field drawer-field-full">
            <label>Last Updated</label>
            <div class="drawer-field-value mono">{{ profile.modification_date || '—' }}</div>
          </div>
        </div>
        <div v-if="profile.gene_id" class="drawer-section">
          <a
            class="drawer-link"
            :href="`https://www.ncbi.nlm.nih.gov/gene?Db=gene&Cmd=DetailsSearch&Term=${encodeURIComponent(profile.gene_id)}`"
            target="_blank"
            rel="noopener"
          >
            <ExternalLink :size="14" /> Open in NCBI Gene
          </a>
        </div>
      </div>
    </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { X, ExternalLink } from 'lucide-vue-next';
import { useGeneDrawerStore } from '../stores/geneDrawer';

const geneDrawer = useGeneDrawerStore();

const profile = computed(() => geneDrawer.activeGeneProfile || ({} as NonNullable<typeof geneDrawer.activeGeneProfile>));
</script>
