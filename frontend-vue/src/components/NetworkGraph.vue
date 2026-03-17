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

  // Add filters for drop shadows and glow
  const filterGlow = defs.append('filter')
    .attr('id', 'glow')
    .attr('x', '-20%').attr('y', '-20%')
    .attr('width', '140%').attr('height', '140%');
  filterGlow.append('feGaussianBlur')
    .attr('stdDeviation', '2.5')
    .attr('result', 'blur');
  filterGlow.append('feComposite')
    .attr('in', 'SourceGraphic')
    .attr('in2', 'blur')
    .attr('operator', 'over');
    
  const filterShadow = defs.append('filter')
    .attr('id', 'drop-shadow')
    .attr('x', '-20%').attr('y', '-20%')
    .attr('width', '140%').attr('height', '140%');
  filterShadow.append('feDropShadow')
    .attr('dx', '0')
    .attr('dy', '2')
    .attr('stdDeviation', '1.5')
    .attr('flood-color', '#000000')
    .attr('flood-opacity', '0.15');

  simulation = d3
    .forceSimulation<SimNode>(nodes)
    .force('link', d3.forceLink<SimNode, SimLink>(links).id((d: SimNode) => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide<SimNode>().radius((d: SimNode) => (typeRadius[d.type || ''] || 5) + 6))
    .stop();

  // Pre-compute ~80% of layout, leave the rest for a smooth settle animation
  const totalIterations = Math.ceil(Math.log(simulation.alphaMin()) / Math.log(1 - simulation.alphaDecay()));
  const precompute = Math.floor(totalIterations * 0.8);
  for (let i = 0; i < precompute; i++) simulation.tick();
  simulation.alpha(0.15).restart();

  const link = g.append('g')
    .selectAll('line').data(links).join('line')
    .attr('class', 'graph-link')
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
    .attr('class', 'graph-node')
    .style('cursor', 'pointer')
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
    .attr('stroke', (d: SimNode) => {
      const isInput = (d as { is_input?: boolean }).is_input;
      // Use slightly transparent white/light stroke for inner bevel effect on non-inputs
      return isInput ? (nodeColor[d.type || ''] || '#94a3b8') : 'rgba(255,255,255,0.7)';
    })
    .attr('stroke-width', (d: SimNode) => (d as { is_input?: boolean }).is_input ? 2 : 1)
    .attr('stroke-opacity', (d: SimNode) => (d as { is_input?: boolean }).is_input ? 0.6 : 1)
    .attr('filter', (d: SimNode) => (d as { is_input?: boolean }).is_input ? 'url(#glow)' : 'url(#drop-shadow)')
    .style('transition', 'transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), r 0.2s ease');

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
    
    // Smooth transition for nodes
    node.classed('node-dimmed', (n: SimNode) => !connected.has(n.id));
    d3.select(this).select('circle').style('transform', 'scale(1.25)');
    
    // Show label for hovered node and its neighbors
    nodeText.style('display', (n: SimNode) => connected.has(n.id) ? 'block' : 'none');
    
    // Smooth transition for links
    link.classed('link-dimmed', (l: SimLink) => {
      const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source;
      const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target;
      return !(src === d.id || tgt === d.id);
    });
  }).on('mouseout', function () {
    node.classed('node-dimmed', false);
    d3.select(this).select('circle').style('transform', 'scale(1)');
    link.classed('link-dimmed', false);
    
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

  // Apply pre-computed positions
  function updatePositions() {
    link
      .attr('x1', (d: SimLink) => (d.source as SimNode).x || 0)
      .attr('y1', (d: SimLink) => (d.source as SimNode).y || 0)
      .attr('x2', (d: SimLink) => (d.target as SimNode).x || 0)
      .attr('y2', (d: SimLink) => (d.target as SimNode).y || 0);
    node.attr('transform', (d: SimNode) => `translate(${d.x},${d.y})`);
  }
  updatePositions();

  // Only animate on drag interactions
  simulation.on('tick', updatePositions);

  // ── Legend (fixed position, outside zoom group) ──
  renderLegend(element, width, height);
}

function renderLegend(container: HTMLDivElement, _width: number, _height: number) {
  // Remove old legend if re-rendering
  container.querySelector('.graph-legend')?.remove();

  const el = document.createElement('div');
  el.className = 'graph-legend';

  const edgeItems = [
    { label: 'Literature', type: 'literature' },
    { label: 'Local KG', type: 'local-kg' },
    { label: 'Enrichment', type: 'enrichment' },
  ];

  const nodeItems = [
    { label: 'Gene', type: 'gene' },
    { label: 'Disease', type: 'disease' },
    { label: 'Drug', type: 'drug' },
    { label: 'GO/KEGG', type: 'go-kegg' },
  ];

  let html = '';
  for (const item of edgeItems) {
    html += `<div class="graph-legend-item">
      <span class="graph-legend-line" data-edge-type="${item.type}"></span>
      <span>${item.label}</span>
    </div>`;
  }
  html += '<div class="graph-legend-sep"></div>';
  for (const item of nodeItems) {
    html += `<div class="graph-legend-item">
      <span class="graph-legend-dot" data-node-type="${item.type}"></span>
      <span>${item.label}</span>
    </div>`;
  }

  el.innerHTML = html;
  container.appendChild(el);
}

onMounted(render);

let renderTimer: ReturnType<typeof setTimeout> | null = null;
let lastFingerprint = '';

watch(
  () => {
    const nIds = props.nodes.map((n) => getNodeId(n)).sort().join(',');
    const eIds = props.edges.map((e) => {
      const s = typeof e.source === 'string' ? e.source : getNodeId(e.source as GraphNode);
      const t = typeof e.target === 'string' ? e.target : getNodeId(e.target as GraphNode);
      return `${s}-${t}`;
    }).sort().join(',');
    return `${nIds}|${eIds}`;
  },
  (fingerprint) => {
    if (fingerprint === lastFingerprint) return;
    lastFingerprint = fingerprint;
    if (renderTimer) clearTimeout(renderTimer);
    renderTimer = setTimeout(() => {
      renderTimer = null;
      requestAnimationFrame(render);
    }, 200);
  },
);

onBeforeUnmount(() => {
  if (renderTimer) clearTimeout(renderTimer);
  simulation?.stop();
  simulation = null;
});
</script>
