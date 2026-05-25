<template>
  <div class="table-card network-tab-card" :class="{ 'is-fullscreen': isFullscreen }" @keydown.esc.stop="exitFullscreen">
    <div v-if="!allNodes.length" class="state-card state-card-compact">
      <h3>No network data</h3>
      <p>No network data yet — a partial graph will appear after local KG lookup.</p>
    </div>
    <template v-else>
      <div class="network-tab-controls">

        <!-- Row 1: presets + status + actions -->
        <div class="network-controls-header">
          <div class="segmented-control">
            <button
              v-for="preset in presets"
              :key="preset.id"
              class="segmented-control-btn"
              :class="{ active: activePreset === preset.id }"
              @click="applyPreset(preset.id)"
            >
              <component :is="preset.icon" :size="14" />
              {{ preset.label }}
            </button>
          </div>

          <div class="graph-status-bar source-meta-badge">
            {{ filteredNodes.length }} nodes · {{ filteredEdges.length }} edges
            <button class="reset-btn" @click="applyPreset(activePreset)">Reset</button>
          </div>
        </div>

        <!-- Row 2: toolbar (search + action buttons) -->
        <div class="graph-toolbar">
          <!-- Search -->
          <div class="graph-search-box" :class="{ 'has-results': searchResults.length > 0 }">
            <Search :size="13" class="graph-search-icon" />
            <input
              ref="searchInputEl"
              v-model="searchQuery"
              class="graph-search-input"
              placeholder="Search nodes…"
              @keydown.enter.prevent="nextSearchResult"
              @keydown.escape="clearSearch"
            />
            <span v-if="searchResults.length" class="graph-search-count">
              {{ searchIndex + 1 }}/{{ searchResults.length }}
            </span>
            <button v-if="searchResults.length > 1" class="graph-search-nav" @click="prevSearchResult" title="Previous">
              <ChevronUp :size="11" />
            </button>
            <button v-if="searchResults.length > 1" class="graph-search-nav" @click="nextSearchResult" title="Next">
              <ChevronDown :size="11" />
            </button>
            <button v-if="searchQuery" class="graph-search-clear" @click="clearSearch">
              <X :size="11" />
            </button>
          </div>

          <div class="graph-action-btns">
            <!-- Selection mode toggle -->
            <button
              class="graph-action-btn"
              :class="{ active: selectionMode }"
              :title="selectionMode ? 'Exit selection mode' : 'Enter selection mode'"
              @click="toggleSelectionMode"
            >
              <MousePointer2 :size="14" />
              <span>Select</span>
            </button>

            <!-- Fullscreen -->
            <button
              class="graph-action-btn"
              :title="isFullscreen ? 'Exit fullscreen (Esc)' : 'Fullscreen'"
              @click="toggleFullscreen"
            >
              <component :is="isFullscreen ? Minimize2 : Maximize2" :size="14" />
            </button>
          </div>
        </div>

        <!-- Accordion filters (custom preset) -->
        <div v-show="activePreset === 'custom'" class="filter-accordion">
          <!-- Source section -->
          <div class="filter-section">
            <div class="filter-section-header" @click="toggleSection('source')">
              <div class="filter-section-left">
                <span class="filter-section-caret" :class="{ open: openSection === 'source' }">▸</span>
                <span class="filter-section-label">Source</span>
              </div>
              <span class="filter-section-summary">{{ sourceSummary }}</span>
            </div>
            <div v-if="openSection === 'source'" class="filter-section-body">
              <div class="filter-row">
                <div class="sub-tabs">
                  <button
                    v-for="src in sourceCategories"
                    :key="src.id"
                    class="filter-pill"
                    :class="{ active: activeSources.has(src.id) }"
                    @click="setCustom(); toggleSource(src.id)"
                  >
                    {{ src.label }} <span class="pill-count">{{ src.count }}</span>
                  </button>
                  <template v-if="activeSources.has('local-kg') && kgSubSources.length > 1">
                    <div class="filter-children-row">
                      <div class="filter-branch-line"></div>
                      <button
                        v-for="sub in kgSubSources"
                        :key="sub.id"
                        class="filter-pill filter-pill-sm"
                        :class="{ active: activeKgSources.has(sub.id) }"
                        @click="setCustom(); toggleKgSource(sub.id)"
                      >
                        {{ sub.label }} <span class="pill-count">{{ sub.count }}</span>
                      </button>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <!-- Enrichment section -->
          <div v-if="enrichmentSources.length" class="filter-section">
            <div class="filter-section-header" @click="toggleSection('enrichment')">
              <div class="filter-section-left">
                <span class="filter-section-caret" :class="{ open: openSection === 'enrichment' }">▸</span>
                <span class="filter-section-label">Enrichment</span>
              </div>
              <span class="filter-section-summary">{{ enrichmentSummary }}</span>
            </div>
            <div v-if="openSection === 'enrichment'" class="filter-section-body">
              <div class="filter-row">
                <div class="sub-tabs">
                  <button
                    v-for="src in enrichmentSources"
                    :key="src.id"
                    class="filter-pill"
                    :class="{ active: activeEnrichment.has(src.id) }"
                    @click="setCustom(); toggleEnrichment(src.id)"
                  >
                    {{ src.label }} <span class="pill-count">{{ src.count }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Relation Type section -->
          <div v-if="relationGroupOptions.length" class="filter-section">
            <div class="filter-section-header" @click="toggleSection('relation')">
              <div class="filter-section-left">
                <span class="filter-section-caret" :class="{ open: openSection === 'relation' }">▸</span>
                <span class="filter-section-label">Relation Type</span>
              </div>
              <span class="filter-section-summary">{{ relationSummary }}</span>
            </div>
            <div v-if="openSection === 'relation'" class="filter-section-body">
              <div v-for="group in relationGroupOptions" :key="group.label" class="relation-group relation-group-horiz">
                <div class="relation-group-main">
                  <button
                    class="filter-pill filter-pill-group"
                    :class="{ active: isGroupFullyActive(group), partial: isGroupPartiallyActive(group) }"
                    @click="setCustom(); toggleWholeGroup(group)"
                  >
                    {{ group.label }} <span class="pill-count">{{ group.totalCount }}</span>
                  </button>
                  <div v-if="group.subtypes.length > 0 && (isGroupFullyActive(group) || isGroupPartiallyActive(group))" class="filter-children-row">
                    <div class="filter-branch-line"></div>
                    <div class="relation-subtypes-horiz">
                      <button
                        v-for="sub in group.subtypes"
                        :key="sub.relation"
                        class="filter-pill filter-pill-sm"
                        :class="{ active: activeRelations.has(sub.relation) }"
                        @click="setCustom(); toggleRelation(sub.relation)"
                      >
                        {{ sub.label }} <span class="pill-count">{{ sub.count }}</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Selection / Groups panel -->
      <div v-if="selectionMode || groups.length > 0" class="graph-selection-panel">

        <!-- Active selection info -->
        <div v-if="selectionMode" class="graph-sel-info">
          <div class="graph-sel-count">
            <MousePointer2 :size="13" />
            <span>{{ selectedNodeIds.size }} selected</span>
            <button v-if="selectedNodeIds.size > 0" class="graph-sel-clear" @click="clearSelection">Clear</button>
          </div>
          <div class="graph-group-create">
            <input
              v-model="newGroupName"
              class="graph-group-name-input"
              placeholder="Group name…"
              @keydown.enter.prevent="createGroup"
            />
            <button
              class="graph-action-btn graph-action-btn-sm"
              :disabled="selectedNodeIds.size === 0 || !newGroupName.trim()"
              @click="createGroup"
            >
              <Plus :size="13" /> Add Group
            </button>
          </div>
        </div>

        <!-- Groups list -->
        <div v-if="groups.length > 0" class="graph-groups-list">
          <div
            v-for="grp in groups"
            :key="grp.id"
            class="graph-group-item"
            :style="{ '--grp-color': grp.color }"
          >
            <span class="graph-group-dot"></span>
            <span class="graph-group-name">{{ grp.name }}</span>
            <span class="graph-group-count">{{ grp.nodeIds.length }} genes</span>
            <button class="graph-group-action" :title="'Copy gene list: ' + grp.name" @click="copyGroupGenes(grp)">
              <Check v-if="copiedGroupId === grp.id" :size="12" />
              <Copy v-else :size="12" />
            </button>
            <button
              v-if="selectionMode"
              class="graph-group-action"
              title="Select group nodes"
              @click="selectGroup(grp)"
            >
              <MousePointer2 :size="12" />
            </button>
            <button class="graph-group-action graph-group-delete" title="Remove group" @click="removeGroup(grp.id)">
              <X :size="12" />
            </button>
          </div>
        </div>

      </div>

      <NetworkGraph
        ref="graphRef"
        :nodes="filteredNodes"
        :edges="filteredEdges"
        :selection-mode="selectionMode"
        :selected-node-ids="selectedNodeIds"
        :group-color-map="groupColorMap"
        :search-match-ids="searchMatchIds"
        @node-click="handleNodeClick"
        @node-select="handleNodeSelect"
        @lasso-select="handleLassoSelect"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick, onMounted, onUnmounted } from 'vue';
