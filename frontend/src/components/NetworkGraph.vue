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
  selectionMode?: boolean;
  selectedNodeIds?: Set<string>;
  groupColorMap?: Map<string, string>;
  searchMatchIds?: Set<string> | null;
}>();

const emit = defineEmits<{
  nodeClick: [node: GraphNode];
  nodeSelect: [nodeId: string];
  lassoSelect: [nodeIds: string[]];
}>();

const container = ref<HTMLDivElement | null>(null);

// ── Component-scope D3 state (set by render, used by helpers) ──
let simulation: d3.Simulation<SimNode, SimLink> | null = null;
let svgSel: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null;
let nodeGroupSel: d3.Selection<SVGGElement, SimNode, SVGGElement, unknown> | null = null;
let nodeCircleSel: d3.Selection<SVGCircleElement, SimNode, SVGGElement, unknown> | null = null;
let nodeTextSel: d3.Selection<SVGTextElement, SimNode, SVGGElement, unknown> | null = null;
let linkSel: d3.Selection<SVGLineElement, SimLink, SVGGElement, unknown> | null = null;
let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
let simNodes: SimNode[] = [];
let simLinks: SimLink[] = [];
let degreeCutoff = 0;
let renderWidth = 900;
let renderHeight = 520;

// Preserve positions across re-renders (e.g., fullscreen toggle)
const savedPositions = new Map<string, { x: number; y: number }>();

type SimNode = d3.SimulationNodeDatum & GraphNode & { id: string; degree: number };
type SimLink = d3.SimulationLinkDatum<SimNode> & {
  source: string | SimNode;
  target: string | SimNode;
  type?: string;
  source_db?: string;
  relation?: string;
};

function getNodeId(node: GraphNode) {
  return node.id || node.label || node.name || 'node';
}

/* ── Node visual config ── */

const nodeColor: Record<string, string> = {
  gene: '#1e293b',
  go: '#6366f1',
  kegg: '#8b5cf6',
  disease: '#ef4444',
  drug: '#f59e0b',
  pathway: '#8b5cf6',
  other: '#94a3b8',
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
  if (db === 'reactome' || db === 'kegg' || db === 'string') return '#3b82f6';
  return '#f59e0b';
}

function edgeOpacity(d: SimLink): number {
  return d.type === 'enrichment' ? 0.35 : 0.55;
}

const LABEL_TOP_N = 15;

/* ── Visual state update (no re-render) ── */

function updateNodeVisuals() {
  if (!nodeCircleSel || !nodeGroupSel || !nodeTextSel) return;

  const selected = props.selectedNodeIds || new Set<string>();
  const groupColors = props.groupColorMap || new Map<string, string>();
  const searchMatch = props.searchMatchIds;
  const inSelMode = props.selectionMode ?? false;

  nodeCircleSel
    .attr('fill', (d: SimNode) => {
      if (groupColors.has(d.id)) return groupColors.get(d.id)!;
      const isInput = (d as { is_input?: boolean }).is_input;
      return isInput ? (nodeColor[d.type || ''] || '#1e293b') : (nodeColorLight[d.type || ''] || '#cbd5e1');
    })
    .attr('stroke', (d: SimNode) => {
      if (inSelMode && selected.has(d.id)) return '#ffffff';
      if (groupColors.has(d.id)) return 'rgba(255,255,255,0.8)';
      const isInput = (d as { is_input?: boolean }).is_input;
      return isInput ? (nodeColor[d.type || ''] || '#94a3b8') : 'rgba(255,255,255,0.7)';
    })
    .attr('stroke-width', (d: SimNode) => {
      if (inSelMode && selected.has(d.id)) return 3.5;
      const isInput = (d as { is_input?: boolean }).is_input;
      return isInput ? 2 : 1;
    })
    .attr('stroke-opacity', (d: SimNode) => {
      if (inSelMode && selected.has(d.id)) return 1;
      const isInput = (d as { is_input?: boolean }).is_input;
      return isInput ? 0.6 : 1;
    });

  nodeGroupSel.classed('node-dimmed', (d: SimNode) => {
    if (searchMatch && searchMatch.size > 0 && !searchMatch.has(d.id)) return true;
    if (inSelMode && selected.size > 0 && !selected.has(d.id)) return true;
    return false;
  });
}

