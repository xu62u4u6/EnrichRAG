<template>
  <div ref="container" class="graph-canvas"></div>
</template>

<script setup lang="ts">
import * as d3 from 'd3';
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { GraphEdge, GraphNode } from '../types';

const props = defineProps<{
  nodes: GraphNode[];
  edges: GraphEdge[];
}>();

const emit = defineEmits<{
  nodeClick: [node: GraphNode];
}>();

const container = ref<HTMLDivElement | null>(null);
let simulation: d3.Simulation<SimNode, SimLink> | null = null;

type SimNode = d3.SimulationNodeDatum & GraphNode & { id: string; degree: number };
type SimLink = d3.SimulationLinkDatum<SimNode> & {
  source: string | SimNode;
  target: string | SimNode;
  type?: string;
  source_db?: string;
};

function getNodeId(node: GraphNode) {
  return node.id || node.label || node.name || 'node';
}

/* ── Node visual config by type ── */

const nodeColor: Record<string, string> = {
  gene: '#1e293b',     // dark slate — primary entity
  go: '#6366f1',       // indigo — GO terms
  kegg: '#8b5cf6',     // violet — KEGG
  disease: '#ef4444',  // red — diseases
  drug: '#f59e0b',     // amber — drugs
  pathway: '#8b5cf6',  // violet — pathways
  other: '#94a3b8',    // gray
};

const nodeColorLight: Record<string, string> = {
  gene: '#475569',
  go: '#a5b4fc',
  kegg: '#c4b5fd',
  disease: '#fca5a5',
  drug: '#fcd34d',
  pathway: '#c4b5fd',
  other: '#cbd5e1',
};

const typeRadius: Record<string, number> = {
  gene: 7, go: 5, kegg: 5,
  disease: 6, drug: 6, pathway: 5, other: 4,
};

/* ── Edge visual config ── */

function edgeColor(d: SimLink): string {
  if (d.type === 'enrichment') return '#94a3b8';
  const db = (d.source_db || '').toLowerCase();
  if (db === 'reactome' || db === 'kegg' || db === 'string') return '#3b82f6'; // blue — local KG
  return '#f59e0b'; // amber — literature
}

function edgeOpacity(d: SimLink): number {
  if (d.type === 'enrichment') return 0.35;
  return 0.55;
}

/* ── Label visibility: top N by degree ── */

const LABEL_TOP_N = 15;