import {
  Layers, GitFork, Tags, Heart, SlidersHorizontal,
  Search, ChevronUp, ChevronDown, X, MousePointer2, Maximize2, Minimize2,
  Plus, Copy, Check,
} from 'lucide-vue-next';
import NetworkGraph from '../NetworkGraph.vue';
import { useAnalysisStore } from '../../stores/analysis';
import { useGeneDrawerStore } from '../../stores/geneDrawer';
import type { GraphEdge, GraphNode } from '../../types';

type PresetId = 'overview' | 'gene-relations' | 'bio-terms' | 'disease-context' | 'custom';
type SourceCategory = 'literature' | 'local-kg';
type SectionId = 'source' | 'enrichment' | 'relation';

/* ── Source classification ── */

function classifyEdgeSource(edge: GraphEdge): { category: SourceCategory; db: string } {
  if (edge.type === 'enrichment') return { category: 'literature', db: '' };
  const db = (edge.source_db || '').toLowerCase();
  if (db === 'reactome' || db === 'kegg' || db === 'string' || db === 'pubtator') {
    return { category: 'local-kg', db };
  }
  return { category: 'literature', db: 'llm' };
}

function classifyEnrichmentSource(edge: GraphEdge): string {
  const targetId = typeof edge.target === 'string' ? edge.target : (edge.target.id || '');
  if (targetId.startsWith('go:')) return 'go';
  if (targetId.startsWith('kegg:')) return 'kegg';
  return 'other';
}

