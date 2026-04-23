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

## CLI 研究流程（Agent 操作指南）

以下是 agent 透過 terminal 執行基因分析的標準流程。依序操作，每步驗證後再進下一步。

### 流程總覽

```
1. 確認 KG 就緒        → kg status
2. 驗證 gene symbols   → genes validate（檢查 remap / rejected）
3. 查疑問 gene 細節    → genes profile
4. 跑分析              → analyze --validate-first
5. 審閱結果            → result summary
6. 深入追查            → result papers / terms / graph-stats / inspect
```

### Step 1 — 確認 KG

```bash
uv run enrichrag kg status
```

若 KG 不存在會提示 `enrichrag kg build`。確認有 gene_id_map 和 edges 才能繼續。

### Step 2 — 驗證 Gene Symbols

```bash
# 人類可讀表格
uv run enrichrag genes validate BRCA1 BRCA2 TP53 ATM CHEK2

# 從檔案讀取（一行一個 gene，# 開頭為註解）
uv run enrichrag genes validate --file genes.txt

# 混合使用
uv run enrichrag genes validate BRCA1 BRCA2 --file more_genes.txt

# 機器可讀 JSON
uv run enrichrag genes validate BRCA1 P53 NOPE --json
```

輸出：每個 gene 的 status（accepted / remapped / rejected）、normalized symbol、source。
- **accepted**：完全匹配 HGNC canonical symbol
- **remapped**：別名/舊名 → 標準名（如 P53 → TP53）
- **rejected**：找不到對應，需修正後重試
- 有任何 rejected → exit code 2

### Step 3 — 查 Gene Profile

```bash
uv run enrichrag genes profile BRCA1
uv run enrichrag genes profile TP53 --json
```

顯示 Gene ID、Official Symbol/Name、Type、Chromosome、Map Location、Synonyms、DBXrefs。
資料來源：NCBI Homo_sapiens.gene_info.gz 快取。

### Step 4 — 跑分析

```bash
uv run enrichrag analyze BRCA1 BRCA2 RAD51 ATM CHEK2 \
  --disease "breast cancer" \
  --pval 0.05 \
  --validate-first \
  --output output/result.json
```

| Flag | 預設 | 說明 |
|------|------|------|
| `--disease, -d` | `"cancer"` | 疾病 context |
| `--pval, -p` | `0.05` | enrichment p-value 門檻 |
| `--validate-first` | off | 先跑 validation，rejected 會警告但繼續用剩餘 genes 跑 |
| `--strict` | off | 搭配 --validate-first，有任何 rejected 就中止（exit 2） |
| `--file, -f` | — | 從檔案讀 gene list（一行一個，# 為註解） |
| `--output, -o` | `output/result.json` | 輸出路徑 |
| `--json` | off | validation 結果用 JSON 輸出（搭配 --validate-first） |

`--validate-first` 會自動用 normalized symbols 跑 pipeline，不需要手動替換。
rejected genes 會被跳過並顯示黃色警告，若全部 rejected 則中止（exit 2）。

### Step 5 — 審閱結果

```bash
uv run enrichrag result summary output/result.json
uv run enrichrag result summary output/result.json --json
```

Summary 包含：
- 總覽表：genes 數、GO/KEGG terms 數、web/PubMed sources 數、relations 數、graph nodes/edges
- Top 5 GO terms（term name、adjusted p-value、overlap）
- Top 5 KEGG terms
- Top 5 PubMed sources（PMID、title、journal）
- Graph node type 分布
- LLM insight preview（前 800 字）

### Step 6 — 深入追查

#### 查看所有文獻來源

```bash
uv run enrichrag result papers output/result.json
uv run enrichrag result papers output/result.json --limit 10   # 限制顯示數量
uv run enrichrag result papers output/result.json --json
```

列出所有 PubMed sources（PMID、title、journal、date）和 Web sources（title、URL）。

#### 圖譜統計

```bash
uv run enrichrag result graph-stats output/result.json
uv run enrichrag result graph-stats output/result.json --top 20  # top hub nodes 數量
uv run enrichrag result graph-stats output/result.json --json
```

顯示：node type 分布、edge type 分布、relation type + group 分布、top hub nodes（by degree）。

#### 查看 Enrichment Terms

```bash
uv run enrichrag result terms output/result.json                 # 全部 GO + KEGG
uv run enrichrag result terms output/result.json --db GO         # 只看 GO
uv run enrichrag result terms output/result.json --db KEGG --limit 10
uv run enrichrag result terms output/result.json --json
```

完整列出 enrichment terms（term name、adjusted p-value、overlap、genes）。

#### 反查特定 Gene

```bash
uv run enrichrag result inspect output/result.json --gene BRCA1
uv run enrichrag result inspect output/result.json --gene ATM --json
```

顯示該 gene 涉及的：
- Enrichment terms（哪些 GO/KEGG terms 包含此 gene）
- Relations（與其他 genes/diseases/chemicals 的關係）
- Related papers（透過 relations 連結到的 PubMed 文獻）

### 完整範例（推薦操作序列）

```bash
# 1. 環境確認
uv run enrichrag kg status

# 2. 驗證
uv run enrichrag genes validate BRCA1 BRCA2 RAD51 RAD52 ATM ATR CHEK1 CHEK2 MLH1 MSH2 MSH6 PMS2

# 3. 分析（含自動驗證，rejected 會警告但繼續）
uv run enrichrag analyze BRCA1 BRCA2 RAD51 RAD52 ATM ATR CHEK1 CHEK2 MLH1 MSH2 MSH6 PMS2 \
  --disease "breast cancer" \
  --pval 0.05 \
  --validate-first

# 4. 摘要總覽
uv run enrichrag result summary output/result.json

# 5. 深入追查
uv run enrichrag result papers output/result.json           # 文獻來源
uv run enrichrag result graph-stats output/result.json      # 圖譜統計
uv run enrichrag result terms output/result.json --db GO    # GO terms
uv run enrichrag result inspect output/result.json --gene BRCA1  # 反查 BRCA1

# 從檔案讀 gene list
uv run enrichrag analyze --file genes.txt --disease "breast cancer" --validate-first
```

### 其他指令

```bash
uv run enrichrag version          # 版本
uv run enrichrag serve            # 啟動 web server（同 make backend）
uv run enrichrag kg build         # 建置 KG（首次約 10 分鐘）
uv run enrichrag kg build --source ncbi --force  # 重建單一來源
```

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
├── test_enrichment_cases.py   ← enrichment integration tests
└── test_cli.py                ← CLI subcommands (validate, profile, summary)
```

## 技術棧

Python 3.10+, gseapy, LangChain, FastAPI, SSE, SQLite, Biopython, Tavily, Typer, Pydantic Settings, Loguru | Vue 3, Pinia, D3.js 7, Vite, TypeScript
