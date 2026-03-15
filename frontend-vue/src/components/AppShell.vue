<template>
  <div class="app-frame">
    <section v-if="!auth.bootstrapped || !auth.isAuthenticated" class="auth-scene">
      <div class="auth-panel">
        <div class="hero-tag">EnrichRAG Vue Prototype</div>
        <h1>Signal-first biomedical analysis, rebuilt in Vue.</h1>
        <p>New route, isolated build, same backend contract. The existing service remains untouched on the main route.</p>
        <AuthPanel />
      </div>
    </section>

    <template v-else>
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="sidebar-kicker">Parallel UI</div>
          <h1>EnrichRAG</h1>
          <p>{{ auth.user?.display_name }}</p>
        </div>
        <nav class="sidebar-nav">
          <button
            v-for="item in navItems"
            :key="item.id"
            class="nav-chip"
            :class="{ active: ui.currentView === item.id }"
            @click="ui.currentView = item.id"
          >
            {{ item.label }}
          </button>
        </nav>
        <div style="padding: 0.75rem 1rem; border-top: 1px solid var(--gray-100);">
          <button class="ghost-button" style="width: 100%;" @click="handleLogout">Sign out</button>
        </div>
      </aside>

      <main class="workspace">
        <header class="workspace-header">
          <div>
            <p class="eyebrow">Vue Refactor Route</p>
            <h2>Operational cockpit for enrichment analysis</h2>
          </div>
          <div class="header-actions">
            <span class="header-pill">API compatible</span>
            <span class="header-pill">Route isolated</span>
          </div>
        </header>

        <section class="workspace-grid">
          <div class="primary-column">
            <AnalysisForm v-if="ui.currentView === 'input'" />
            <ResultsWorkspace v-if="ui.currentView === 'results'" />
            <HistoryPanel v-if="ui.currentView === 'history'" />
          </div>

          <aside class="secondary-column">
            <section class="status-card">
              <p class="status-kicker">Pipeline telemetry</p>
              <div class="status-grid">
                <div v-for="item in analysis.resultStats" :key="item.label" class="metric-tile">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>
              <ol class="progress-list">
                <li v-for="(event, index) in recentProgress" :key="index">
                  <strong>{{ event.event }}</strong>
                  <span>{{ event.message || 'running' }}</span>
                </li>
              </ol>
            </section>
          </aside>
        </section>
      </main>

      <ChatDrawer />
      <GeneDrawer />
      <transition name="fade">
        <div v-if="ui.toast" class="toast">{{ ui.toast }}</div>
      </transition>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useAnalysisStore } from '../stores/analysis';
import { useAuthStore } from '../stores/auth';
import { useUiStore } from '../stores/ui';
import AnalysisForm from './AnalysisForm.vue';
import AuthPanel from './AuthPanel.vue';
import ChatDrawer from './ChatDrawer.vue';
import GeneDrawer from './GeneDrawer.vue';
import HistoryPanel from './HistoryPanel.vue';
import ResultsWorkspace from './ResultsWorkspace.vue';

const auth = useAuthStore();
const ui = useUiStore();
const analysis = useAnalysisStore();

const navItems = [
  { id: 'input', label: 'New Analysis' },
  { id: 'results', label: 'Results' },
  { id: 'history', label: 'History' },
] as const;

const recentProgress = computed(() => analysis.progress.slice(-8).reverse());

async function handleLogout() {
  await auth.logout();
}

onMounted(async () => {
  await auth.bootstrap();
});
</script>