function render() {
  const element = container.value;
  if (!element) return;
  simulation?.stop();
  element.innerHTML = '';

  const width = element.clientWidth || 900;
  const height = 520;

  const svg = d3.select(element).append('svg')
    .attr('width', width).attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    .style('cursor', 'grab');

  const g = svg.append('g');
  const zoom = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.3, 5])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
      // Semantic zoom: show more labels when zoomed in
      const k = event.transform.k;
      nodeText.style('display', (d: SimNode) => {
        if ((d as { is_input?: boolean }).is_input) return 'block';
        if (k >= 1.5) return 'block'; // show all when zoomed in
        return d.degree >= degreeCutoff ? 'block' : 'none';
      });
    });
  svg.call(zoom);

  // Arrow markers
  const defs = svg.append('defs');
  const markerDefs = [
    { id: 'arrow-lit', fill: '#f59e0b' },
    { id: 'arrow-kg', fill: '#3b82f6' },
  ];
  markerDefs.forEach(({ id, fill }) => {
    defs.append('marker')
      .attr('id', id).attr('viewBox', '0 -4 8 8')
      .attr('refX', 20).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path').attr('d', 'M0,-3L7,0L0,3')
      .attr('fill', fill).attr('fill-opacity', 0.7);
  });

  // Compute degree for each node
  const degreeMap = new Map<string, number>();
  props.edges.forEach((edge) => {
    const src = typeof edge.source === 'string' ? edge.source : getNodeId(edge.source as GraphNode);
    const tgt = typeof edge.target === 'string' ? edge.target : getNodeId(edge.target as GraphNode);
    degreeMap.set(src, (degreeMap.get(src) || 0) + 1);
    degreeMap.set(tgt, (degreeMap.get(tgt) || 0) + 1);
  });

  const nodes: SimNode[] = props.nodes.map((node) => ({
    ...node,
    id: getNodeId(node),
    degree: degreeMap.get(getNodeId(node)) || 0,
  }));
  const links: SimLink[] = props.edges.map((edge) => ({
    ...edge,
    source: typeof edge.source === 'string' ? edge.source : getNodeId(edge.source as GraphNode),
    target: typeof edge.target === 'string' ? edge.target : getNodeId(edge.target as GraphNode),
  }));

  // Degree cutoff for label visibility
  const sortedDegrees = nodes.map((n) => n.degree).sort((a, b) => b - a);
  const degreeCutoff = sortedDegrees[Math.min(LABEL_TOP_N, sortedDegrees.length - 1)] || 0;

  simulation = d3
    .forceSimulation<SimNode>(nodes)
    .force('link', d3.forceLink<SimNode, SimLink>(links).id((d: SimNode) => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide<SimNode>().radius((d: SimNode) => (typeRadius[d.type || ''] || 5) + 6));

  const link = g.append('g')
    .selectAll('line').data(links).join('line')
    .attr('stroke', edgeColor)
    .attr('stroke-opacity', edgeOpacity)
    .attr('stroke-width', (d: SimLink) => d.type === 'relation' ? 1.2 : 0.8)
    .attr('stroke-dasharray', (d: SimLink) => d.type === 'enrichment' ? '3,3' : 'none')
    .attr('marker-end', (d: SimLink) => {
      if (d.type !== 'relation') return '';
      const db = (d.source_db || '').toLowerCase();
      return (db === 'reactome' || db === 'kegg' || db === 'string') ? 'url(#arrow-kg)' : 'url(#arrow-lit)';
    });

  const node = g.append('g')
    .selectAll<SVGGElement, SimNode>('g').data(nodes).join('g')
    .call(d3.drag<SVGGElement, SimNode>()
      .on('start', (e, d) => { if (!e.active) simulation?.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on('end', (e, d) => { if (!e.active) simulation?.alphaTarget(0); d.fx = null; d.fy = null; })
    );

  node.append('circle')
    .attr('r', (d: SimNode) => {
      const base = typeRadius[d.type || ''] || 5;
      return (d as { is_input?: boolean }).is_input ? base + 2 : base;
    })
    .attr('fill', (d: SimNode) => {
      const isInput = (d as { is_input?: boolean }).is_input;
      return isInput ? (nodeColor[d.type || ''] || '#1e293b') : (nodeColorLight[d.type || ''] || '#cbd5e1');
    })
    .attr('stroke', (d: SimNode) => nodeColor[d.type || ''] || '#94a3b8')
    .attr('stroke-width', (d: SimNode) => (d as { is_input?: boolean }).is_input ? 2 : 1)
    .attr('stroke-opacity', 0.6)
    .style('cursor', 'pointer');

  const nodeText = node.append('text')
    .text((d: SimNode) => d.label || d.id)
    .attr('x', 0)
    .attr('y', (d: SimNode) => -(typeRadius[d.type || ''] || 5) - 5)
    .attr('text-anchor', 'middle')
    .attr('font-size', (d: SimNode) => d.type === 'gene' ? '9px' : '8px')
    .attr('font-family', 'Manrope, sans-serif')
    .attr('font-weight', (d: SimNode) => (d as { is_input?: boolean }).is_input ? '700' : '500')
    .attr('fill', (d: SimNode) => nodeColor[d.type || ''] || '#64748b')
    .style('pointer-events', 'none')
    .style('display', (d: SimNode) => {
      if ((d as { is_input?: boolean }).is_input) return 'block';
      return d.degree >= degreeCutoff ? 'block' : 'none';
    });

  // Hover highlight
  node.on('mouseover', function (_e: MouseEvent, d: SimNode) {
    const connected = new Set<string>();
    connected.add(d.id);
    links.forEach(edge => {
      const src = typeof edge.source === 'object' ? (edge.source as SimNode).id : String(edge.source);
      const tgt = typeof edge.target === 'object' ? (edge.target as SimNode).id : String(edge.target);
      if (src === d.id) connected.add(tgt);
      if (tgt === d.id) connected.add(src);
    });
    node.style('opacity', (n: SimNode) => connected.has(n.id) ? 1 : 0.12);
    // Show label for hovered node and its neighbors
    nodeText.style('display', (n: SimNode) => connected.has(n.id) ? 'block' : 'none');
    link.style('opacity', (l: SimLink) => {
      const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source;
      const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target;
      return (src === d.id || tgt === d.id) ? 1 : 0.04;
    });
  }).on('mouseout', function () {
    node.style('opacity', 1);
    link.style('opacity', (d: SimLink) => edgeOpacity(d));
    // Restore label visibility
    nodeText.style('display', (d: SimNode) => {
      if ((d as { is_input?: boolean }).is_input) return 'block';
      return d.degree >= degreeCutoff ? 'block' : 'none';
    });
  });

  // Click
  node.on('click', function (_e: MouseEvent, d: SimNode) {
    emit('nodeClick', d);
  });

  simulation.on('tick', () => {
    link
      .attr('x1', (d: SimLink) => (d.source as SimNode).x || 0)
      .attr('y1', (d: SimLink) => (d.source as SimNode).y || 0)
      .attr('x2', (d: SimLink) => (d.target as SimNode).x || 0)
      .attr('y2', (d: SimLink) => (d.target as SimNode).y || 0);
    node.attr('transform', (d: SimNode) => `translate(${d.x},${d.y})`);
  });

  // ── Legend (fixed position, outside zoom group) ──
  renderLegend(element, width, height);
}

function renderLegend(container: HTMLDivElement, _width: number, _height: number) {
  // Remove old legend if re-rendering
  container.querySelector('.graph-legend')?.remove();

  const el = document.createElement('div');
  el.className = 'graph-legend';

  const edgeItems = [
    { label: 'Literature', color: '#f59e0b', dash: false },
    { label: 'Local KG', color: '#3b82f6', dash: false },
    { label: 'Enrichment', color: '#94a3b8', dash: true },
  ];

  const nodeItems = [
    { label: 'Gene', color: '#1e293b' },
    { label: 'Disease', color: '#ef4444' },
    { label: 'Drug', color: '#f59e0b' },
    { label: 'GO/KEGG', color: '#6366f1' },
  ];

  let html = '';
  for (const item of edgeItems) {
    const style = item.dash
      ? `border-top: 2px dashed ${item.color}`
      : `border-top: 2px solid ${item.color}`;
    html += `<div class="graph-legend-item">
      <span class="graph-legend-line" style="${style}"></span>
      <span>${item.label}</span>
    </div>`;
  }
  html += '<div class="graph-legend-sep"></div>';
  for (const item of nodeItems) {
    html += `<div class="graph-legend-item">
      <span class="graph-legend-dot" style="background:${item.color}"></span>
      <span>${item.label}</span>
    </div>`;
  }

  el.innerHTML = html;
  container.appendChild(el);
}

onMounted(render);
watch(() => [props.nodes, props.edges], render, { deep: true });
onBeforeUnmount(() => {
  simulation?.stop();
  simulation = null;
});
</script>