/* ── Relation groups ── */

const RELATION_TO_GROUP: Record<string, string> = {
  activate: 'Regulation', inhibit: 'Regulation',
  upregulate: 'Regulation', downregulate: 'Regulation',
  interact: 'Interaction', catalyze: 'Interaction',
  phosphorylation: 'Interaction', binding: 'Interaction',
  associate: 'Association', predicted: 'Association', compound: 'Association',
  expression_up: 'Expression', expression_down: 'Expression',
  treat: 'Clinical', cause: 'Clinical', biomarker: 'Clinical',
  positive_correlate: 'Correlation', negative_correlate: 'Correlation',
};

const RELATION_LABELS: Record<string, string> = {
  activate: 'Activate', inhibit: 'Inhibit',
  upregulate: 'Upregulate', downregulate: 'Downregulate',
  interact: 'Interact', catalyze: 'Catalyze',
  phosphorylation: 'Phosphorylation', binding: 'Binding',
  associate: 'Associate', predicted: 'Predicted', compound: 'Compound',
  expression_up: 'Expression ↑', expression_down: 'Expression ↓',
  treat: 'Treat', cause: 'Cause', biomarker: 'Biomarker',
  positive_correlate: 'Positive', negative_correlate: 'Negative',
};

const GROUP_ORDER = ['Regulation', 'Interaction', 'Association', 'Expression', 'Clinical', 'Correlation'];

function getRelationGroup(relation: string): string {
  return RELATION_TO_GROUP[relation] || (relation ? 'Other' : 'Association');
}

/* ── Group color palette ── */

const GROUP_COLORS = [
  '#6366f1', '#f59e0b', '#10b981', '#ef4444',
  '#8b5cf6', '#06b6d4', '#f97316', '#ec4899',
];

/* ── Presets ── */

