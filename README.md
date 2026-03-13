# EnrichRAG

**EnrichRAG is a modular framework that performs canonical gene set enrichment and extends it with knowledge graph retrieval, literature augmentation, and LLM-based interpretation.**

核心概念：從一群基因出發，透過多種手段（enrichment、knowledge graph、文獻檢索）擴充上下文，再用 LLM 做整合分析與未知探索。

---

## Architecture

```mermaid
flowchart TD
    INPUT["🧬 Input Gene List"]

    subgraph ENRICH["Phase 1: Enrichment Analysis"]
        ORA["GeneEnricher\n(GO / KEGG ORA)"]
    end

    subgraph GRAPH["Phase 2: Knowledge Graph Retrieval"]
        direction TB
        KG["KnowledgeGraph\n(NetworkX MultiDiGraph)"]
        QUERY["Graph Query\nego_graph / PageRank"]

        subgraph KNOWN["已知關係 (底層)"]
            STRING["STRING DB\n(PPI)"]
            KEGG_G["KEGG Pathway\n(調控方向)"]
            REACTOME["Reactome\n(訊號通路)"]
        end

        subgraph UNKNOWN["潛在關聯 (上層, 後續)"]
            PUBMED_LLM["PubMed + LLM\nRelationExtractor"]
        end

        KNOWN --> KG
        UNKNOWN -.-> KG
        KG --> QUERY
    end

    subgraph EXPAND["Phase 3: Context Expansion"]
        NEIGHBOR["擴充基因\n(Graph Neighbors)"]
        ENRICH2["二次 Enrichment\n(擴充後的基因集)"]
        PUBMED["PubMedFetcher\n(targeted abstracts)"]
        WEB["WebSearcher\n(Tavily)"]
    end

    subgraph LLM_PHASE["Phase 4: LLM Integration"]
        PROMPT["PromptGenerator\n(組合所有 context)"]
        LLM["LLM Analysis\n(GPT-4o / Claude)"]
        OUTPUT["📊 Analysis Report\n+ Novel Hypotheses"]
    end

    INPUT --> ORA
    INPUT --> QUERY
    QUERY --> NEIGHBOR
    NEIGHBOR --> ENRICH2
    ORA --> PROMPT
    ENRICH2 --> PROMPT
    NEIGHBOR --> PUBMED
    PUBMED --> PROMPT
    WEB --> PROMPT
    PROMPT --> LLM
    LLM --> OUTPUT

    QUERY -. "gap: 圖上無路徑的基因對" .-> PUBMED_LLM
    PUBMED_LLM -. "新關係存回圖" .-> KG

    style KNOWN fill:#e8f5e9
    style UNKNOWN fill:#fff3e0
    style LLM_PHASE fill:#e3f2fd
```

---

## Problem Statement

給定一組基因（gene set），研究者希望知道：

1. 這組基因在**哪些生物功能／路徑中顯著富集**
2. 不同資料庫（GO、KEGG…）的結果是否**一致或互補**
3. 是否存在**文獻支持的隱含關聯**，解釋這些富集結果的生物學脈絡

### 現有方法的限制

* 傳統 enrichment（ORA / GSEA）：結果分散在多個資料庫，缺乏整合與語境解釋
* 文獻閱讀：高成本、不可重現
* LLM 直接生成：缺乏可驗證的基礎結果

---

## Modules

### Enrichment Layer

| Module | Description | Status |
|--------|-------------|--------|
| **GeneEnricher** | ORA analysis (GO/KEGG) with gseapy | ✅ Done |
| **PromptGenerator** | YAML template + LangChain LCEL | ✅ Done |

### Retrieval Layer

| Module | Description | Status |
|--------|-------------|--------|
| **PubMedFetcher** | Entrez API abstract retrieval | ✅ Done |
| **WebSearcher** | Tavily Search integration | ✅ Done |
| **RelationExtractor** | LLM-based relation extraction (Pydantic structured output) | ✅ Done |

### Knowledge Graph Layer

| Module | Description | Status |
|--------|-------------|--------|
| **KnowledgeGraph** | NetworkX MultiDiGraph wrapper with graph query | Planned |
| **STRING DB importer** | PPI edges (`type="ppi"`) | Planned |
| **KEGG Pathway importer** | Directed regulatory edges (`type="pathway"`) | Planned |

### LLM Integration

| Module | Description | Status |
|--------|-------------|--------|
| **LLM Chain** | GPT-4o / Claude with StrOutputParser | ✅ Done |

### Web UI & Visualization

| Feature | Description | Status |
|---------|-------------|--------|
| **Web Interface** | FastAPI + SSE streaming pipeline | ✅ Done |
| **Gene Validation** | Canonical gene normalization with accepted / remapped / rejected summaries | ✅ Done |
| **Pipeline Flowchart** | Animated node states with per-step timers | ✅ Done |
| **Network Graph** | D3.js force-directed graph (zoom/pan, color-coded entities) | ✅ Done |
| **Report Rendering** | Markdown → styled HTML with Lora serif typography | ✅ Done |
| **Tabbed Results** | Enrichment tables, sources, relations, insights | ✅ Done |
| **Analysis Chat Assistant** | Result-grounded chat drawer with streaming answers and suggested questions | ✅ Done |
| **History Management** | Load, delete, and clear saved browser-side analysis history | ✅ Done |
| **UI Refactor Sandbox** | Isolated `/ui-refactor` route for staged frontend redesign work | ✅ Done |

---

## Core API

