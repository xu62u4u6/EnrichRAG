<template>
  <div class="pipeline-tab-wrap">
    <div class="loading-header">
      <h3>Pipeline Execution</h3>
      <p>{{ analysis.running ? 'Running pipeline...' : analysis.status === 'done' ? 'Pipeline complete' : 'Waiting to start' }}</p>
    </div>
    <div class="pipeline-canvas">
      <svg class="pipeline-desktop-map pipeline-desktop-lines" viewBox="0 0 1080 340">
        <!-- Enrichment → Planning -->
        <path :class="['pipe-line', lineStates['line-0-1']]" d="M 75 155 L 210 155" fill="none" />
        <!-- Planning → Web Search / Local KG / PubMed -->
        <path :class="['pipe-line', lineStates['line-1-2a']]" d="M 210 155 C 300 155, 300 60, 390 60" fill="none" />
        <path :class="['pipe-line', lineStates['line-1-2b']]" d="M 210 155 L 390 155" fill="none" />
        <path :class="['pipe-line', lineStates['line-1-2c']]" d="M 210 155 C 300 155, 300 260, 390 260" fill="none" />
        <!-- Web Search → LLM (bypass extraction) -->
        <path :class="['pipe-line', lineStates['line-2a-4']]" d="M 390 60 C 520 60, 640 155, 770 155" fill="none" />
        <!-- Local KG → LLM (bypass extraction) -->
        <path :class="['pipe-line', lineStates['line-2b-4']]" d="M 390 155 L 770 155" fill="none" />
        <!-- PubMed → Extraction (only direct feeder) -->
        <path :class="['pipe-line', lineStates['line-2c-3']]" d="M 390 260 L 580 260" fill="none" />
        <!-- Extraction → LLM -->
        <path :class="['pipe-line', lineStates['line-3-4']]" d="M 580 260 C 680 260, 680 155, 770 155" fill="none" />
        <!-- LLM → Report -->
        <path :class="['pipe-line', lineStates['line-4-5']]" d="M 770 155 L 940 155" fill="none" />
      </svg>
      <!-- Desktop nodes (absolute positioned) -->
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

      <!-- Mobile vertical rail -->
      <div class="pipeline-mobile-rail">
        <!-- Sequential: Enrichment, Planning -->
        <div v-for="n in mobileSequentialBefore" :key="'m-' + n.id" class="mobile-step">
          <div class="mobile-link" :data-link-status="mobileLinkStatus(n.id)"></div>
          <div class="pipe-node mobile-node" :data-status="nodeStates[n.id]">
            <div class="node-circle"><component :is="nodeIcon(n)" :size="18" /></div>
            <div class="node-label">
              <div class="node-title">{{ n.title }}</div>
              <div class="node-sub">{{ nodeSubs[n.id] || n.defaultSub }}</div>
              <div v-if="nodeTimers[n.id]" class="node-timer">{{ nodeTimers[n.id] }}</div>
            </div>
          </div>
        </div>

        <!-- Parallel: Web Search, Local KG, PubMed -->
        <div class="mobile-branch-group">
          <div class="mobile-branch-head">
            <span class="branch-kicker">Parallel Retrieval</span>
            <span class="branch-rule"></span>
          </div>
          <div class="mobile-branch-grid">
            <div v-for="n in mobileParallel" :key="'m-' + n.id" class="mobile-step">
              <div class="pipe-node mobile-node" :data-status="nodeStates[n.id]">
                <div class="node-circle"><component :is="nodeIcon(n)" :size="18" /></div>
                <div class="node-label">
                  <div class="node-title">{{ n.title }}</div>
                  <div class="node-sub">{{ nodeSubs[n.id] || n.defaultSub }}</div>
                  <div v-if="nodeTimers[n.id]" class="node-timer">{{ nodeTimers[n.id] }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Sequential: Extraction, LLM, Report -->
        <div v-for="n in mobileSequentialAfter" :key="'m-' + n.id" class="mobile-step">
          <div class="mobile-link" :data-link-status="mobileLinkStatus(n.id)"></div>
          <div class="pipe-node mobile-node" :data-status="nodeStates[n.id]">
            <div class="node-circle"><component :is="nodeIcon(n)" :size="18" /></div>
            <div class="node-label">
              <div class="node-title">{{ n.title }}</div>
              <div class="node-sub">{{ nodeSubs[n.id] || n.defaultSub }}</div>
              <div v-if="nodeTimers[n.id]" class="node-timer">{{ nodeTimers[n.id] }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch, onUnmounted, computed } from 'vue';
import {
  Network, Route, Globe, BookOpen, ScanSearch, Database,
  BrainCircuit, FileText, Loader2, Check, AlertTriangle, Clock3, Minus,
} from 'lucide-vue-next';
import { useAnalysisStore } from '../stores/analysis';

const analysis = useAnalysisStore();

type NodeStatus = 'pending' | 'active' | 'done' | 'failed' | 'timeout' | 'cancelled';

// Mobile layout groupings
const mobileSequentialBefore = computed(() =>
  nodeConfigs.filter(n => n.id === 'enrichment' || n.id === 'planning'),
);
const mobileParallel = computed(() =>
  nodeConfigs.filter(n => ['search', 'knowledge_graph', 'pubmed'].includes(n.id)),
);
const mobileSequentialAfter = computed(() =>
  nodeConfigs.filter(n => ['extraction', 'llm', 'done'].includes(n.id)),
);

function mobileLinkStatus(nodeId: string): string {
  const status = nodeStates[nodeId];
  if (status === 'done' || status === 'active') return status;
  return 'pending';
}

const nodeConfigs = [
  { id: 'enrichment', x: 75, y: 155, icon: Network, title: 'Enrichment', defaultSub: 'GO & KEGG' },
  { id: 'planning', x: 210, y: 155, icon: Route, title: 'Planning', defaultSub: 'Query Strategy' },
  { id: 'search', x: 390, y: 60, icon: Globe, title: 'Web Search', defaultSub: 'Tavily API' },
  { id: 'knowledge_graph', x: 390, y: 155, icon: Database, title: 'Local KG', defaultSub: 'Reactome · STRING' },
  { id: 'pubmed', x: 390, y: 260, icon: BookOpen, title: 'PubMed', defaultSub: 'Entrez API' },
  { id: 'extraction', x: 580, y: 260, icon: ScanSearch, title: 'Extraction', defaultSub: 'Relations' },
  { id: 'llm', x: 770, y: 155, icon: BrainCircuit, title: 'Synthesis', defaultSub: 'LLM Gen' },
  { id: 'done', x: 940, y: 155, icon: FileText, title: 'Report', defaultSub: 'Structuring' },
];

const nodeStates = reactive<Record<string, NodeStatus>>({
  enrichment: 'pending', planning: 'pending', search: 'pending', knowledge_graph: 'pending',
  pubmed: 'pending', extraction: 'pending', llm: 'pending', done: 'pending',
});

const lineStates = reactive<Record<string, string>>({
  'line-0-1': 'pending', 'line-1-2a': 'pending', 'line-1-2b': 'pending', 'line-1-2c': 'pending',
  'line-2a-4': 'pending', 'line-2b-4': 'pending', 'line-2c-3': 'pending', 'line-3-4': 'pending', 'line-4-5': 'pending',
});

const nodeSubs = reactive<Record<string, string>>({});
const nodeTimers = reactive<Record<string, string>>({});

// Timer intervals
const timerIntervals: Record<string, ReturnType<typeof setInterval>> = {};
const timerStarts: Record<string, number> = {};

function startTimer(nodeId: string) {
  if (timerIntervals[nodeId]) return; // already running
  timerStarts[nodeId] = Date.now();
  timerIntervals[nodeId] = setInterval(() => {
    const elapsed = ((Date.now() - timerStarts[nodeId]) / 1000).toFixed(1);
    nodeTimers[nodeId] = `${elapsed}s`;
  }, 500);
}

function stopTimer(nodeId: string) {
  if (timerIntervals[nodeId]) {
    clearInterval(timerIntervals[nodeId]);
    delete timerIntervals[nodeId];
  }
}

function setNode(id: string, status: NodeStatus) {
  const cur = nodeStates[id];
  // Don't regress: done → active, or re-set same status
  if (cur === status) return;
  if (cur === 'done' && status === 'active') return;
  nodeStates[id] = status;
  if (status === 'active') startTimer(id);
  if (status !== 'active') stopTimer(id);
}

const lineOrder = ['pending', 'active', 'done'] as const;
function setLine(id: string, status: string) {
  const curIdx = lineOrder.indexOf(lineStates[id] as typeof lineOrder[number]);
  const newIdx = lineOrder.indexOf(status as typeof lineOrder[number]);
  // Only advance forward: pending → active → done
  if (newIdx > curIdx) lineStates[id] = status;
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
        setLine('line-1-2a', 'active'); setLine('line-1-2b', 'active'); setLine('line-1-2c', 'active');
      }
      if (isFail) setNode('planning', 'failed');
      break;
    case 'search':
      if (msg.includes('searching')) {
        setNode('search', 'active');
        setLine('line-1-2a', 'done'); // data arrived at node
      } else if (msg.includes('skipping web')) {
        setNode('search', 'done');
        setLine('line-2a-4', 'done');
      } else if (msg.includes('found') && msg.includes('web')) {
        setNode('search', 'done');
        setLine('line-2a-4', 'active');
      } else if (msg.includes('all searches') || msg.includes('complete')) {
        // Backstop: force all parallel nodes done
        setNode('search', 'done'); setNode('pubmed', 'done'); setNode('knowledge_graph', 'done');
        setLine('line-1-2a', 'done'); setLine('line-1-2b', 'done'); setLine('line-1-2c', 'done');
      }
      if (isFail) setNode('search', 'failed');
      break;
    case 'knowledge_graph':
      if (msg.includes('querying')) {
        setNode('knowledge_graph', 'active');
        setLine('line-1-2b', 'done'); // data arrived at node
      } else if (msg.includes('merged')) {
        // Post-extraction merge — KG node already done, just update sub label
        const mm = msg.match(/(\d+)\s+local kg/);
        if (mm) nodeSubs.knowledge_graph = `${mm[1]} merged`;
      } else if (
        msg.includes('found')
        || msg.includes('no local kg relations found')
        || msg.includes('skipping')
        || msg.includes('database is empty')
      ) {
        setNode('knowledge_graph', 'done');
        setLine('line-1-2b', 'done');
        setLine('line-2b-4', 'active');
        const m = msg.match(/(\d+)\s+local kg relations/);
        if (m) nodeSubs.knowledge_graph = `${m[1]} rel`;
        else if (msg.includes('no local kg relations found')) nodeSubs.knowledge_graph = '0 rel';
        else if (msg.includes('database is empty')) nodeSubs.knowledge_graph = 'DB empty';
        else if (msg.includes('skipping')) nodeSubs.knowledge_graph = 'Skipped';
      }
      if (isFail) setNode('knowledge_graph', 'failed');
      break;
    case 'pubmed':
      if (msg.includes('fetching')) {
        setNode('pubmed', 'active');
        setLine('line-1-2c', 'done'); // data arrived at node
      } else if (msg.includes('fetched') || msg.includes('skipping') || msg.includes('no pubmed')) {
        setNode('pubmed', 'done');
        setLine('line-2c-3', 'active');
      }
      if (isFail) setNode('pubmed', 'failed');
      break;
    case 'extraction':
      if (msg.includes('extracting')) {
        setNode('extraction', 'active');
        setLine('line-2c-3', 'done'); // PubMed → Extraction arrived
        // Parse progress like "3/10"
        const m = msg.match(/(\d+)\/(\d+)/);
        if (m) nodeSubs['extraction'] = `${m[1]}/${m[2]}`;
      } else if (msg.includes('extracted') || msg.includes('skipping')) {
        setNode('extraction', 'done');
        const relMatch = msg.match(/(\d+)\s*rel/);
        if (relMatch) nodeSubs['extraction'] = `${relMatch[1]} relations`;
        setLine('line-3-4', 'active'); // flowing to LLM
      }
      if (isFail) setNode('extraction', 'failed');
      break;
    case 'llm':
      if (msg.includes('generating')) {
        setNode('extraction', 'done'); // force
        setNode('llm', 'active');
        // All incoming lines arrive at LLM
        setLine('line-2a-4', 'done'); setLine('line-2b-4', 'done');
        setLine('line-3-4', 'done');
      } else if (msg.includes('generated') || msg.includes('skipping')) {
        setNode('llm', 'done');
        setLine('line-4-5', 'active');
      }
      if (isFail) setNode('llm', 'failed');
      break;
    case 'graph_update':
      if (msg.includes('local')) {
        nodeSubs['knowledge_graph'] = 'Graph ready';
      }
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