/* ── Lasso ── */

let lassoActive = false;
let lassoX0 = 0;
let lassoY0 = 0;
let lassoRectEl: SVGRectElement | null = null;

function enableLasso() {
  if (!svgSel) return;
  svgSel
    .on('mousedown.lasso', (event: MouseEvent) => {
      if ((event.target as Element).closest('.graph-node')) return;
      if (event.button !== 0) return;
      lassoActive = true;
      [lassoX0, lassoY0] = d3.pointer(event as unknown as d3.ClientPointEvent);
      lassoRectEl = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      lassoRectEl.setAttribute('class', 'lasso-rect');
      lassoRectEl.setAttribute('x', String(lassoX0));
      lassoRectEl.setAttribute('y', String(lassoY0));
      lassoRectEl.setAttribute('width', '0');
      lassoRectEl.setAttribute('height', '0');
      svgSel!.node()!.appendChild(lassoRectEl);
      event.stopPropagation();
    })
    .on('mousemove.lasso', (event: MouseEvent) => {
      if (!lassoActive || !lassoRectEl) return;
      const [x, y] = d3.pointer(event as unknown as d3.ClientPointEvent);
      lassoRectEl.setAttribute('x', String(Math.min(x, lassoX0)));
      lassoRectEl.setAttribute('y', String(Math.min(y, lassoY0)));
      lassoRectEl.setAttribute('width', String(Math.abs(x - lassoX0)));
      lassoRectEl.setAttribute('height', String(Math.abs(y - lassoY0)));
    })
    .on('mouseup.lasso', (event: MouseEvent) => {
      if (!lassoActive) return;
      lassoActive = false;
      const [x, y] = d3.pointer(event as unknown as d3.ClientPointEvent);
      lassoRectEl?.remove();
      lassoRectEl = null;

      const x1 = Math.min(x, lassoX0), x2 = Math.max(x, lassoX0);
      const y1 = Math.min(y, lassoY0), y2 = Math.max(y, lassoY0);
      if (Math.abs(x2 - x1) < 5 && Math.abs(y2 - y1) < 5) return;

      // Convert screen rect to graph-coordinate space using current zoom transform
      const svgNode = svgSel!.node()!;
      const t = d3.zoomTransform(svgNode);
      const [gx1, gy1] = t.invert([x1, y1]);
      const [gx2, gy2] = t.invert([x2, y2]);

      const ids = simNodes
        .filter((n) => n.x != null && n.y != null && n.x >= gx1 && n.x <= gx2 && n.y >= gy1 && n.y <= gy2)
        .map((n) => n.id);

      if (ids.length > 0) emit('lassoSelect', ids);
    });
}

function disableLasso() {
  svgSel?.on('mousedown.lasso', null).on('mousemove.lasso', null).on('mouseup.lasso', null);
  lassoRectEl?.remove();
  lassoRectEl = null;
  lassoActive = false;
}

/* ── Focus / pan to node (for search navigation) ── */

