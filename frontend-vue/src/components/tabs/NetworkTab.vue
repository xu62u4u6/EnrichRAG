<template>
  <div class="table-card network-tab-card">
    <div v-if="!allNodes.length" class="state-card state-card-compact">
      <h3>No network data</h3>
      <p>The relation network is generated after extraction completes.</p>
    </div>
    <template v-else>
      <div class="network-tab-controls">
        <div class="sub-tabs">
          <button
            v-for="type in edgeTypeOptions"
            :key="type.id"
            class="sub-tab-btn"
            :class="{ active: edgeTypes.has(type.id) }"
            @click="toggleEdgeType(type.id)"
          >
            {{ type.label }} {{ type.count }}
          </button>
        </div>

        <div v-if="edgeTypes.has('relation') && relationTypeOptions.length" class="sub-tabs">
          <button
            v-for="relationType in relationTypeOptions"
            :key="relationType"
            class="sub-tab-btn"
            :class="{ active: relationTypes.has(relationType) }"
            @click="toggleRelationType(relationType)"
          >
            {{ relationType }}
          </button>
        </div>

        <div v-if="nodeTypeOptions.length > 1" class="sub-tabs">
          <button
            v-for="nodeType in nodeTypeOptions"
            :key="nodeType"
            class="sub-tab-btn"
            :class="{ active: nodeTypes.has(nodeType) }"
            @click="toggleNodeType(nodeType)"
          >
            {{ nodeType }}
          </button>
        </div>

        <div class="graph-stats source-meta-badge">
          {{ filteredNodes.length }} nodes · {{ filteredEdges.length }} edges
        </div>
      </div>

      <NetworkGraph :nodes="filteredNodes" :edges="filteredEdges" @node-click="handleNodeClick" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import NetworkGraph from '../NetworkGraph.vue';
import { useAnalysisStore } from '../../stores/analysis';
import { useGeneDrawerStore } from '../../stores/geneDrawer';
import type { GraphEdge, GraphNode } from '../../types';

type EdgeTypeFilter = 'relation' | 'enrichment';

const analysis = useAnalysisStore();
const geneDrawer = useGeneDrawerStore();

const edgeTypes = ref(new Set<EdgeTypeFilter>(['relation', 'enrichment']));
const relationTypes = ref(new Set<string>());
const nodeTypes = ref(new Set<string>());

const allNodes = computed(() => analysis.result?.graph?.nodes || []);
const allEdges = computed(() => analysis.result?.graph?.edges || []);
const relationEdges = computed(() => allEdges.value.filter((edge) => edge.type === 'relation'));
const edgeTypeOptions = computed(() => [
  { id: 'relation' as const, label: 'Relations', count: relationEdges.value.length },
  { id: 'enrichment' as const, label: 'Enrichment', count: allEdges.value.filter((edge) => edge.type === 'enrichment').length },
]);
const relationTypeOptions = computed(() =>
  Array.from(new Set(relationEdges.value.map((edge) => edge.relation).filter((value): value is string => Boolean(value)))).sort(),
);
const nodeTypeOptions = computed(() =>
  Array.from(new Set(allNodes.value.map((node) => node.type).filter((value): value is string => Boolean(value)))).sort(),
);
const inputGeneIds = computed(() =>
  new Set(allNodes.value.filter((node) => node.type === 'gene' && (node as GraphNode & { is_input?: boolean }).is_input).map(resolveNodeId)),
);

watch(
  relationTypeOptions,
  (types) => {
    relationTypes.value = new Set(types);
  },
  { immediate: true },
);

watch(
  nodeTypeOptions,
  (types) => {
    nodeTypes.value = new Set(types);
  },
  { immediate: true },
);

const filteredEdges = computed(() => {
  const allowedNodeIds = new Set(
    allNodes.value
      .filter((node) => node.type ? nodeTypes.value.has(node.type) : true)
      .map(resolveNodeId),
  );

  return allEdges.value.filter((edge) => {
    const edgeType = edge.type as EdgeTypeFilter | undefined;
    if (!edgeType || !edgeTypes.value.has(edgeType)) return false;
    if (edgeType === 'relation' && edge.relation && !relationTypes.value.has(edge.relation)) return false;

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
    const matchesType = node.type ? nodeTypes.value.has(node.type) : true;
    if (!matchesType) return false;
    return connectedIds.has(nodeId) || inputGeneIds.value.has(nodeId);
  });
});

function resolveNodeId(node: GraphNode) {
  return node.id || node.label || node.name || 'node';
}

function resolveEdgeNodeId(node: GraphNode | string) {
  return typeof node === 'string' ? node : resolveNodeId(node);
}

function toggleValue<T>(target: Set<T>, value: T) {
  const next = new Set(target);
  if (next.has(value)) {
    next.delete(value);
  } else {
    next.add(value);
  }
  return next;
}

function toggleEdgeType(value: EdgeTypeFilter) {
  edgeTypes.value = toggleValue(edgeTypes.value, value);
}

function toggleRelationType(value: string) {
  relationTypes.value = toggleValue(relationTypes.value, value);
}

function toggleNodeType(value: string) {
  nodeTypes.value = toggleValue(nodeTypes.value, value);
}

function handleNodeClick(node: GraphNode) {
  if (node.type !== 'gene') return;
  const symbol = node.label || node.name || resolveNodeId(node).replace(/^gene:/, '');
  if (symbol) {
    geneDrawer.openGene(symbol);
  }
}
</script>