const presets: { id: PresetId; label: string; icon: typeof Layers }[] = [
  { id: 'overview', label: 'Overview', icon: Layers },
  { id: 'gene-relations', label: 'Gene Relations', icon: GitFork },
  { id: 'bio-terms', label: 'Bio Terms', icon: Tags },
  { id: 'disease-context', label: 'Disease Context', icon: Heart },
  { id: 'custom', label: 'Custom', icon: SlidersHorizontal },
];

/* ── Stores ── */

const analysis = useAnalysisStore();
const geneDrawer = useGeneDrawerStore();

/* ── Filter state ── */

const activePreset = ref<PresetId>('overview');
const openSection = ref<SectionId | null>(null);
const activeSources = ref(new Set<SourceCategory>(['literature', 'local-kg']));
const activeKgSources = ref(new Set<string>());
const activeEnrichment = ref(new Set<string>());
const activeRelations = ref(new Set<string>());
const activeNodeTypes = ref(new Set<string>());

/* ── Graph ref ── */

const graphRef = ref<InstanceType<typeof NetworkGraph> | null>(null);

/* ── Search state ── */

const searchQuery = ref('');
const searchIndex = ref(0);
const searchInputEl = ref<HTMLInputElement | null>(null);

/* ── Selection + groups state ── */

const selectionMode = ref(false);
const selectedNodeIds = ref(new Set<string>());
const newGroupName = ref('');
const copiedGroupId = ref<string | null>(null);

interface NodeGroup {
  id: string;
  name: string;
  color: string;
  nodeIds: string[];
}
const groups = ref<NodeGroup[]>([]);

/* ── Fullscreen state ── */

const isFullscreen = ref(false);

/* ── Computed data ── */

const allNodes = computed(() => analysis.result?.graph?.nodes || []);
const allEdges = computed(() => analysis.result?.graph?.edges || []);
const relationEdges = computed(() => allEdges.value.filter((e) => e.type === 'relation'));
const enrichmentEdges = computed(() => allEdges.value.filter((e) => e.type === 'enrichment'));
const inputGeneIds = computed(() =>
  new Set(allNodes.value.filter((n) => n.type === 'gene' && (n as GraphNode & { is_input?: boolean }).is_input).map(resolveNodeId)),
);

/* ── Source categories ── */

const sourceCategories = computed(() => {
  let litCount = 0, kgCount = 0;
  for (const e of relationEdges.value) {
    const { category } = classifyEdgeSource(e);
    if (category === 'literature') litCount++;
    else kgCount++;
  }
  const cats: { id: SourceCategory; label: string; count: number }[] = [];
  if (litCount) cats.push({ id: 'literature', label: 'Literature', count: litCount });
  if (kgCount) cats.push({ id: 'local-kg', label: 'Local KG', count: kgCount });
  return cats;
});

const kgSubSources = computed(() => {
  const counts: Record<string, number> = {};
  for (const e of relationEdges.value) {
    const { category, db } = classifyEdgeSource(e);
    if (category === 'local-kg' && db) counts[db] = (counts[db] || 0) + 1;
  }
  const labelMap: Record<string, string> = { reactome: 'Reactome', kegg: 'KEGG', string: 'STRING', pubtator: 'PubTator' };
  return Object.entries(counts).map(([id, count]) => ({ id, label: labelMap[id] || id, count })).sort((a, b) => b.count - a.count);
});

const enrichmentSources = computed(() => {
  const counts: Record<string, number> = {};
  for (const e of enrichmentEdges.value) {
    const src = classifyEnrichmentSource(e);
    counts[src] = (counts[src] || 0) + 1;
  }
  const labelMap: Record<string, string> = { go: 'GO Terms', kegg: 'KEGG Pathways' };
  return Object.entries(counts)
    .filter(([id]) => id !== 'other')
    .map(([id, count]) => ({ id, label: labelMap[id] || id, count }))
    .sort((a, b) => b.count - a.count);
});

/* ── Relation groups ── */

interface RelationSubtype { relation: string; label: string; count: number }
interface RelationGroupOption { label: string; subtypes: RelationSubtype[]; totalCount: number }

