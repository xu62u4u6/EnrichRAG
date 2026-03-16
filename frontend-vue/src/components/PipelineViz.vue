<template>
  <div class="pipeline-tab-wrap">
    <div class="loading-header">
      <h3>Pipeline Execution</h3>
      <p>{{ analysis.running ? 'Running pipeline...' : analysis.status === 'done' ? 'Pipeline complete' : 'Waiting to start' }}</p>
    </div>
    <div class="pipeline-canvas">
      <svg class="pipeline-desktop-map" viewBox="0 0 1020 280" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0">
        <path :class="['pipe-line', lineStates['line-0-1']]" d="M 75 140 L 210 140" fill="none" />
        <path :class="['pipe-line', lineStates['line-1-2a']]" d="M 210 140 C 300 140, 300 65, 390 65" fill="none" />
        <path :class="['pipe-line', lineStates['line-1-2b']]" d="M 210 140 C 300 140, 300 215, 390 215" fill="none" />
        <path :class="['pipe-line', lineStates['line-2a-3']]" d="M 390 65 C 480 65, 480 140, 570 140" fill="none" />
        <path :class="['pipe-line', lineStates['line-2b-3']]" d="M 390 215 C 480 215, 480 140, 570 140" fill="none" />
        <path :class="['pipe-line', lineStates['line-3-4']]" d="M 570 140 L 730 140" fill="none" />
        <path :class="['pipe-line', lineStates['line-4-5']]" d="M 730 140 L 900 140" fill="none" />
      </svg>
      <div
        v-for="n in nodeConfigs"
        :key="n.id"
        class="pipe-node"
        :data-status="nodeStates[n.id]"
        :style="{ left: n.x + 'px', top: n.y + 'px' }"
      >
        <div class="node-circle">
          <component :is="nodeIcon(n)" :size="18" />
        </div>
        <div class="node-label">
          <div class="node-title">{{ n.title }}</div>
          <div class="node-sub">{{ nodeSubs[n.id] || n.defaultSub }}</div>
          <div v-if="nodeTimers[n.id]" class="node-timer">{{ nodeTimers[n.id] }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch, onUnmounted, computed } from 'vue';
import {
  Network, Route, Globe, BookOpen, ScanSearch,
  BrainCircuit, FileText, Loader2, Check, AlertTriangle, Clock3, Minus,
} from 'lucide-vue-next';
import { useAnalysisStore } from '../stores/analysis';

const analysis = useAnalysisStore();

type NodeStatus = 'pending' | 'active' | 'done' | 'failed' | 'timeout' | 'cancelled';

const nodeConfigs = [
  { id: 'enrichment', x: 75, y: 140, icon: Network, title: 'Enrichment', defaultSub: 'GO & KEGG' },
  { id: 'planning', x: 210, y: 140, icon: Route, title: 'Planning', defaultSub: 'Query Strategy' },
  { id: 'search', x: 390, y: 65, icon: Globe, title: 'Web Search', defaultSub: 'Tavily API' },
  { id: 'pubmed', x: 390, y: 215, icon: BookOpen, title: 'PubMed', defaultSub: 'Entrez API' },
  { id: 'extraction', x: 570, y: 140, icon: ScanSearch, title: 'Extraction', defaultSub: 'Relations' },
  { id: 'llm', x: 730, y: 140, icon: BrainCircuit, title: 'Synthesis', defaultSub: 'LLM Gen' },
  { id: 'done', x: 900, y: 140, icon: FileText, title: 'Report', defaultSub: 'Structuring' },
];

const nodeStates = reactive<Record<string, NodeStatus>>({
  enrichment: 'pending', planning: 'pending', search: 'pending',
  pubmed: 'pending', extraction: 'pending', llm: 'pending', done: 'pending',
});

const lineStates = reactive<Record<string, string>>({
  'line-0-1': 'pending', 'line-1-2a': 'pending', 'line-1-2b': 'pending',
  'line-2a-3': 'pending', 'line-2b-3': 'pending', 'line-3-4': 'pending', 'line-4-5': 'pending',
});

const nodeSubs = reactive<Record<string, string>>({});
const nodeTimers = reactive<Record<string, string>>({});

// Timer intervals
const timerIntervals: Record<string, ReturnType<typeof setInterval>> = {};
const timerStarts: Record<string, number> = {};

function startTimer(nodeId: string) {
  timerStarts[nodeId] = Date.now();
  timerIntervals[nodeId] = setInterval(() => {
    const elapsed = ((Date.now() - timerStarts[nodeId]) / 1000).toFixed(1);
    nodeTimers[nodeId] = `${elapsed}s`;
  }, 100);
}

function stopTimer(nodeId: string) {
  if (timerIntervals[nodeId]) {
    clearInterval(timerIntervals[nodeId]);
    delete timerIntervals[nodeId];
  }
}

function setNode(id: string, status: NodeStatus) {
  nodeStates[id] = status;
  if (status === 'active') startTimer(id);
  if (status !== 'active') stopTimer(id);
}

