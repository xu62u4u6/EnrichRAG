<template>
  <div class="app-frame ui-refactor-body">
    <div v-if="!auth.bootstrapped" class="app-loading"></div>
    <section v-else-if="!auth.isAuthenticated" class="auth-shell active">
      <div class="auth-crosshair auth-crosshair-v"></div>
      <div class="auth-crosshair auth-crosshair-h"></div>
      <div class="auth-panel">
        <div class="auth-brand">
          <div class="auth-brand-row">
            <div class="auth-logo-mark">
              <img :src="logoSrc" alt="EnrichRAG logo" />
            </div>
            <div class="auth-brand-copy">
              <h1>EnrichRAG</h1>
              <p>Augmentation Protocol</p>
            </div>
          </div>
        </div>
        <AuthPanel />
      </div>
    </section>

    <template v-else>
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="icon brand-image-shell">
            <img :src="logoSrc" alt="EnrichRAG logo" />
          </div>
          <div>
            <h1>EnrichRAG</h1>
            <small>Literature Aug.</small>
          </div>
        </div>
        <button class="mobile-toggle" @click="mobileNavOpen = !mobileNavOpen" aria-label="Toggle menu">
          <Menu :size="20" />
        </button>
        <nav :class="{ 'mobile-open': mobileNavOpen }">
          <button
            v-for="item in navItems"
            :key="item.id"
            class="nav-btn"
            :class="{ active: ui.currentView === item.id }"
            :disabled="item.id === 'results' && !analysis.result && !analysis.running"
            @click="ui.currentView = item.id; mobileNavOpen = false"
          >
            <component :is="item.icon" :size="16" />
            {{ item.label }}
            <span v-if="item.id === 'history'" class="badge">{{ history.items.length }}</span>
          </button>
        </nav>
        <div class="sidebar-footer">
          <div class="sidebar-user">
            <div class="sidebar-user-name">{{ auth.user?.display_name || 'Lab Operator' }}</div>
            <div class="sidebar-user-handle">@{{ usernameHandle }}</div>
          </div>
          <button class="sidebar-signout" @click="handleLogout" aria-label="Sign out" title="Sign out">
            <LogOut :size="15" />
          </button>
        </div>
      </aside>

      <div class="main">
        <div class="main-inner">
          <AnalysisForm v-if="ui.currentView === 'input'" />
          <ResultsWorkspace v-if="ui.currentView === 'results'" />
          <HistoryPanel v-if="ui.currentView === 'history'" />
        </div>
      </div>

      <div v-if="chat.open || geneDrawer.activeGeneProfile" class="drawer-backdrop" @click="closeAllDrawers"></div>
      <ChatDrawer />
      <GeneDrawer />
      <transition name="fade">
        <div v-if="ui.toast" class="toast">{{ ui.toast }}</div>
      </transition>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Dna, LayoutDashboard, History, LogOut, Menu } from 'lucide-vue-next';
import { useAnalysisStore } from '../stores/analysis';
import { useAuthStore } from '../stores/auth';
import { useChatStore } from '../stores/chat';
import { useGeneDrawerStore } from '../stores/geneDrawer';
import { useHistoryStore } from '../stores/history';
import { useUiStore } from '../stores/ui';
import AnalysisForm from './AnalysisForm.vue';
import AuthPanel from './AuthPanel.vue';
import ChatDrawer from './ChatDrawer.vue';
import GeneDrawer from './GeneDrawer.vue';
import HistoryPanel from './HistoryPanel.vue';
import ResultsWorkspace from './ResultsWorkspace.vue';

const auth = useAuthStore();
const ui = useUiStore();
const history = useHistoryStore();
const analysis = useAnalysisStore();
const chat = useChatStore();
const geneDrawer = useGeneDrawerStore();
const mobileNavOpen = ref(false);

const navItems = [
  { id: 'input', label: 'New Analysis', icon: Dna },
  { id: 'results', label: 'Results', icon: LayoutDashboard },
  { id: 'history', label: 'History', icon: History },
] as const;

const logoSrc = `${window.__API_PREFIX || ''}/img/path1.svg`;
const usernameHandle = computed(() => (auth.user?.email || 'lab').split('@')[0]);

function closeAllDrawers() {
  chat.open = false;
  geneDrawer.closeGene();
}

async function handleLogout() {
  await auth.logout();
}

onMounted(async () => {
  await auth.bootstrap();
  if (auth.isAuthenticated) await history.refresh();
});
</script>