const relationGroupOptions = computed<RelationGroupOption[]>(() => {
  const counts: Record<string, number> = {};
  for (const e of relationEdges.value) {
    const r = e.relation || 'associate';
    counts[r] = (counts[r] || 0) + 1;
  }
  const groupMap = new Map<string, RelationSubtype[]>();
  for (const [relation, count] of Object.entries(counts)) {
    const group = getRelationGroup(relation);
    if (!groupMap.has(group)) groupMap.set(group, []);
    groupMap.get(group)!.push({ relation, label: RELATION_LABELS[relation] || relation, count });
  }
  for (const subtypes of groupMap.values()) subtypes.sort((a, b) => b.count - a.count);
  const result: RelationGroupOption[] = [];
  for (const groupLabel of GROUP_ORDER) {
    const subtypes = groupMap.get(groupLabel);
    if (subtypes?.length) result.push({ label: groupLabel, subtypes, totalCount: subtypes.reduce((s, x) => s + x.count, 0) });
  }
  const otherSubtypes = groupMap.get('Other');
  if (otherSubtypes?.length) result.push({ label: 'Other', subtypes: otherSubtypes, totalCount: otherSubtypes.reduce((s, x) => s + x.count, 0) });
  return result;
});

const allRelationTypesInData = computed(() => {
  const types = new Set<string>();
  for (const e of relationEdges.value) types.add(e.relation || 'associate');
  return types;
});

function isGroupFullyActive(group: RelationGroupOption): boolean {
  return group.subtypes.every((s) => activeRelations.value.has(s.relation));
}
function isGroupPartiallyActive(group: RelationGroupOption): boolean {
  return !isGroupFullyActive(group) && group.subtypes.some((s) => activeRelations.value.has(s.relation));
}

/* ── Summaries ── */

const sourceSummary = computed(() => {
  const parts: string[] = [];
  if (activeSources.value.has('literature')) parts.push('Literature');
  if (activeSources.value.has('local-kg')) {
    const subs = kgSubSources.value.filter((s) => activeKgSources.value.has(s.id)).map((s) => s.label);
    parts.push(subs.length ? `KG (${subs.join(', ')})` : 'Local KG');
  }
  return parts.join(' · ') || 'None';
});

const enrichmentSummary = computed(() => {
  const active = enrichmentSources.value.filter((s) => activeEnrichment.value.has(s.id));
  return active.map((s) => s.label).join(' · ') || 'None';
});

const relationSummary = computed(() => {
  const allActive = relationGroupOptions.value.every((g) => isGroupFullyActive(g));
  if (allActive) return 'All';
  const activeGroups = relationGroupOptions.value.filter((g) => isGroupFullyActive(g) || isGroupPartiallyActive(g));
  return activeGroups.map((g) => g.label).join(' · ') || 'None';
});

/* ── Filtering ── */

watch(allEdges, () => { applyPreset(activePreset.value); }, { immediate: true });

function applyPreset(id: PresetId) {
  activePreset.value = id;
  if (id === 'custom') return;

  const allKg = kgSubSources.value.map((s) => s.id);
  const allEnrich = enrichmentSources.value.map((s) => s.id);
  const allRels = Array.from(allRelationTypesInData.value);

  switch (id) {
    case 'overview':
      activeSources.value = new Set(['literature', 'local-kg']);
      activeKgSources.value = new Set(allKg);
      activeEnrichment.value = new Set(allEnrich);
      activeRelations.value = new Set(allRels);
      activeNodeTypes.value = new Set(['gene']);
      break;
    case 'gene-relations':
      activeSources.value = new Set(['literature', 'local-kg']);
      activeKgSources.value = new Set(allKg);
      activeEnrichment.value = new Set();
      activeRelations.value = new Set(allRels);
      activeNodeTypes.value = new Set(['gene', 'disease', 'drug']);
      break;
    case 'bio-terms':
      activeSources.value = new Set();
      activeKgSources.value = new Set();
      activeEnrichment.value = new Set(allEnrich);
      activeRelations.value = new Set(allRels);
      activeNodeTypes.value = new Set(['gene', 'go', 'kegg', 'pathway']);
      break;
    case 'disease-context': {
      activeSources.value = new Set(['literature', 'local-kg']);
      activeKgSources.value = new Set(allKg);
      activeEnrichment.value = new Set();
      const clinicalRels = allRels.filter((r) => {
        const g = getRelationGroup(r);
        return g === 'Clinical' || g === 'Association';
      });
      activeRelations.value = new Set(clinicalRels);
      activeNodeTypes.value = new Set(['gene', 'disease', 'drug']);
      break;
    }
  }
}