function setLine(id: string, status: string) {
  lineStates[id] = status;
}

function resetPipeline() {
  for (const id of Object.keys(nodeStates)) {
    nodeStates[id] = 'pending';
    stopTimer(id);
    delete nodeTimers[id];
    delete nodeSubs[id];
  }
  for (const id of Object.keys(lineStates)) {
    lineStates[id] = 'pending';
  }
}

function setAllDone() {
  for (const id of Object.keys(nodeStates)) {
    nodeStates[id] = 'done';
    stopTimer(id);
  }
  for (const id of Object.keys(lineStates)) {
    lineStates[id] = 'done';
  }
}

function nodeIcon(n: typeof nodeConfigs[number]) {
  const status = nodeStates[n.id];
  if (status === 'active') return Loader2;
  if (status === 'done') return Check;
  if (status === 'failed') return AlertTriangle;
  if (status === 'timeout') return Clock3;
  if (status === 'cancelled') return Minus;
  return n.icon;
}

// Map SSE progress events to pipeline state — mirrors original updatePipelineFromEvent
function handleEvent(step: string, message: string) {
  const msg = (message || '').toLowerCase();
  const isFail = /fail|error/i.test(msg);

  switch (step) {
    case 'enrichment':
      if (msg.includes('running')) { setNode('enrichment', 'active'); }
      else if (msg.includes('complete') || msg.includes('done')) { setNode('enrichment', 'done'); setLine('line-0-1', 'active'); }
      else if (isFail) { setNode('enrichment', 'failed'); }
      break;
    case 'planning':
      if (msg.includes('generating') || msg.includes('planning')) {
        setNode('planning', 'active'); setLine('line-0-1', 'done');
      } else if (!isFail) {
        setNode('planning', 'done');
        setLine('line-1-2a', 'active'); setLine('line-1-2b', 'active');
      }
      if (isFail) setNode('planning', 'failed');
      break;
    case 'search':
      if (msg.includes('searching')) { setNode('search', 'active'); setNode('pubmed', 'active'); }
      else if (msg.includes('skipping web')) { setNode('search', 'done'); }
      else if (msg.includes('found')) { setNode('search', 'done'); }
      else if (msg.includes('all searches') || msg.includes('complete')) {
        setNode('search', 'done'); setNode('pubmed', 'done');
        setLine('line-1-2a', 'done'); setLine('line-1-2b', 'done');
        setLine('line-2a-3', 'active'); setLine('line-2b-3', 'active');
      }
      if (isFail) setNode('search', 'failed');
      break;
    case 'pubmed':
      if (msg.includes('fetching')) { setNode('pubmed', 'active'); }
      else if (msg.includes('fetched') || msg.includes('skipping')) { setNode('pubmed', 'done'); }
      if (isFail) setNode('pubmed', 'failed');
      break;
    case 'extraction':
      if (msg.includes('extracting')) {
        setNode('extraction', 'active');
        setLine('line-2a-3', 'done'); setLine('line-2b-3', 'done');
        // Parse progress like "3/10"
        const m = msg.match(/(\d+)\/(\d+)/);
        if (m) nodeSubs['extraction'] = `${m[1]}/${m[2]}`;
      } else if (msg.includes('extracted') || msg.includes('skipping')) {
        setNode('extraction', 'done');
        const relMatch = msg.match(/(\d+)\s*rel/);
        if (relMatch) nodeSubs['extraction'] = `${relMatch[1]} relations`;
        setLine('line-3-4', 'active');
      }
      if (isFail) setNode('extraction', 'failed');
      break;
    case 'llm':
      if (msg.includes('generating')) {
        setNode('extraction', 'done'); // force
        setNode('llm', 'active');
        setLine('line-3-4', 'done');
      } else if (msg.includes('generated') || msg.includes('skipping')) {
        setNode('llm', 'done');
        setLine('line-4-5', 'active');
      }
      if (isFail) setNode('llm', 'failed');
      break;
    case 'done':
      setNode('done', 'done');
      setLine('line-4-5', 'done');
      break;
  }
}

// Watch progress array for new events
let lastProcessed = 0;

watch(() => analysis.progress.length, () => {
  const events = analysis.progress;
  for (let i = lastProcessed; i < events.length; i++) {
    handleEvent(events[i].event, events[i].message || '');
  }
  lastProcessed = events.length;
});

// Watch status changes
watch(() => analysis.status, (status) => {
  if (status === 'running') {
    resetPipeline();
    lastProcessed = 0;
  } else if (status === 'done') {
    setAllDone();
  } else if (status === 'error') {
    // Stop all active timers
    for (const id of Object.keys(nodeStates)) {
      if (nodeStates[id] === 'active') setNode(id, 'failed');
    }
  }
}, { immediate: true });

// If result already loaded (e.g. from history), show all done
if (analysis.result && analysis.status === 'done') {
  setAllDone();
}

onUnmounted(() => {
  for (const id of Object.keys(timerIntervals)) {
    clearInterval(timerIntervals[id]);
  }
});
</script>