function focusNode(nodeId: string, flash = true) {
  if (!svgSel || !zoomBehavior) return;
  const node = simNodes.find((n) => n.id === nodeId);
  if (!node || node.x == null || node.y == null) return;

  const scale = 2;
  const tx = renderWidth / 2 - node.x * scale;
  const ty = renderHeight / 2 - node.y * scale;

  svgSel
    .transition()
    .duration(550)
    .ease(d3.easeCubicInOut)
    .call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));

  if (flash && nodeCircleSel) {
    nodeCircleSel
      .filter((d: SimNode) => d.id === nodeId)
      .attr('stroke', '#f59e0b')
      .attr('stroke-width', 5)
      .transition()
      .delay(700)
      .duration(500)
      .attr('stroke', (d: SimNode) => {
        const inSelMode = props.selectionMode ?? false;
        const selected = props.selectedNodeIds || new Set<string>();
        if (inSelMode && selected.has(d.id)) return '#ffffff';
        const isInput = (d as { is_input?: boolean }).is_input;
        return isInput ? (nodeColor[d.type || ''] || '#94a3b8') : 'rgba(255,255,255,0.7)';
      })
      .attr('stroke-width', (d: SimNode) => {
        const inSelMode = props.selectionMode ?? false;
        const selected = props.selectedNodeIds || new Set<string>();
        if (inSelMode && selected.has(d.id)) return 3.5;
        const isInput = (d as { is_input?: boolean }).is_input;
        return isInput ? 2 : 1;
      });
  }
}

/* ── Save / restore positions across re-renders ── */

function savePositions() {
  for (const n of simNodes) {
    if (n.x != null && n.y != null) savedPositions.set(n.id, { x: n.x, y: n.y });
  }
}

defineExpose({ focusNode, savePositions });

/* ── Render ── */