function setCustom() { activePreset.value = 'custom'; }
function toggleSection(id: SectionId) { openSection.value = openSection.value === id ? null : id; }

function toggleSetValue<T>(target: Set<T>, value: T): Set<T> {
  const next = new Set(target);
  next.has(value) ? next.delete(value) : next.add(value);
  return next;
}

function toggleSource(id: SourceCategory) { activeSources.value = toggleSetValue(activeSources.value, id); }
function toggleKgSource(id: string) { activeKgSources.value = toggleSetValue(activeKgSources.value, id); }
function toggleEnrichment(id: string) { activeEnrichment.value = toggleSetValue(activeEnrichment.value, id); }
function toggleRelation(relation: string) { activeRelations.value = toggleSetValue(activeRelations.value, relation); }

function toggleWholeGroup(group: RelationGroupOption) {
  const allActive = isGroupFullyActive(group);
  const next = new Set(activeRelations.value);
  for (const sub of group.subtypes) {
    allActive ? next.delete(sub.relation) : next.add(sub.relation);
  }
  activeRelations.value = next;
}

const filteredEdges = computed(() => {
  const allowedNodeIds = new Set(
    allNodes.value
      .filter((node) => (node.type ? activeNodeTypes.value.has(node.type) : true))
      .map(resolveNodeId),
  );

  return allEdges.value.filter((edge) => {
    if (edge.type === 'enrichment') {
      const src = classifyEnrichmentSource(edge);
      if (!activeEnrichment.value.has(src)) return false;
      const sourceId = resolveEdgeNodeId(edge.source);
      return allowedNodeIds.has(sourceId);
    } else if (edge.type === 'relation') {
      const { category, db } = classifyEdgeSource(edge);
      if (!activeSources.value.has(category)) return false;
      if (category === 'local-kg' && db && !activeKgSources.value.has(db)) return false;
      const relation = edge.relation || 'associate';
      if (!activeRelations.value.has(relation)) return false;
      const sourceId = resolveEdgeNodeId(edge.source);
      const targetId = resolveEdgeNodeId(edge.target);
      return allowedNodeIds.has(sourceId) && allowedNodeIds.has(targetId);
    }
    return false;
  });
});

const filteredNodes = computed(() => {
  const connectedIds = new Set<string>();
  const enrichmentTargetIds = new Set<string>();
  filteredEdges.value.forEach((edge) => {
    connectedIds.add(resolveEdgeNodeId(edge.source));
    connectedIds.add(resolveEdgeNodeId(edge.target));
    if (edge.type === 'enrichment') enrichmentTargetIds.add(resolveEdgeNodeId(edge.target));
  });

  return allNodes.value.filter((node) => {
    const nodeId = resolveNodeId(node);
    if (enrichmentTargetIds.has(nodeId)) return true;
    const matchesType = node.type ? activeNodeTypes.value.has(node.type) : true;
    if (!matchesType) return false;
    return connectedIds.has(nodeId) || inputGeneIds.value.has(nodeId);
  });
});

/* ── Helpers ── */

function resolveNodeId(node: GraphNode) {
  return node.id || node.label || node.name || 'node';
}
function resolveEdgeNodeId(node: GraphNode | string) {
  return typeof node === 'string' ? node : resolveNodeId(node);
}

/* ── Search ── */

const searchResults = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return [];
  return filteredNodes.value
    .filter((n) => {
      const label = (n.label || n.name || n.id || '').toLowerCase();
      return label.includes(q);
    })
    .map(resolveNodeId);
});

const searchMatchIds = computed<Set<string> | null>(() => {
  if (!searchQuery.value.trim() || searchResults.value.length === 0) return null;
  return new Set(searchResults.value);
});

watch(searchResults, (results) => {
  searchIndex.value = 0;
  if (results.length > 0) focusSearchResult(0);
});

watch(searchQuery, (q) => {
  if (!q) searchIndex.value = 0;
});

function focusSearchResult(idx: number) {
  const nodeId = searchResults.value[idx];
  if (nodeId) graphRef.value?.focusNode(nodeId);
}

