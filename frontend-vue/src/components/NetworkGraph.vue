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
};

function getNodeId(node: GraphNode) {
  return node.id || node.label || node.name || 'node';
}

function render() {
  const element = container.value;
  if (!element) return;
  element.innerHTML = '';

  const width = element.clientWidth || 800;
  const height = 420;
  const svg = d3.select(element).append('svg').attr('viewBox', `0 0 ${width} ${height}`);
  const nodes: SimNode[] = props.nodes.map((node) => ({ ...node, id: getNodeId(node) }));
  const links: SimLink[] = props.edges.map((edge) => ({
    ...edge,
    source: typeof edge.source === 'string' ? edge.source : getNodeId(edge.source),
    target: typeof edge.target === 'string' ? edge.target : getNodeId(edge.target),
  }));

  const simulation = d3
    .forceSimulation<SimNode>(nodes)
    .force('link', d3.forceLink<SimNode, SimLink>(links).id((d: SimNode) => d.id).distance(90))
    .force('charge', d3.forceManyBody().strength(-180))
    .force('center', d3.forceCenter(width / 2, height / 2));

  const link = svg
    .append('g')
    .selectAll('line')
    .data(links)
    .enter()
    .append('line')
    .attr('stroke', 'rgba(245, 239, 224, 0.16)');

  const node = svg
    .append('g')
    .selectAll('circle')
    .data(nodes)
    .enter()
    .append('circle')
    .attr('r', 8)
    .attr('fill', '#ff8f5c')
    .attr('stroke', '#1d1a17')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .on('click', (_event: MouseEvent, datum: SimNode) => emit('nodeClick', getNodeId(datum)));

  const label = svg
    .append('g')
    .selectAll('text')
    .data(nodes)
    .enter()
    .append('text')
    .text((datum: SimNode) => getNodeId(datum))
    .attr('fill', '#f5efe0')
    .attr('font-size', 11)
    .attr('font-family', 'IBM Plex Sans, sans-serif');

  simulation.on('tick', () => {
    link
      .attr('x1', (datum: SimLink) => (datum.source as SimNode).x || 0)
      .attr('y1', (datum: SimLink) => (datum.source as SimNode).y || 0)
      .attr('x2', (datum: SimLink) => (datum.target as SimNode).x || 0)
      .attr('y2', (datum: SimLink) => (datum.target as SimNode).y || 0);

    node.attr('cx', (datum: SimNode) => datum.x || 0).attr('cy', (datum: SimNode) => datum.y || 0);
    label.attr('x', (datum: SimNode) => (datum.x || 0) + 10).attr('y', (datum: SimNode) => (datum.y || 0) + 4);
  });
}

onMounted(render);
watch(() => [props.nodes, props.edges], render, { deep: true });
</script>