function render() {
  const element = container.value;
  if (!element) return;

  simulation?.stop();
  disableLasso();
  element.innerHTML = '';

  svgSel = null;
  nodeGroupSel = null;
  nodeCircleSel = null;
  nodeTextSel = null;
  linkSel = null;

  const width = element.clientWidth || 900;
  const height = element.clientHeight || 520;
  renderWidth = width;
  renderHeight = height;

  const svg = d3.select(element).append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    .style('cursor', 'grab');

  svgSel = svg;

  const g = svg.append('g');
  const zoom = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.3, 5])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
      const k = event.transform.k;
      nodeTextSel?.style('display', (d: SimNode) => {
        if ((d as { is_input?: boolean }).is_input) return 'block';
        if (k >= 1.5) return 'block';
        return d.degree >= degreeCutoff ? 'block' : 'none';
      });
    });
  svg.call(zoom);
  zoomBehavior = zoom;

  // Arrow markers
  const defs = svg.append('defs');
  [{ id: 'arrow-lit', fill: '#f59e0b' }, { id: 'arrow-kg', fill: '#3b82f6' }].forEach(({ id, fill }) => {
    defs.append('marker')
      .attr('id', id).attr('viewBox', '0 -4 8 8')
      .attr('refX', 20).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path').attr('d', 'M0,-3L7,0L0,3')
      .attr('fill', fill).attr('fill-opacity', 0.7);
  });

  // Glow filter
  const filterGlow = defs.append('filter')
    .attr('id', 'glow')
    .attr('x', '-30%').attr('y', '-30%')
    .attr('width', '160%').attr('height', '160%');
  filterGlow.append('feGaussianBlur').attr('stdDeviation', '2').attr('result', 'blur');
  filterGlow.append('feComposite').attr('in', 'SourceGraphic').attr('in2', 'blur').attr('operator', 'over');

  // Degree map
  const degreeMap = new Map<string, number>();
  props.edges.forEach((edge) => {
    const src = typeof edge.source === 'string' ? edge.source : getNodeId(edge.source as GraphNode);
    const tgt = typeof edge.target === 'string' ? edge.target : getNodeId(edge.target as GraphNode);
    degreeMap.set(src, (degreeMap.get(src) || 0) + 1);
    degreeMap.set(tgt, (degreeMap.get(tgt) || 0) + 1);
  });

  // Build sim nodes — restore saved positions if available
  const nodes: SimNode[] = props.nodes.map((node) => {
    const id = getNodeId(node);
    const saved = savedPositions.get(id);
    return {
      ...node,
      id,
      degree: degreeMap.get(id) || 0,
      ...(saved ? { x: saved.x, y: saved.y } : {}),
    };
  });

  const links: SimLink[] = props.edges.map((edge) => ({
    ...edge,
    source: typeof edge.source === 'string' ? edge.source : getNodeId(edge.source as GraphNode),
    target: typeof edge.target === 'string' ? edge.target : getNodeId(edge.target as GraphNode),
  }));

  simNodes = nodes;
  simLinks = links;

  const sortedDegrees = nodes.map((n) => n.degree).sort((a, b) => b - a);
  degreeCutoff = sortedDegrees[Math.min(LABEL_TOP_N, sortedDegrees.length - 1)] || 0;

  simulation = d3
    .forceSimulation<SimNode>(nodes)
    .force('link', d3.forceLink<SimNode, SimLink>(links).id((d) => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide<SimNode>().radius((d) => (typeRadius[d.type || ''] || 5) + 6))
    .stop();

  // Pre-compute layout (skip if we have saved positions)
  const hasSaved = nodes.some((n) => savedPositions.has(n.id));
  if (!hasSaved) {
    const totalIter = Math.ceil(Math.log(simulation.alphaMin()) / Math.log(1 - simulation.alphaDecay()));
    for (let i = 0; i < Math.floor(totalIter * 0.8); i++) simulation.tick();
  }
  simulation.alpha(hasSaved ? 0.05 : 0.15).restart();

  // Links
  const link = g.append('g')
    .selectAll<SVGLineElement, SimLink>('line').data(links).join('line')
    .attr('class', 'graph-link')
    .attr('stroke', edgeColor)
    .attr('stroke-opacity', edgeOpacity)
    .attr('stroke-width', (d) => d.type === 'relation' ? 1.2 : 0.8)
    .attr('stroke-dasharray', (d) => d.type === 'enrichment' ? '3,3' : 'none')
    .attr('marker-end', (d) => {
      if (d.type !== 'relation') return '';
      const db = (d.source_db || '').toLowerCase();
      return (db === 'reactome' || db === 'kegg' || db === 'string') ? 'url(#arrow-kg)' : 'url(#arrow-lit)';
    });
  linkSel = link;

  // Nodes
  const node = g.append('g')
    .selectAll<SVGGElement, SimNode>('g').data(nodes).join('g')
    .attr('class', 'graph-node')
    .style('cursor', 'pointer')
    .call(
      d3.drag<SVGGElement, SimNode>()
        .filter(() => !(props.selectionMode ?? false))
        .on('start', (e, d) => { if (!e.active) simulation?.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on('end', (e, d) => { if (!e.active) simulation?.alphaTarget(0); d.fx = null; d.fy = null; }),
    );

  const circle = node.append('circle')
    .attr('r', (d) => {
      const base = typeRadius[d.type || ''] || 5;
      return (d as { is_input?: boolean }).is_input ? base + 2 : base;
    })
    .attr('fill', (d) => {
      const isInput = (d as { is_input?: boolean }).is_input;
      return isInput ? (nodeColor[d.type || ''] || '#1e293b') : (nodeColorLight[d.type || ''] || '#cbd5e1');
    })
    .attr('stroke', (d) => {
      const isInput = (d as { is_input?: boolean }).is_input;
      return isInput ? (nodeColor[d.type || ''] || '#94a3b8') : 'rgba(255,255,255,0.7)';
    })
    .attr('stroke-width', (d) => (d as { is_input?: boolean }).is_input ? 2 : 1)
    .attr('stroke-opacity', (d) => (d as { is_input?: boolean }).is_input ? 0.6 : 1)
    .attr('filter', (d) => (d as { is_input?: boolean }).is_input ? 'url(#glow)' : null)
    .style('transition', 'transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), r 0.2s ease');

  nodeGroupSel = node;
  nodeCircleSel = circle;

  const nodeText = node.append('text')
    .text((d) => d.label || d.id)
    .attr('x', 0)
    .attr('y', (d) => -(typeRadius[d.type || ''] || 5) - 5)
    .attr('text-anchor', 'middle')
    .attr('font-size', (d) => d.type === 'gene' ? '9px' : '8px')
    .attr('font-family', 'Manrope, sans-serif')
    .attr('font-weight', (d) => (d as { is_input?: boolean }).is_input ? '700' : '500')
    .attr('fill', (d) => nodeColor[d.type || ''] || '#64748b')
    .style('pointer-events', 'none')
    .style('display', (d) => {
      if ((d as { is_input?: boolean }).is_input) return 'block';
      return d.degree >= degreeCutoff ? 'block' : 'none';
    });
  nodeTextSel = nodeText;

  // Hover highlight (only when not in selection mode)
  node
    .on('mouseover', function (_e: MouseEvent, d: SimNode) {
      if (props.selectionMode) return;
      const connected = new Set<string>([d.id]);
      links.forEach((edge) => {
        const src = typeof edge.source === 'object' ? (edge.source as SimNode).id : String(edge.source);
        const tgt = typeof edge.target === 'object' ? (edge.target as SimNode).id : String(edge.target);
        if (src === d.id) connected.add(tgt);
        if (tgt === d.id) connected.add(src);
      });
      node.classed('node-dimmed', (n) => !connected.has(n.id));
      d3.select(this).select('circle').style('transform', 'scale(1.25)');
      nodeText.style('display', (n) => connected.has(n.id) ? 'block' : 'none');
      link.classed('link-dimmed', (l) => {
        const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source;
        const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target;
        return !(src === d.id || tgt === d.id);
      });
    })
    .on('mouseout', function () {
      if (props.selectionMode) return;
      node.classed('node-dimmed', false);
      d3.select(this).select('circle').style('transform', 'scale(1)');
      link.classed('link-dimmed', false);
      nodeText.style('display', (d) => {
        if ((d as { is_input?: boolean }).is_input) return 'block';
        return d.degree >= degreeCutoff ? 'block' : 'none';
      });
    });

  // Click: select (selection mode) or open gene drawer (normal, dblclick)
  node
    .on('click', (_e: MouseEvent, d: SimNode) => {
      if (props.selectionMode) emit('nodeSelect', d.id);
    })
    .on('dblclick', (_e: MouseEvent, d: SimNode) => {
      if (props.selectionMode) return;
      _e.stopPropagation();
      emit('nodeClick', d);
    });

  // Tick
  function updatePositions() {
    link
      .attr('x1', (d) => (d.source as SimNode).x || 0)
      .attr('y1', (d) => (d.source as SimNode).y || 0)
      .attr('x2', (d) => (d.target as SimNode).x || 0)
      .attr('y2', (d) => (d.target as SimNode).y || 0);
    node.attr('transform', (d) => `translate(${d.x},${d.y})`);
  }
  updatePositions();
  simulation.on('tick', updatePositions);
  simulation.on('end', () => simulation?.stop());

  // Apply current visual state (selection / groups / search)
  updateNodeVisuals();

  // Setup lasso if already in selection mode
  if (props.selectionMode) enableLasso();

  renderLegend(element, width, height);
}

function renderLegend(container: HTMLDivElement, _width: number, _height: number) {
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
    html += `<div class="graph-legend-item"><span class="graph-legend-line" data-edge-type="${item.type}"></span><span>${item.label}</span></div>`;
  }
  html += '<div class="graph-legend-sep"></div>';
  for (const item of nodeItems) {
    html += `<div class="graph-legend-item"><span class="graph-legend-dot" data-node-type="${item.type}"></span><span>${item.label}</span></div>`;
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

// Reactively update visuals when selection/groups/search change (no re-render)
watch(
  () => [props.selectionMode, props.selectedNodeIds, props.groupColorMap, props.searchMatchIds],
  () => {
    updateNodeVisuals();
    if (props.selectionMode) enableLasso();
    else disableLasso();
  },
  { deep: true },
);

onBeforeUnmount(() => {
  if (renderTimer) clearTimeout(renderTimer);
  simulation?.stop();
  simulation = null;
  disableLasso();
});
</script>