function nextSearchResult() {
  if (!searchResults.value.length) return;
  searchIndex.value = (searchIndex.value + 1) % searchResults.value.length;
  focusSearchResult(searchIndex.value);
}

function prevSearchResult() {
  if (!searchResults.value.length) return;
  searchIndex.value = (searchIndex.value - 1 + searchResults.value.length) % searchResults.value.length;
  focusSearchResult(searchIndex.value);
}

function clearSearch() {
  searchQuery.value = '';
  searchIndex.value = 0;
}

/* ── Selection mode ── */

function toggleSelectionMode() {
  selectionMode.value = !selectionMode.value;
  if (!selectionMode.value) clearSelection();
}

function clearSelection() {
  selectedNodeIds.value = new Set();
}

function handleNodeClick(node: GraphNode) {
  if (node.type !== 'gene') return;
  const symbol = node.label || node.name || resolveNodeId(node).replace(/^gene:/, '');
  if (symbol) geneDrawer.openGene(symbol);
}

function handleNodeSelect(nodeId: string) {
  const next = new Set(selectedNodeIds.value);
  next.has(nodeId) ? next.delete(nodeId) : next.add(nodeId);
  selectedNodeIds.value = next;
}

function handleLassoSelect(nodeIds: string[]) {
  const next = new Set(selectedNodeIds.value);
  // Toggle: if all selected → deselect, else add all
  const allAlreadySelected = nodeIds.every((id) => next.has(id));
  for (const id of nodeIds) {
    allAlreadySelected ? next.delete(id) : next.add(id);
  }
  selectedNodeIds.value = next;
}

/* ── Groups ── */

function createGroup() {
  const name = newGroupName.value.trim();
  if (!name || selectedNodeIds.value.size === 0) return;

  const usedColors = new Set(groups.value.map((g) => g.color));
  const color = GROUP_COLORS.find((c) => !usedColors.has(c)) || GROUP_COLORS[groups.value.length % GROUP_COLORS.length];

  // Only include gene nodes in the group for export purposes
  const geneIds = Array.from(selectedNodeIds.value).filter((id) => {
    const node = filteredNodes.value.find((n) => resolveNodeId(n) === id);
    return node?.type === 'gene';
  });

  groups.value.push({
    id: `grp-${Date.now()}`,
    name,
    color,
    nodeIds: geneIds.length > 0 ? geneIds : Array.from(selectedNodeIds.value),
  });

  newGroupName.value = '';
  clearSelection();
}

function removeGroup(id: string) {
  groups.value = groups.value.filter((g) => g.id !== id);
}

function selectGroup(grp: NodeGroup) {
  selectedNodeIds.value = new Set(grp.nodeIds);
}

async function copyGroupGenes(grp: NodeGroup) {
  // Resolve gene symbols from node IDs
  const symbols = grp.nodeIds.map((id) => {
    const node = allNodes.value.find((n) => resolveNodeId(n) === id);
    return node?.label || node?.name || id.replace(/^gene:/, '');
  });
  const text = symbols.join('\n');
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
  copiedGroupId.value = grp.id;
  setTimeout(() => { copiedGroupId.value = null; }, 1500);
}

const groupColorMap = computed<Map<string, string>>(() => {
  const map = new Map<string, string>();
  for (const grp of groups.value) {
    for (const id of grp.nodeIds) map.set(id, grp.color);
  }
  return map;
});

/* ── Fullscreen ── */

function toggleFullscreen() {
  graphRef.value?.savePositions();
  isFullscreen.value = !isFullscreen.value;
  // Re-render with new container dimensions after layout
  nextTick(() => {
    setTimeout(() => {
      // Trigger resize-based re-render in the graph
      window.dispatchEvent(new Event('resize'));
    }, 50);
  });
}

function exitFullscreen() {
  if (isFullscreen.value) {
    graphRef.value?.savePositions();
    isFullscreen.value = false;
  }
}

// Close fullscreen on Escape globally
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isFullscreen.value) exitFullscreen();
}
onMounted(() => window.addEventListener('keydown', onKeydown));
onUnmounted(() => window.removeEventListener('keydown', onKeydown));
</script>
