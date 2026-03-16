<template>
  <div class="table-card network-tab-card">
    <div v-if="!allNodes.length" class="state-card state-card-compact">
      <h3>No network data</h3>
      <p>No network data yet — a partial graph will appear after local KG lookup.</p>
    </div>
    <template v-else>
      <div class="network-tab-controls">
        <!-- Segmented control presets -->
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

        <!-- Advanced filters toggle -->
        <button class="advanced-filters-toggle" @click="showAdvanced = !showAdvanced">
          {{ showAdvanced ? 'Hide' : 'Show' }} Advanced Filters
          <span class="filter-section-caret" :class="{ open: showAdvanced }">▸</span>
        </button>

        <!-- Accordion filters -->
        <div v-show="showAdvanced" class="filter-accordion">
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
                    class="filter-chip"
                    :class="{ active: activeSources.has(src.id) }"
                    @click="setCustom(); toggleSource(src.id)"
                  >
                    <span class="chip-check" />{{ src.label }} {{ src.count }}
                  </button>
                </div>
              </div>
              <div v-if="activeSources.has('local-kg') && kgSubSources.length > 1" class="filter-row" style="padding-left: 0.6rem;">
                <span class="filter-row-label">DB</span>
                <div class="sub-tabs">
                  <button
                    v-for="sub in kgSubSources"
                    :key="sub.id"
                    class="filter-chip"
                    :class="{ active: activeKgSources.has(sub.id) }"
                    @click="setCustom(); toggleKgSource(sub.id)"
                  >
                    <span class="chip-check" />{{ sub.label }} {{ sub.count }}
                  </button>
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
                    class="filter-chip"
                    :class="{ active: activeEnrichment.has(src.id) }"
                    @click="setCustom(); toggleEnrichment(src.id)"
                  >
                    <span class="chip-check" />{{ src.label }} {{ src.count }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Relation Type section — hierarchical -->
          <div v-if="relationGroupOptions.length" class="filter-section">
            <div class="filter-section-header" @click="toggleSection('relation')">
              <div class="filter-section-left">
                <span class="filter-section-caret" :class="{ open: openSection === 'relation' }">▸</span>
                <span class="filter-section-label">Relation Type</span>
              </div>
              <span class="filter-section-summary">{{ relationSummary }}</span>
            </div>
            <div v-if="openSection === 'relation'" class="filter-section-body">
              <div v-for="group in relationGroupOptions" :key="group.label" class="relation-group">
                <div class="relation-group-header">
                  <button
                    class="filter-chip"
                    :class="{ active: isGroupFullyActive(group), partial: isGroupPartiallyActive(group) }"
                    @click="setCustom(); toggleWholeGroup(group)"
                  >
                    <span class="chip-check" />{{ group.label }} {{ group.totalCount }}
                  </button>
                  <button
                    v-if="group.subtypes.length > 1"
                    class="relation-expand-btn"
                    @click="toggleExpandedGroup(group.label)"
                  >
                    <span class="filter-section-caret" :class="{ open: expandedGroups.has(group.label) }">▸</span>
                  </button>
                </div>
                <div v-if="expandedGroups.has(group.label)" class="relation-subtypes">
                  <button
                    v-for="sub in group.subtypes"
                    :key="sub.relation"
                    class="filter-chip filter-chip-sm"
                    :class="{ active: activeRelations.has(sub.relation) }"
                    @click="setCustom(); toggleRelation(sub.relation)"
                  >
                    <span class="chip-check" />{{ sub.label }} {{ sub.count }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Status bar -->
        <div class="graph-status-bar source-meta-badge">
          {{ presetLabel }} · {{ filteredNodes.length }} nodes · {{ filteredEdges.length }} edges
          <button class="reset-btn" @click="applyPreset(activePreset)">Reset</button>
        </div>
      </div>

      <NetworkGraph :nodes="filteredNodes" :edges="filteredEdges" @node-click="handleNodeClick" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Layers, GitFork, Tags, Heart, SlidersHorizontal } from 'lucide-vue-next';
import NetworkGraph from '../NetworkGraph.vue';
import { useAnalysisStore } from '../../stores/analysis';
import { useGeneDrawerStore } from '../../stores/geneDrawer';
import type { GraphEdge, GraphNode } from '../../types';

type PresetId = 'overview' | 'gene-relations' | 'bio-terms' | 'disease-context' | 'custom';
type SourceCategory = 'literature' | 'local-kg';
type SectionId = 'source' | 'enrichment' | 'relation';

/* ── Source classification ── */

function classifyEdgeSource(edge: GraphEdge): { category: SourceCategory; db: string } {
  if (edge.type === 'enrichment') {
    return { category: 'literature', db: '' };
  }
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

/* ── Relation group mapping (mirrors backend relation_taxonomy.py) ── */

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

// Desired display order
const GROUP_ORDER = ['Regulation', 'Interaction', 'Association', 'Expression', 'Clinical', 'Correlation'];

function getRelationGroup(relation: string): string {
  return RELATION_TO_GROUP[relation] || (relation ? 'Other' : 'Association');
}

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

/* ── State ── */

const activePreset = ref<PresetId>('overview');
const showAdvanced = ref(false);
const openSection = ref<SectionId | null>(null);
const expandedGroups = ref(new Set<string>());

// Source filters
const activeSources = ref(new Set<SourceCategory>(['literature', 'local-kg']));
const activeKgSources = ref(new Set<string>());
const activeEnrichment = ref(new Set<string>());
// Relation filters — now tracks individual relations, not groups
const activeRelations = ref(new Set<string>());
const activeNodeTypes = ref(new Set<string>());

/* ── Computed data ── */

const allNodes = computed(() => analysis.result?.graph?.nodes || []);
const allEdges = computed(() => analysis.result?.graph?.edges || []);

const relationEdges = computed(() => allEdges.value.filter((e) => e.type === 'relation'));
const enrichmentEdges = computed(() => allEdges.value.filter((e) => e.type === 'enrichment'));

const inputGeneIds = computed(() =>
  new Set(allNodes.value.filter((n) => n.type === 'gene' && (n as GraphNode & { is_input?: boolean }).is_input).map(resolveNodeId)),
);

/* ── Source categories with counts ── */

const sourceCategories = computed(() => {
  let litCount = 0;
  let kgCount = 0;
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
    if (category === 'local-kg' && db) {
      counts[db] = (counts[db] || 0) + 1;
    }
  }
  const labelMap: Record<string, string> = { reactome: 'Reactome', kegg: 'KEGG', string: 'STRING', pubtator: 'PubTator' };
  return Object.entries(counts)
    .map(([id, count]) => ({ id, label: labelMap[id] || id, count }))
    .sort((a, b) => b.count - a.count);
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

/* ── Relation groups — hierarchical with counts ── */

interface RelationSubtype {
  relation: string;
  label: string;
  count: number;
}

interface RelationGroupOption {
  label: string;
  subtypes: RelationSubtype[];
  totalCount: number;
}

const relationGroupOptions = computed<RelationGroupOption[]>(() => {
  // Count each relation type
  const counts: Record<string, number> = {};
  for (const e of relationEdges.value) {
    const r = e.relation || 'associate';
    counts[r] = (counts[r] || 0) + 1;
  }

  // Group by relation_group
  const groupMap = new Map<string, RelationSubtype[]>();
  for (const [relation, count] of Object.entries(counts)) {
    const group = getRelationGroup(relation);
    if (!groupMap.has(group)) groupMap.set(group, []);
    groupMap.get(group)!.push({
      relation,
      label: RELATION_LABELS[relation] || relation,
      count,
    });
  }

  // Sort subtypes by count within each group
  for (const subtypes of groupMap.values()) {
    subtypes.sort((a, b) => b.count - a.count);
  }

  // Return in display order
  const result: RelationGroupOption[] = [];
  for (const groupLabel of GROUP_ORDER) {
    const subtypes = groupMap.get(groupLabel);
    if (subtypes?.length) {
      result.push({
        label: groupLabel,
        subtypes,
        totalCount: subtypes.reduce((sum, s) => sum + s.count, 0),
      });
    }
  }
  // Add "Other" if any
  const otherSubtypes = groupMap.get('Other');
  if (otherSubtypes?.length) {
    result.push({
      label: 'Other',
      subtypes: otherSubtypes,
      totalCount: otherSubtypes.reduce((sum, s) => sum + s.count, 0),
    });
  }
  return result;
});

const allRelationTypesInData = computed(() => {
  const types = new Set<string>();
  for (const e of relationEdges.value) {
    types.add(e.relation || 'associate');
  }
  return types;
});

const allNodeTypes = computed(() =>
  Array.from(new Set(allNodes.value.map((n) => n.type).filter((v): v is string => Boolean(v)))).sort(),
);

/* ── Group active state helpers ── */

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

const presetLabel = computed(() => presets.find((p) => p.id === activePreset.value)?.label || 'Custom');

/* ── Initialize filters when data arrives ── */

watch(allEdges, () => { applyPreset(activePreset.value); }, { immediate: true });

/* ── Preset application ── */

function applyPreset(id: PresetId) {
  activePreset.value = id;

  if (id === 'custom') {
    return;
  }

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
      // Only clinical + association relations
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

function setCustom() {
  activePreset.value = 'custom';
  showAdvanced.value = true;
}

/* ── Section accordion ── */

function toggleSection(id: SectionId) {
  openSection.value = openSection.value === id ? null : id;
}

/* ── Toggle helpers ── */

function toggleSetValue<T>(target: Set<T>, value: T): Set<T> {
  const next = new Set(target);
  next.has(value) ? next.delete(value) : next.add(value);
  return next;
}

function toggleSource(id: SourceCategory) {
  activeSources.value = toggleSetValue(activeSources.value, id);
}

function toggleKgSource(id: string) {
  activeKgSources.value = toggleSetValue(activeKgSources.value, id);
}

function toggleEnrichment(id: string) {
  activeEnrichment.value = toggleSetValue(activeEnrichment.value, id);
}

function toggleRelation(relation: string) {
  activeRelations.value = toggleSetValue(activeRelations.value, relation);
}

function toggleWholeGroup(group: RelationGroupOption) {
  const allActive = isGroupFullyActive(group);
  const next = new Set(activeRelations.value);
  for (const sub of group.subtypes) {
    if (allActive) {
      next.delete(sub.relation);
    } else {
      next.add(sub.relation);
    }
  }
  activeRelations.value = next;
}

function toggleExpandedGroup(label: string) {
  expandedGroups.value = toggleSetValue(expandedGroups.value, label);
}

/* ── Filtering ── */

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
    } else if (edge.type === 'relation') {
      const { category, db } = classifyEdgeSource(edge);
      if (!activeSources.value.has(category)) return false;
      if (category === 'local-kg' && db && !activeKgSources.value.has(db)) return false;

      // Check individual relation
      const relation = edge.relation || 'associate';
      if (!activeRelations.value.has(relation)) return false;
    } else {
      return false;
    }

    const sourceId = resolveEdgeNodeId(edge.source);
    const targetId = resolveEdgeNodeId(edge.target);
    return allowedNodeIds.has(sourceId) && allowedNodeIds.has(targetId);
  });
});

const filteredNodes = computed(() => {
  const connectedIds = new Set<string>();
  filteredEdges.value.forEach((edge) => {
    connectedIds.add(resolveEdgeNodeId(edge.source));
    connectedIds.add(resolveEdgeNodeId(edge.target));
  });

  return allNodes.value.filter((node) => {
    const nodeId = resolveNodeId(node);
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

function handleNodeClick(node: GraphNode) {
  if (node.type !== 'gene') return;
  const symbol = node.label || node.name || resolveNodeId(node).replace(/^gene:/, '');
  if (symbol) geneDrawer.openGene(symbol);
}
</script>