```python
enrich(gene_set: List[str]) -> EnrichmentReport
```

### EnrichmentReport schema

```json
{
  "input_genes": [...],
  "databases": ["GO", "KEGG"],
  "results": {
    "GO": [...],
    "KEGG": [...]
  }
}
```

### Relation Table schema

```
| Source Gene | Target Gene | Relation | Type    | Source DB | Evidence                        |
|-------------|-------------|----------|---------|-----------|---------------------------------|
| TP53        | EGFR        | up       | pathway | KEGG      | KEGG:hsa05200                   |
| TP53        | MDM2        | up       | ppi     | STRING    | combined_score=0.999            |
| RBM10       | MYC         | down     | llm     | PubMed    | "...inhibiting transcription..." |
```

---

## Roadmap

### v0.1 - Core Framework ✅

- [x] **GeneEnricher**: ORA analysis (GO/KEGG)
- [x] **PromptGenerator**: YAML template + LangChain LCEL
- [x] **LLM Integration**: GPT-4o chain with StrOutputParser
- [x] **WebSearcher**: Tavily Search integration
- [x] **PubMedFetcher**: Entrez API abstract retrieval
- [x] **RelationExtractor**: LLM-based relation extraction with Pydantic structured output

### v0.2 - Web UI & Pipeline Integration ✅

- [x] **Web UI**: FastAPI backend + single-page frontend with SSE streaming
- [x] **Gene Validation**: Normalize symbols before analysis with accepted / remapped / rejected feedback
- [x] **Pipeline Orchestration**: Enrichment → parallel search (Web + PubMed) → relation extraction → LLM synthesis
- [x] **Animated Pipeline Flowchart**: Real-time node status with elapsed timers, timeout/failure states
- [x] **D3 Network Graph**: Force-directed visualization with zoom/pan, lazy rendering
- [x] **Report Typography**: Lora serif font, wider layout, structured Markdown headings
- [x] **Relations in LLM Prompt**: Extracted biomedical relations fed into analysis for richer interpretation
- [x] **Result-grounded Chat Assistant**: Full-result chat context, streaming responses, and suggested follow-up questions
- [x] **History Controls**: Browser-side saved analyses can be reloaded, deleted individually, or cleared
- [x] **UI Refactor Sandbox**: `/ui-refactor` route for iterative frontend redesign without changing the main page
- [x] **CLI Interface**: `enrichrag` command via Typer

### Frontend Notes

- Main application route: `/`
- Frontend redesign sandbox: `/ui-refactor`
- Analysis results are stored in browser local storage under `enrichrag_history_v2`
- Chat answers are grounded in the current analysis result payload rather than an external database lookup

### v0.3 - Knowledge Graph: 已知關係 (Next)

**KnowledgeGraph module**
- [ ] `KnowledgeGraph` class (NetworkX MultiDiGraph wrapper)
  - [ ] Unified edge schema: `(source, target, {type, direction, source_db, evidence, ...})`
  - [ ] `add_relations(df)` — batch add edges from DataFrame
  - [ ] `get_neighbors(gene, radius)` — ego subgraph
  - [ ] `rank_nodes(method)` — degree / PageRank
  - [ ] `to_context(genes)` — convert to text for prompt injection
  - [ ] Persistence: save/load GraphML or JSON

**Import known biological graphs**
- [ ] **STRING DB** — download TSV, import PPI edges (`type="ppi"`)
- [ ] **KEGG Pathway** — import directed regulatory edges (`type="pathway"`)
- [ ] **PubTator Central** — bulk co-occurrence edges from FTP. Provides low-cost, large-scale gene-gene and gene-disease co-occurrence relationships mined from PubMed abstracts.
- [ ] (optional) Reactome / DisGeNET

**Pipeline integration**
- [ ] `genes → KnowledgeGraph.get_neighbors() → expanded_genes`
- [ ] `expanded_genes → GeneEnricher (second-round enrichment)`
- [ ] `expanded_genes → PubMedFetcher (targeted search)`
- [ ] All context assembled → PromptGenerator → LLM

### v0.4 - Knowledge Graph: 潛在關聯 (Future)

**LLM-based Relation Extraction (on-demand)**
- [ ] Detect gaps: find gene pairs with no path in graph
- [ ] For gap pairs → PubMedFetcher → RelationExtractor → extract relations
- [ ] Store new relations back to KnowledgeGraph (graph grows with usage)
- [ ] Cache layer: avoid duplicate queries for same gene pairs

### v0.5 - Visualization Enhancements (Future)

**Enrichment Charts**
- [ ] Enrichment bar chart — top GO/KEGG terms sorted by -log10(p-adjusted)
- [ ] Dot plot — x=gene count, y=term, size=overlap ratio, color=p-value
- [ ] Gene-term heatmap — overlap matrix (genes × pathways)

**Network Graph Enhancements**
- [ ] Node sizing by degree / PageRank, edge coloring by relation type
- [ ] Interactive: hover to highlight neighbors, click to inspect evidence
- [ ] `/api/graph` endpoint — return graph JSON for frontend rendering

### v1.0 - Full Pipeline (Future)

- [ ] CLI: `enrichrag analyze --genes TP53 KRAS EGFR --disease cancer`
- [ ] Single command: enrich → graph expand → literature → LLM report
- [ ] PubMed query cache (SQLite/Parquet)
- [ ] (optional) Embedding index for semantic retrieval (ChromaDB)
- [ ] (optional) Neo4j to replace NetworkX for large persistent graphs
