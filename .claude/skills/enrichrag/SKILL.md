---
name: enrichrag
description: enrichRAG 專案完整指南——架構、pipeline 流程、開發/部署指令、API、設定、檔案位置。開發、debug、寫測試、重構時載入此 skill。
---

# enrichRAG — 基因富集分析 RAG Pipeline

將一組基因 + 疾病 context 輸入，經過富集分析、文獻檢索、關係提取，產出結構化知識圖譜與 LLM 分析報告。

## Quick Start

```bash
cp .env.example .env          # 填入 OPENAI_API_KEY, TAVILY_API_KEY, PUBMED_EMAIL
uv sync                       # Python deps
cd frontend && npm i && cd .. # Frontend deps
make kg-build                 # 建置 local KG (首次, ~10 min)
make dev                      # frontend build + backend → http://localhost:9001
```

## 常用指令

| 指令 | 說明 |
|------|------|
| `make dev` | build frontend + 啟動 backend (reload) |
| `make frontend` | 僅啟動 frontend dev server |
| `make backend` | 僅啟動 backend (uvicorn --reload, port 9001) |
| `make start` | production-like (no reload) |
| `make kg-build` | 下載 + 匯入 KG sources → SQLite |
| `make kg-rebuild` | 強制重新下載 KG |
| `make lint` | ruff (Python) + eslint (frontend) |
| `make typecheck` | vue-tsc |
| `make clean` | 清除 frontend/dist + __pycache__ |
| `uv run enrichrag analyze` | CLI 跑完整 pipeline |
| `uv run pytest tests/ -v` | 跑測試 |

## Pipeline 流程

```
run_pipeline(genes, disease_context, pval_threshold)   ← core/pipeline.py
  │
  ├─ 1. Gene Enrichment ──── core/enricher.py
  │     gseapy ORA → GO_Biological_Process_2021 + KEGG_2021_Human
  │     filter by adjusted p-value
  │
  ├─ 2. Query Planning ──── core/query_planner.py [LLM]
  │     enrichment terms + disease → QueryPlan
  │     4 類 SearchIntent: pathway_mechanism / gene_interaction / gene_disease / therapeutic
  │     每個 intent 帶 tavily_query + pubmed_query + MeSH terms
  │
  ├─ 3. Parallel Search ──── 3 threads
  │     ├─ core/web_search.py ─── Tavily API
  │     ├─ core/pubmed.py ─────── NCBI Entrez (Biopython)
  │     └─ knowledge_graph/knowledge_graph.py ── SQLite local KG
  │
  ├─ 4. Relation Extraction ──── core/relation_extractor.py [LLM]
  │     PubMed abstracts → entities (gene/disease/drug/pathway)
  │                       → relations (upregulate/downregulate/activate/inhibit/...)
  │     SQLite cache by PMID
  │
  ├─ 5. Graph Building ──── core/graph_builder.py
  │     enrichment + extracted + KG relations → D3 JSON { nodes[], edges[] }
  │
  └─ 6. LLM Synthesis ──── prompts/templates/enrichment_analysis.yaml [LLM]
        → Markdown 報告 (signals / interpretation / caveats / hypotheses)
```

## API Endpoints

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/api/analyze/stream` | SSE pipeline stream (params: genes, disease, pval) |
| POST | `/api/chat` | SSE result-grounded chat |
| POST | `/api/genes/validate` | 驗證基因列表 |
| GET | `/api/genes/{symbol}` | Gene profile |
| GET | `/api/history` | 已儲存的分析列表 |
| POST | `/api/auth/login` | 登入 |
| POST | `/api/auth/register` | 註冊 (需 invite code) |

Auth: HttpOnly session cookie, SameSite=Lax。除 auth 外所有 endpoint 需驗證。

## LLM 配置

| 步驟 | ENV | Default | Temp | 可降級 |
|------|-----|---------|------|--------|
| Query Planning | `LLM_MODEL` | gpt-4o | 0 | Yes (rule-based) |
| Relation Extraction | `LLM_MODEL` | gpt-4o | 0 | Yes (空 relations) |
| Synthesis Report | `LLM_MODEL_REPORT` | gpt-4o | 0.2 | Yes (跳過) |
| Chat QA | `LLM_MODEL` | gpt-4o | — | — |

LangChain prompt templating + Pydantic structured output (function calling)。

## 環境變數

```env
# Required
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
PUBMED_EMAIL=your@email.com

# Optional
LLM_MODEL=gpt-4o
LLM_MODEL_REPORT=gpt-4o
LOG_LEVEL=INFO
URL_PREFIX=""                  # reverse proxy prefix
KG_ENABLED=true
AUTH_INVITE_CODE=enrichrag-invite
AUTH_SECURE_COOKIES=false      # true for HTTPS
```

## Knowledge Graph

SQLite local KG，存放於 `~/.enrichrag/knowledge_graph/data/`。

| Source | 資料 |
|--------|------|
| STRING v12.0 | PPI (score ≥ 700) |
| KEGG Pathway | 有向調控關係 (KGML) |
| PubTator Central | gene-gene/disease/chemical 共現 (~39M) |
| Reactome | Functional interactions with direction + score |
| NCBI Gene | Symbol normalization |

15 canonical relation types × 6 groups (Regulation, Interaction, Association, Expression, Clinical, Correlation)。

## 最終輸出 JSON

```
{
  input_genes, disease_context,
  enrichment_results: { GO: [], KEGG: [] },
  llm_insight: "# Markdown report...",
  sources: { web: [{title, url, content}], pubmed: [{pmid, title, abstract, ...}] },
  gene_relations: [{source, target, relation, evidence, pmid, source_db}],
  graph: { nodes: [{id, label, type}], edges: [{source, target, relation}] },
  query_plan: { intents[], top_genes[], gene_clusters{} }
}
```

## 檔案速查

```
enrichrag/
├── core/
│   ├── pipeline.py            ← run_pipeline() 主流程
│   ├── enricher.py            ← GeneEnricher, gseapy ORA
│   ├── query_planner.py       ← QueryPlanner, LLM 分類 + MeSH
│   ├── web_search.py          ← Tavily search
│   ├── pubmed.py              ← PubMed fetch (Biopython/Entrez)
│   ├── relation_extractor.py  ← LLM 結構化提取
│   └── graph_builder.py       ← D3 graph JSON
├── knowledge_graph/
│   └── knowledge_graph.py     ← SQLite local KG
├── prompts/templates/
│   ├── enrichment_analysis.yaml
│   ├── get_genes_relation.yaml
│   └── chat_qa.yaml
├── api/
│   ├── app.py                 ← FastAPI app
│   └── routes.py              ← SSE routes + auth
├── cli.py                     ← Typer CLI
├── settings.py                ← Pydantic Settings
└── main.py                    ← backward-compat entry

frontend/
├── src/
│   ├── components/            ← Vue 3 components (15+)
│   ├── stores/                ← Pinia state
│   ├── services/              ← API client
│   ├── styles/                ← Domain-scoped CSS (14 files)
│   └── types.ts               ← TypeScript defs
└── dist/                      ← Build output (served by FastAPI)

tests/
└── test_enrichment_cases.py   ← enrichment integration tests
```

## 技術棧

Python 3.10+, gseapy, LangChain, FastAPI, SSE, SQLite, Biopython, Tavily, Typer, Pydantic Settings, Loguru | Vue 3, Pinia, D3.js 7, Vite, TypeScript
