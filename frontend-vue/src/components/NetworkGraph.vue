<template>
  <div ref="container" class="graph-canvas"></div>
</template>

<script setup lang="ts">
import * as d3 from 'd3';
import { onMounted, ref, watch } from 'vue';
import type { GraphEdge, GraphNode } from '../types';

const props = defineProps<{
  nodes: GraphNode[];
  edges: GraphEdge[];
}>();

const emit = defineEmits<{
  nodeClick: [symbol: string];
}>();

const container = ref<HTMLDivElement | null>(null);

type SimNode = d3.SimulationNodeDatum & GraphNode & { id: string };
type SimLink = d3.SimulationLinkDatum<SimNode> & {
  source: string | SimNode;
  target: string | SimNode;
  type?: string;
};

function getNodeId(node: GraphNode) {
  return node.id || node.label || node.name || 'node';
}

const typeColor: Record<string, string> = {
  gene: '#344054', go: '#667085', kegg: '#667085',
  disease: '#98a2b3', drug: '#98a2b3', pathway: '#667085', other: '#d0d5dd',
};

const typeRadius: Record<string, number> = {
  gene: 7, go: 5, kegg: 5,
  disease: 6, drug: 6, pathway: 5, other: 4,
};

function render() {
  const element = container.value;
  if (!element) return;
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
    .on('zoom', (event) => { g.attr('transform', event.transform); });
  svg.call(zoom);

  // Arrow markers
  const defs = svg.append('defs');
  ['relation', 'enrichment'].forEach(t => {
    defs.append('marker')
      .attr('id', 'arrow-' + t).attr('viewBox', '0 -4 8 8')
      .attr('refX', 20).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path').attr('d', 'M0,-3L7,0L0,3')
      .attr('fill', t === 'relation' ? '#98a2b3' : '#d0d5dd');
  });

  const nodes: SimNode[] = props.nodes.map((node) => ({ ...node, id: getNodeId(node) }));
  const links: SimLink[] = props.edges.map((edge) => ({
    ...edge,
    source: typeof edge.source === 'string' ? edge.source : getNodeId(edge.source as GraphNode),
    target: typeof edge.target === 'string' ? edge.target : getNodeId(edge.target as GraphNode),
  }));

  const simulation = d3
    .forceSimulation<SimNode>(nodes)
    .force('link', d3.forceLink<SimNode, SimLink>(links).id((d: SimNode) => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide<SimNode>().radius((d: SimNode) => (typeRadius[d.type || ''] || 5) + 6));

  const link = g.append('g')
    .selectAll('line').data(links).join('line')
    .attr('stroke', (d: SimLink) => d.type === 'relation' ? '#98a2b3' : '#e4e7ec')
    .attr('stroke-width', (d: SimLink) => d.type === 'relation' ? 1.2 : 0.8)
    .attr('stroke-dasharray', (d: SimLink) => d.type === 'enrichment' ? '3,3' : 'none')
    .attr('marker-end', (d: SimLink) => d.type === 'relation' ? 'url(#arrow-relation)' : '');

  const node = g.append('g')
    .selectAll<SVGGElement, SimNode>('g').data(nodes).join('g')
    .call(d3.drag<SVGGElement, SimNode>()
      .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on('end', (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
    );

  node.append('circle')
    .attr('r', (d: SimNode) => (d as { is_input?: boolean }).is_input ? (typeRadius[d.type || ''] || 5) + 2 : (typeRadius[d.type || ''] || 5))
    .attr('fill', (d: SimNode) => (d as { is_input?: boolean }).is_input ? '#101828' : (typeColor[d.type || ''] || '#d0d5dd'))
    .attr('stroke', (d: SimNode) => (d as { is_input?: boolean }).is_input ? '#101828' : '#e4e7ec')
    .attr('stroke-width', (d: SimNode) => (d as { is_input?: boolean }).is_input ? 2 : 1)
    .style('cursor', 'pointer');

  node.append('text')
    .text((d: SimNode) => d.label || d.id)
    .attr('x', 0)
    .attr('y', (d: SimNode) => -(typeRadius[d.type || ''] || 5) - 5)
    .attr('text-anchor', 'middle')
    .attr('font-size', (d: SimNode) => d.type === 'gene' ? '9px' : '8px')
    .attr('font-family', 'Manrope, sans-serif')
    .attr('font-weight', (d: SimNode) => (d as { is_input?: boolean }).is_input ? '700' : '500')
    .attr('fill', (d: SimNode) => (d as { is_input?: boolean }).is_input ? '#101828' : '#98a2b3')
    .style('pointer-events', 'none');

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
    node.style('opacity', (n: SimNode) => connected.has(n.id) ? 1 : 0.15);
    link.style('opacity', (l: SimLink) => {
      const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source;
      const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target;
      return (src === d.id || tgt === d.id) ? 1 : 0.06;
    });
  }).on('mouseout', function () {
    node.style('opacity', 1);
    link.style('opacity', 1);
  });

  // Click
  node.on('click', function (_e: MouseEvent, d: SimNode) {
    emit('nodeClick', d.id);
  });

  simulation.on('tick', () => {
    link
      .attr('x1', (d: SimLink) => (d.source as SimNode).x || 0)
      .attr('y1', (d: SimLink) => (d.source as SimNode).y || 0)
      .attr('x2', (d: SimLink) => (d.target as SimNode).x || 0)
      .attr('y2', (d: SimLink) => (d.target as SimNode).y || 0);
    node.attr('transform', (d: SimNode) => `translate(${d.x},${d.y})`);
  });
}

onMounted(render);
watch(() => [props.nodes, props.edges], render, { deep: true });
</script>
