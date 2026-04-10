# enrichRAG 進階 RAG 技術與 Agent 化研究報告

> 目標讀者：對 RAG / AI agent 概念尚在建立中的開發者
> 撰寫日期：2026-03-21
> 基於 enrichRAG 現有架構出發，評估可行的改進方向與 agent 化策略

---

## 目錄

- [Part 0 — RAG 流派全景圖](#part-0--rag-流派全景圖)
  - [0.1 流派總覽表](#01-流派總覽表)
  - [0.2 基礎層 RAG 流派](#02-基礎層-rag-流派)
  - [0.3 高階工程／架構流派](#03-高階工程架構流派)
  - [0.4 圖式與知識結構流派](#04-圖式與知識結構流派)
  - [0.5 Agent／系統工程流派](#05-agent系統工程流派)
  - [0.6 enrichRAG 在流派地圖上的位置](#06-enrichrag-在流派地圖上的位置)
- [Part 1 — 從現有架構到進階 RAG](#part-1--從現有架構到進階-rag)
  - [1.1 背景知識：RAG 是什麼](#11-背景知識rag-是什麼)
  - [1.2 enrichRAG 現有架構總覽](#12-enrichrag-現有架構總覽)
  - [1.3 我們已經做到的（對照業界技術）](#13-我們已經做到的對照業界技術)
  - [1.4 改進方向總覽（快速比較表）](#14-改進方向總覽快速比較表)
  - [1.5 各改進項目細節](#15-各改進項目細節)
- [Part 2 — 從 Pipeline 到 Agent](#part-2--從-pipeline-到-agent)
  - [2.1 什麼是 Agent？跟 Pipeline 差在哪？](#21-什麼是-agent跟-pipeline-差在哪)
  - [2.2 Agent 架構設計](#22-agent-架構設計)
  - [2.3 需要的 Skills / Tools](#23-需要的-skills--tools)
  - [2.4 實作路徑與技術選型](#24-實作路徑與技術選型)
  - [2.5 完整使用情境範例](#25-完整使用情境範例)

---

## Part 0 — RAG 流派全景圖

在深入 enrichRAG 的改進方向之前，先看看 RAG 的整體「技術樹」長什麼樣。這張表幫你定位：我們在哪裡、還能往哪走。

### 0.1 流派總覽表

| 層級 | 流派 | 一句話說明 | 核心技能 | 典型場景 | enrichRAG |
|------|------|-----------|---------|---------|-----------|
| **基礎層** | Naive RAG | Query → 向量搜尋 top-k → LLM 回答 | Chunking、embedding、向量 DB | 快速 PoC、文件問答 | — |
| | Simple RAG + Memory | 加上 session / context window 管理 | Token budget、對話歷史管理 | 客服聊天、診斷對話 | ⚠️ chat 有 |
| | Hybrid RAG（基礎版） | 向量 + BM25 關鍵字混合檢索 | 多 retriever 融合、score normalization | 企業搜尋、FAQ | ⚠️ 跨源混合 |
| **高階工程** | Advanced RAG | Query rewrite → 多 retriever → rerank → 壓縮 → LLM | Re-ranking、contextual pruning、query rewrite | 醫療知識庫、金融文件 | 🔜 目標 |
| | Multi-hop / Iterative RAG | 拆子問題 → 分步檢索 → 組合答案 | Query decomposition、planning、multi-round | 法律合規、學術研究 | ⚠️ 有拆 intent |
| | Adaptive / Self-RAG | LLM 自我判斷「靠不靠譜、要不要再查」 | Self-evaluation、confidence scoring | 高精度問答、醫療診斷 | — |
| | Router-based RAG | Query 進來先路由到不同子 pipeline | Query classifier、domain routing | 多領域企業系統 | ✅ query_planner |
| **知識結構** | GraphRAG | 知識圖譜 + RAG，支援關係推理 | KG 建構、entity linking、graph traversal | 金融、醫療、法務 | ✅ 核心能力 |
| | Multimodal KG-RAG | 圖 + 多模態（影像、表格、文本）多跳推理 | 多模態 embedding、跨模態對齊 | 醫療影像 + 病歷、工程圖 + 規範 | — |
| **Agent 系統** | Agentic RAG | Agent 控制：要不要查、查哪裡、多步決策 | Agent loop、tool selection、planning | 研究助理、自動分析 | 🔜 目標 |
| | Reasoning + Tool RAG | RAG 做知識檢索 + tool calling 做計算/API | Tool use、function calling、混合推理 | 診斷建議、數據分析 | ⚠️ 部分有 |
| | State-aware / Memory RAG | 多輪對話中逐漸 refine，帶持久記憶 | Session state、長期 memory、追蹤式更新 | 病情追蹤、連續研究 | ⚠️ chat history |

> 圖例：✅ 已實作 ｜ ⚠️ 部分具備 ｜ 🔜 規劃中 ｜ — 尚未涉及

---

### 0.2 基礎層 RAG 流派

這些是「先跑起來」的架構，適合 PoC 和入門。

#### Naive / Simple RAG

```
User Query → Embedding → 向量 DB (top-k) → LLM → Answer
```

- **做法**：文件切 chunk → embedding → 存向量 DB → query 時算 cosine similarity 取 top-k → 塞進 prompt
- **優點**：簡單、好 debug、半天能做出 demo
- **缺點**：recall 差（只靠向量相似度）、噪音多（top-k 不一定都相關）、多跳問題無能為力
- **基礎技能**：
  - Document chunking（固定長度 vs 語意切割 vs recursive splitting）
  - Embedding model 選擇（OpenAI `text-embedding-3-small`、開源 `bge-m3`、生醫 `BioSentVec`）
  - 向量 DB 操作（Chroma / FAISS / Milvus / Qdrant）

#### Simple RAG + Memory / Context Management

- **做法**：在 Naive RAG 基礎上管理 context window——session 歷史、retrieved chunk 長度控制
- **解決的問題**：context overflow（塞太多東西 LLM 看不完）
- **常見於**：客服聊天、診斷對話紀錄上的 RAG
- **enrichRAG 現況**：`chat_context.py` 的 `_compact_*()` 系列函數和 token budget 控制就是這個概念

#### Hybrid RAG（基礎版）

- **做法**：同時用「語意向量搜尋」和「關鍵字 BM25」，混合結果
- **為什麼需要**：向量搜尋擅長「語意相似」但怕同義詞，BM25 擅長「精確匹配」但怕換句話說。兩個互補。
- **融合策略**：Reciprocal Rank Fusion (RRF)、weighted score combination
- **enrichRAG 現況**：我們是「跨來源混合」（KG 結構查詢 + PubMed 關鍵字 + Tavily 語意），精神類似但不是傳統的 vector + BM25 on same corpus

---

### 0.3 高階工程／架構流派

已經在「寫 pipeline、改模組」，關注 recall、幻覺、多跳、多源等問題。

#### Advanced RAG（多階段優化）

```
Query → Rewrite → Pre-filter → Multi-Retriever → Rerank → Compress → LLM
```

- **Query Rewrite**：帶入 domain cue、補充背景（例如把 "AD" 展開成 "Alzheimer's Disease"）
- **Pre-retrieval Filter**：query classifier 先決定查哪幾份資料庫（不是全查）
- **Reranking**：cross-encoder 精排，砍掉噪音
- **Contextual Pruning**：只保留 retrieved doc 中與 query 相關的句子
- **常見於**：企業支援、醫療知識庫、金融文件問答
- **enrichRAG 現況**：有 query planning + multi-retriever，但缺 reranking 和 compression → **Part 1 改進重點**

#### Multi-hop / Iterative RAG

- **做法**：把複雜問題拆成子問題，分步檢索，再組合
- **兩種路線**：
  - LLM 自己做 planning（ReAct / Self-Ask / IRCoT）
  - 用 agent framework 串多步（LangGraph / CrewAI）
- **例子**：「BRCA1 突變會影響哪些 pathway，這些 pathway 跟哪些藥物有關？」→ 先查 BRCA1 pathway → 再查 pathway-drug 關聯
- **enrichRAG 現況**：query_planner 會拆 intent（類似 query decomposition），但是單 pass，不會根據結果回頭補查

#### Adaptive / Corrective / Self-RAG

- **做法**：LLM 自我判斷「這答案靠不靠譜」「要不要再查」「要不要換策略」
- **關鍵機制**：
  - **Self-RAG**：生成時同時輸出 `[Retrieve]` / `[No Retrieve]` 特殊 token，決定要不要查
  - **CRAG（Corrective RAG）**：檢查 retrieved doc 是否真的相關，不相關就丟掉或換策略
- **enrichRAG 現況**：目前沒有自我評估機制 → Part 1 的 Multi-hop + Evaluation 改進在往這方向走

#### Branched / Router-based RAG

- **做法**：不同 domain 建不同子 pipeline，query 進來先分類路由
- **例子**：醫療系統裡，「臨床指南」「實驗數據」「影像報告」各自有專屬 retriever
- **enrichRAG 現況**：✅ `query_planner.py` 把 query 分成 4 類 intent（pathway / interaction / disease / therapeutic），各自建不同的 search query → 已具備此能力

---

### 0.4 圖式與知識結構流派

不只是「把段落餵給 LLM」，而是把知識結構化，讓 RAG 能做推理。

#### GraphRAG / Knowledge Graph + RAG

- **做法**：把實體（人、基因、藥物、疾病）和關係建成圖，RAG 查詢時能走圖做多跳推理
- **優勢**：
  - 支援「A 影響 B，B 又影響 C」這種鏈式推理
  - 可追溯性——每條推理路徑都能追回到具體的邊和來源
  - 結構化 schema 降低幻覺
- **enrichRAG 現況**：✅ 這是核心能力。Local KG 包含 STRING（PPI）、KEGG（pathway）、Reactome（functional interaction）、PubTator（文獻共現），加上 LLM extraction 產生的 relation，最終合併為 D3 graph

#### Multimodal KG-RAG（MMKG-RAG）

- **做法**：圖 + 多模態資料（影像、表格、文本），在圖上做多跳推理後 grounding 回原始資料
- **例子**：知識圖（疾病–藥品–檢查）+ MRI 影像 + 病理報告，agent 可以「沿著圖走到 MRI 節點，看影像，再回來繼續推理」
- **enrichRAG 現況**：目前只處理文本和結構化資料，不涉及影像。如果未來要整合基因表達 heatmap、pathway diagram 等圖形資料，這個方向值得探索

---

### 0.5 Agent／系統工程流派

不再只是「一個 RAG 模組」，而是完整的 agent workflow。

#### Agentic RAG / Agent-driven RAG

- **做法**：Agent 動態控制整個流程——要不要查？查哪裡？需不需要多步？需不需要呼叫 API？
- **與 Multi-hop 的差異**：Multi-hop 是「固定拆 N 步」；Agentic 是「根據情況即時決定」
- **常見框架**：LangGraph、CrewAI、AutoGen、Claude tool use
- **enrichRAG 現況**：目前是固定 pipeline → Part 2 的 Agent 化方案就是往這方向走

#### Reasoning + Tool RAG

- **做法**：RAG 負責知識檢索，tool calling 負責計算和外部 API，LLM 整合兩者做推理
- **例子**：
  - RAG 查「某基因的表達數據在哪」
  - Python tool 跑統計分析（t-test、survival analysis）
  - LLM 用兩者結果做診斷建議
- **enrichRAG 現況**：⚠️ 部分具備——gseapy 富集分析就是一種 computational tool，但是寫死在 pipeline 裡，不是 agent 動態呼叫的

#### State-aware / Memory-augmented RAG

- **做法**：多輪對話中逐漸 refine，帶持久記憶，追蹤分析狀態
- **例子**：研究員連續分析 3 組基因，系統記住前兩次的結果，第三次能說「跟你上次分析的 pathway 有重疊」
- **enrichRAG 現況**：⚠️ 有 chat history 和 analysis history，但沒有跨 session 的記憶或結果比較功能

---

### 0.6 enrichRAG 在流派地圖上的位置

```
基礎層                    高階工程                   知識結構              Agent 系統
─────────────────────────────────────────────────────────────────────────────────────
                                                        │
Naive ─→ Hybrid ─→ Advanced ─→ Multi-hop               │              Agentic RAG
                      🔜            ⚠️                  │                  🔜
                                                        │
                   Router-based ──────────────── GraphRAG ──────── Reasoning+Tool
                      ✅                           ✅                   ⚠️
                                                        │
                                                        │           State-aware
                                                        │              ⚠️
```

**enrichRAG 的獨特定位**：不是傳統的「文件問答 RAG」，而是「**統計分析驅動的多源檢索 + 知識圖譜建構系統**」。我們跳過了 Naive RAG 階段（因為不需要向量 DB），直接從 domain-specific 的角度切入，結合了 Router-based + GraphRAG 的特性。

**下一步的自然演進**：
1. 補上 Advanced RAG 的品質層（reranking、compression）→ Part 1
2. 加入 Agent loop 讓系統能自主決策 → Part 2

---

## Part 1 — 從現有架構到進階 RAG

### 1.1 背景知識：RAG 是什麼

**RAG（Retrieval-Augmented Generation）** 的核心概念很簡單：

```
使用者提問 → 先去「檢索」相關資料 → 把資料跟問題一起丟給 LLM → LLM 根據資料回答
```

為什麼不直接問 LLM？因為 LLM 的知識有截止日期、會產生幻覺（hallucination）、不知道你的私有資料。RAG 透過「先查再答」來解決這些問題。

**Naive RAG**（最基本的做法）：
1. 把文件切成小段（chunk）
2. 每段用 embedding model 轉成向量，存進向量資料庫
3. 使用者提問時，把問題也轉成向量
4. 用 cosine similarity / dot product 找出最相關的 top-k 段落
5. 把這些段落塞進 LLM 的 prompt 裡，讓 LLM 回答

enrichRAG 做的事情**遠超 naive RAG**——我們不只是查向量資料庫，而是結合了統計分析（富集分析）、多來源檢索（PubMed、網路、知識圖譜）、結構化資訊提取、和圖譜建構。

---

### 1.2 enrichRAG 現有架構總覽

```
使用者輸入: 基因列表 + 疾病 context
         │
         ▼
┌─────────────────────────────────┐
│  Step 1: Gene Enrichment        │  gseapy ORA → GO + KEGG
│  統計分析，不是 AI              │  p-value 過濾 (≤0.05, ≥2 genes)
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Step 2: Query Planning         │  LLM 把富集結果分成 4 類 intent:
│  LLM 決定「要查什麼」          │  pathway / interaction / disease / therapeutic
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Step 3: Parallel Search        │  三路平行：
│  多來源檢索                     │  ├─ Tavily (網路搜尋, 3 results/query)
│                                 │  ├─ PubMed (NCBI Entrez, ≤20 abstracts)
│                                 │  └─ Local KG (SQLite, ≤500 relations)
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Step 4: Relation Extraction    │  LLM 從 PubMed abstract 提取：
│  結構化資訊提取                 │  entities (gene/disease/drug/pathway)
│                                 │  relations (upregulate/inhibit/treat/...)
│                                 │  SQLite cache by PMID（避免重複呼叫）
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Step 5: Graph Building         │  合併所有來源 → D3 JSON
│  知識圖譜建構                   │  { nodes[], edges[] }
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  Step 6: LLM Synthesis          │  生成 Markdown 分析報告
│  報告生成                       │  (Summary / Interpretation / Caveats / Hypotheses)
└─────────────────────────────────┘
```

**現有的品質控制機制：**

| 機制 | 位置 | 說明 |
|------|------|------|
| P-value 過濾 | enricher.py | 只保留統計顯著的富集結果 |
| URL 去重 | web_search.py | 跨 query 不重複抓同一網頁 |
| PMID 去重 | pubmed.py | 不重複抓同一篇論文 |
| Extraction Cache | extraction_cache.py | 同一篇 PMID 只呼叫一次 LLM |
| Relation 正規化 | relation_extractor.py | 50+ 種 LLM 輸出變體 → 9 種標準類型 |
| Edge 去重 | graph_builder.py | (source, target, relation, source_db, pmid) |
| KG 平衡取樣 | knowledge_graph.py | SQL window function 每個來源限量，避免單一來源壟斷 |
| Disease Boosting | knowledge_graph.py | 疾病相關結果優先排序 |
| Token 預算控制 | chat_context.py | 關係 ≤40 行、富集 ≤15 項、來源 ≤8 筆 |

---

### 1.3 我們已經做到的（對照業界技術）

| 業界技術 | enrichRAG 對應 | 成熟度 |
|----------|---------------|--------|
| Multi-retriever routing | ✅ query_planner 按 4 類 intent 路由至 Tavily / PubMed / KG | 完整 |
| GraphRAG | ✅ local KG (STRING, KEGG, Reactome, PubTator) + LLM relation extraction | 完整 |
| Hybrid retrieval | ⚠️ 部分有：KG = 結構化查詢、PubMed = 關鍵字、Tavily = 語意搜尋；但非同一 corpus 上的 vector + BM25 | 跨來源混合 |
| Query decomposition | ✅ 一個 query 拆成多個 SearchIntent，各自獨立檢索 | 完整 |
| Structured output | ✅ LangChain + Pydantic function calling，保證 LLM 輸出格式 | 完整 |
| Source attribution | ✅ 每條 relation 都帶 PMID / source_db，可追溯 | 完整 |
| Caching | ✅ 逐 PMID 快取 LLM extraction 結果 | 完整 |

---

### 1.4 改進方向總覽（快速比較表）

| # | 改進項目 | 解決什麼問題 | 實作難度 | 預期效果 | 建議優先序 |
|---|---------|-------------|---------|---------|-----------|
| A | Re-ranking | 垃圾 context 進 LLM → hallucination、浪費 token | 🟢 低 | 🔴 高 | ★★★ 第一 |
| B | Contextual Compression | PubMed abstract 太長，只有 1-2 句相關 | 🟢 低 | 🟠 中高 | ★★★ 第一 |
| C | Multi-hop Retrieval | 複雜問題需要多輪檢索才能回答完整 | 🟡 中 | 🔴 高 | ★★☆ 第二 |
| D | Retrieval Evaluation | 不知道檢索品質好不好，無法量化改進效果 | 🟡 中 | 🟠 中高 | ★★☆ 第二 |
| E | Embedding-based Retrieval | 目前只靠關鍵字和 KG 結構查詢，缺語意模糊匹配 | 🟡 中 | 🟠 中 | ★☆☆ 第三 |
| F | Adaptive Retrieval | 簡單問題也跑完整 pipeline，浪費資源 | 🔴 高 | 🟠 中 | ★☆☆ 第三 |

---

### 1.5 各改進項目細節

#### A. Re-ranking（重新排序）

**問題**：三個 retriever 回來的結果品質參差不齊。目前全部 concat 後直接丟給 LLM 做 extraction / synthesis，相當於把噪音一起餵進去。

**原理**：
```
目前:  Tavily 3篇 + PubMed 20篇 + KG 500條 → 全部進 LLM
改進:  Tavily 3篇 + PubMed 20篇 → cross-encoder 逐篇打分 → 只留 top-k → 進 LLM
```

Cross-encoder 跟一般的向量搜尋（bi-encoder）不同：它把 query 和 document **一起**輸入模型，能更精確判斷相關性，但速度較慢，所以適合對候選結果做「精排」。

**技術選型**：

| 方案 | 套件 | 模型 | 速度 | 品質 |
|------|------|------|------|------|
| Cross-encoder（推薦） | `sentence-transformers` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | ~50ms/篇 | 高 |
| LLM re-rank | 現有 `langchain-openai` | GPT-4o | ~500ms/篇 | 最高但貴 |
| Cohere Rerank API | `cohere` | `rerank-v3.5` | ~200ms/batch | 高 |

**建議實作**：

```python
# 新增 enrichrag/core/reranker.py
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2", top_k=10):
        self.model = CrossEncoder(model_name)
        self.top_k = top_k

    def rerank(self, query: str, documents: list[dict], text_key="abstract") -> list[dict]:
        pairs = [(query, doc[text_key]) for doc in documents]
        scores = self.model.predict(pairs)
        ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in ranked[:self.top_k]]
```

**插入位置**：`pipeline.py` Step 3 → Step 4 之間

**可行性**：🟢 高。`sentence-transformers` 是成熟套件，模型輕量（~80MB），不需要 GPU，CPU 推理即可。對現有 pipeline 改動極小——只需在 parallel search 結束後、relation extraction 開始前加一步。

**新增依賴**：`sentence-transformers`（會帶入 `torch`，注意 image size ~2GB）

**替代方案**：若不想引入 PyTorch，可用 Cohere Rerank API（需額外 API key），或直接用現有 GPT-4o 做 LLM-based rerank（較貴但零依賴）。

---

#### B. Contextual Compression（上下文壓縮）

**問題**：一篇 PubMed abstract 可能有 300 字，但跟 query 直接相關的可能只有 2-3 句。把整篇塞進 LLM prompt 既浪費 token 也引入噪音。

**原理**：
```
目前:  PubMed abstract (300字) → 整篇進 synthesis prompt
改進:  PubMed abstract (300字) → 壓縮器提取相關句子 (50字) → 進 synthesis prompt
```

**技術選型**：

| 方案 | 套件 | 說明 | 成本 |
|------|------|------|------|
| LLM Extractor（推薦） | `langchain` 內建 | `LLMChainExtractor` 用 LLM 提取相關段落 | ~$0.001/篇 |
| Embedding Filter | `langchain` 內建 | `EmbeddingsFilter` 用向量相似度過濾句子 | 免費（本地） |
| 自訂規則 | 無需額外套件 | 用正則/關鍵字只留含目標基因的句子 | 免費 |

**建議實作**：先用最簡單的「句子級關鍵字過濾」，效果不夠再升級到 LLM extractor。

```python
# enrichrag/core/compressor.py
def compress_abstract(abstract: str, genes: list[str], disease: str) -> str:
    """只保留提到目標基因或疾病的句子"""
    keywords = set(g.upper() for g in genes) | {disease.upper()}
    sentences = abstract.split(". ")
    relevant = [s for s in sentences if any(kw in s.upper() for kw in keywords)]
    return ". ".join(relevant) if relevant else abstract  # fallback: 全文
```

**插入位置**：`relation_extractor.py` 呼叫 LLM 前，或 `pipeline.py` 組裝 synthesis prompt 時。

**可行性**：🟢 高。最簡方案零依賴、零成本。LLM-based 方案可用現有的 `langchain` + `langchain-openai`。

**注意事項**：壓縮太激進可能丟失重要上下文（例如一個句子沒提到基因名但描述了關鍵機制）。建議保守處理，寧可多留不要少留。

---

#### C. Multi-hop Retrieval（多跳檢索）

**問題**：目前 pipeline 是單次檢索。如果第一輪結果不足以回答問題（例如某個基因的 therapeutic 資料很少），系統無法自動補查。

**原理**：
```
目前:  Plan → Search (一次) → Extract → Synthesize

改進:  Plan → Search → Extract → Evaluator ─┐
                                              │ 「某方向資料不足」
                                              ▼
                                   Refine Query → Search again → Extract → Synthesize
```

**技術選型**：

| 方案 | 套件 | 說明 | 複雜度 |
|------|------|------|--------|
| LLM Gap Detector（推薦） | 現有 `langchain-openai` | LLM 評估結果完整性，輸出缺口 | 中 |
| Self-RAG | 需自訂 | 每步都讓 LLM 決定「要不要再查」 | 高 |
| LangGraph Loop | `langgraph` | 用 conditional edge 實現「不夠就再查」 | 中 |

**建議實作（Phase 1 — 簡單版）**：

```python
# enrichrag/core/gap_detector.py
class GapDetector:
    """分析現有結果，找出資訊缺口"""

    def detect(self, query_plan, relations_df, sources) -> list[str]:
        # 檢查每個 intent 是否有足夠的 evidence
        gaps = []
        for intent in query_plan.intents:
            related_relations = relations_df[
                relations_df["evidence"].str.contains(intent.category, case=False, na=False)
            ]
            if len(related_relations) < 2:
                gaps.append(intent.category)
        return gaps
```

**Phase 2（LLM 版）**：讓 LLM 判斷「根據目前的 relations 和 sources，哪些方面的證據不足？」，輸出新的 search query，回到 Step 3 再跑一輪。

**可行性**：🟡 中。簡單版（規則）很容易做，但效果有限。LLM 版效果好但要處理 loop 的終止條件（最多跑幾輪？避免無限迴圈）。建議限制最多 2 輪。

**對現有架構的影響**：需要把 pipeline.py 的線性流程改成可回跳的結構。用 LangGraph 比較自然，或者簡單地在 `run_pipeline()` 裡加一個 `for round in range(max_rounds)` 迴圈。

---

#### D. Retrieval Evaluation（檢索品質評估）

**問題**：目前無法量化「檢索回來的資料品質如何」。沒有 metrics 就無法有信心地調參數或比較不同策略。

**建議的評估維度**：

| Metric | 衡量什麼 | 怎麼算 |
|--------|---------|--------|
| **Coverage** | 多少輸入基因在結果中被提到 | `len(mentioned_genes) / len(input_genes)` |
| **Source diversity** | 結果是否來自多個來源 | `entropy(source_db distribution)` |
| **Relevance** | 檢索結果跟 query 的相關性 | Cross-encoder score 的平均值 |
| **Faithfulness** | LLM 報告的內容是否有 source 支持 | LLM 自評或 NLI model |
| **Relation density** | 知識圖譜的連通性 | `edges / nodes` |

**技術選型**：

| 套件 | 說明 |
|------|------|
| `ragas` | 專門做 RAG evaluation 的框架，支持 faithfulness / relevancy / context precision |
| 自訂 metrics | 用上面的公式自己算，更輕量 |

**可行性**：🟡 中。自訂 metrics 很簡單；`ragas` 需要額外設置 ground truth。建議先實作 coverage 和 source diversity（零成本），再逐步加入 relevance（需 cross-encoder）。

---

#### E. Embedding-based Retrieval（向量語意檢索）

**問題**：目前 PubMed 用的是關鍵字搜尋，KG 用的是精確匹配。如果使用者用不同的措辭描述同一個概念（例如 "heart attack" vs "myocardial infarction"），可能會漏掉相關結果。

**技術選型**：

| 方案 | 套件 | 說明 |
|------|------|------|
| 對 PubMed abstracts 建向量索引 | `chromadb` / `faiss` + `sentence-transformers` | 把抓回來的 abstract 即時建 index |
| 對 KG edge evidence 建向量索引 | 同上 | 讓 KG 查詢也支持語意模糊匹配 |
| PubMed 用 BioSentVec | `sent2vec` | 生醫領域專用的 sentence embedding |

**可行性**：🟡 中。對「已抓回的結果」建即時向量索引很容易（幾十篇 abstract 用 chromadb in-memory 就夠）。但對整個 KG（幾百萬條）建索引需要離線處理，成本較高。

**建議**：短期內不急。目前的多來源策略已經有不錯的 recall。如果未來想加，優先對 PubMed abstracts 做，因為數量少且每次都是新抓的。

---

#### F. Adaptive Retrieval（自適應檢索）

**問題**：不管問題簡單還是複雜，都跑完整 6 步 pipeline。簡單問題（例如「TP53 是什麼？」）不需要富集分析和多來源檢索。

**原理**：
```
使用者提問 → Complexity Router → Simple:  直接查 KG + LLM 回答
                                → Medium: 跳過富集，只做檢索 + synthesis
                                → Complex: 完整 pipeline
```

**可行性**：🔴 低優先。enrichRAG 的主要使用場景本來就是「給一組基因做深度分析」，不太會收到「簡單問題」。現有的 `/api/chat` endpoint 已經可以處理簡單的追問。等有明確需求再做。

---

### 改進項目依賴關係

```
                   ┌─── A. Re-ranking ←── 基礎，其他項目受益
                   │
可以獨立做 ────────┤─── B. Compression
                   │
                   └─── D. Evaluation ←── 量化效果，驗證 A/B/C 的改進
                            │
                            ▼
                   ┌─── C. Multi-hop ←── 需要 evaluation 來判斷「夠不夠」
                   │
較長期 ────────────┤─── E. Embedding retrieval
                   │
                   └─── F. Adaptive retrieval
```

**建議路線**：A + B → D → C → 其餘

---

## Part 2 — 從 Pipeline 到 Agent

### 2.1 什麼是 Agent？跟 Pipeline 差在哪？

**Pipeline（管線）**：步驟固定，每次都照同一條路跑。像工廠的生產線。

**Agent（代理）**：有一個「大腦」（LLM）在每一步決定「接下來做什麼」。像一個研究員。

| 特徵 | Pipeline | Agent |
|------|----------|-------|
| 流程 | 固定：A → B → C → D | 動態：A → 判斷 → 可能 B 也可能 C → 判斷 → ... |
| 決策者 | 開發者（寫死在程式裡） | LLM（每步都在思考） |
| 靈活度 | 低（同一組輸入 → 同一條路） | 高（根據中間結果調整策略） |
| 可預測性 | 高（容易 debug） | 低（LLM 可能做出意外決定） |
| 適合場景 | 流程明確、輸入輸出固定 | 開放式問題、需要多輪探索 |

**enrichRAG 目前是 Pipeline**——流程固定、每步必跑。

**Agent 的最低門檻**：系統能根據中間結果，**自主決定下一個動作**（包括「不做」和「再做一次」）。

```
Pipeline:  「不管三七二十一，6 步全跑」
Agent:     「我看了第一輪結果，覺得 BRCA1 的資料夠了但 TP53 不夠，
             我決定針對 TP53 再查一輪 PubMed，這次用不同的關鍵字」
```

---

### 2.2 Agent 架構設計

核心理念：**enrichRAG 不需要自己變成 agent，而是成為 agent 的工具之一**。

```
┌─────────────────────────────────────────────────────────────┐
│                    Outer Agent (LLM Brain)                   │
│                                                             │
│  使用者：「幫我分析 BRCA1, TP53, EGFR 跟乳癌的關係，       │
│           特別想知道有沒有新的 therapeutic target」           │
│                                                             │
│  Agent 思考：                                               │
│  1. 這需要基因富集分析 → 用 enrichRAG.analyze              │
│  2. 使用者特別提到 therapeutic → 結果出來後要重點看這部分   │
│  3. 如果 therapeutic 資料不足 → 用 pubmed_search 補查      │
│  4. 最後用 enrichRAG.chat 做 grounded Q&A                   │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │enrichRAG │  │ PubMed   │  │   Web    │  │   PDF    │   │
│  │ analyze  │  │ Search   │  │  Search  │  │  Reader  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │enrichRAG │  │enrichRAG │  │  Code    │  │  File    │   │
│  │   chat   │  │ KG query │  │ Execute  │  │  Write   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.3 需要的 Skills / Tools

#### 核心 Tools（從 enrichRAG 暴露）

| Tool 名稱 | 對應現有功能 | 輸入 | 輸出 | 實作方式 |
|-----------|-------------|------|------|---------|
| `enrichrag_analyze` | `run_pipeline()` | genes, disease, pval | 完整 pipeline 結果 JSON | 包裝 `/api/analyze/stream` |
| `enrichrag_chat` | `/api/chat` | question + pipeline result | Grounded 回答 | 包裝 `/api/chat` |
| `enrichrag_kg_query` | `KnowledgeGraph.lookup()` | gene symbols | Relations list | 新增 API endpoint |
| `enrichrag_validate_genes` | `/api/genes/validate` | gene symbols | Validation result | 已有 |
| `enrichrag_gene_profile` | `/api/genes/{symbol}` | symbol | Gene metadata | 已有 |

#### 補充 Tools（外部能力）

| Tool 名稱 | 用途 | 套件 / 服務 | 為什麼需要 |
|-----------|------|------------|-----------|
| `web_search` | 即時搜尋最新資訊 | Tavily API / `langchain-tavily` | 查 enrichRAG pipeline 沒涵蓋到的資訊（新聞、clinical trial 更新） |
| `pubmed_search` | 針對性查特定論文 | Biopython `Entrez` | Agent 發現某方向資料不足時，自己補查 |
| `pdf_reader` | 讀取完整論文 PDF | `pymupdf` / `pdfplumber` | PubMed 只有 abstract，有時需要讀 full text |
| `code_executor` | 跑統計分析 | Python sandbox | 使用者想做額外的統計測試（例如 survival analysis） |
| `file_writer` | 輸出報告 | 檔案系統 | 把分析結果存成 PDF / Markdown / CSV |
| `plot_generator` | 產生圖表 | `matplotlib` / `seaborn` | 視覺化基因表達、pathway 等 |

#### Tool Description 的重要性

Agent 靠 **tool description** 學會什麼時候該用什麼工具。寫得好不好直接影響 agent 表現。

好的 tool description 包含：

```yaml
name: enrichrag_analyze
description: >
  Run a full gene enrichment analysis pipeline. Use this when the user provides
  a list of gene symbols and wants to understand their biological significance
  in a disease context. Returns enrichment results, literature evidence,
  knowledge graph relations, and an AI-generated analysis report.
  Do NOT use this for simple gene lookups — use enrichrag_gene_profile instead.
parameters:
  genes:
    type: array
    items: { type: string }
    description: "Gene symbols (e.g., ['BRCA1', 'TP53', 'EGFR'])"
  disease_context:
    type: string
    description: "Disease or condition to analyze against (e.g., 'breast cancer')"
  pval_threshold:
    type: number
    default: 0.05
    description: "Adjusted p-value cutoff for enrichment filtering"
```

三要素：
1. **什麼時候用**（"when the user provides a list of gene symbols"）
2. **什麼時候不要用**（"Do NOT use this for simple gene lookups"）
3. **會回傳什麼**（"Returns enrichment results, literature evidence, ..."）

---

### 2.4 實作路徑與技術選型

#### 方案比較

| 方案 | 框架 | 優點 | 缺點 | 適合場景 |
|------|------|------|------|---------|
| **A. MCP Server** | Model Context Protocol | 標準化協議；Claude / Cursor / 任何 MCP client 都能用；不需要自己寫 agent loop | 目前只有部分 client 支援；你不控制 agent 行為 | 讓現有 AI 工具直接呼叫 enrichRAG |
| **B. LangGraph Agent** | `langgraph` | 你們已用 LangChain，遷移成本低；可視化 graph；有 checkpoint | 學習曲線中等；較 opinionated | 自建完整 agent，需要精細控制流程 |
| **C. OpenAI Assistants** | OpenAI API | 最簡單，function calling 即用；內建 thread 管理 | 綁定 OpenAI；靈活度低 | 快速 prototype |
| **D. Claude Tool Use** | Anthropic API | 原生 tool_use；extended thinking 適合多步推理 | 需自己管 conversation loop | 用 Claude 作為 agent brain |

#### 建議路線：MCP Server（短期）→ LangGraph Agent（中期）

**短期（1-2 週）：建立 MCP Server**

把 enrichRAG 的 API 包成 MCP（Model Context Protocol）server。這樣任何支援 MCP 的 AI 工具（Claude Code、Cursor、Windsurf 等）都能直接呼叫你的 pipeline。

```
enrichRAG MCP Server
  ├─ Tool: analyze        → run_pipeline()
  ├─ Tool: chat           → grounded Q&A
  ├─ Tool: kg_query       → KG lookup
  ├─ Tool: validate_genes → gene validation
  └─ Resource: analysis_result → 最近一次分析結果
```

所需套件：`mcp`（Model Context Protocol Python SDK）

**MCP Server 範例結構**：

```python
# enrichrag/mcp_server.py
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("enrichrag")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="analyze",
            description="Run gene enrichment analysis pipeline...",
            inputSchema={
                "type": "object",
                "properties": {
                    "genes": {"type": "array", "items": {"type": "string"}},
                    "disease_context": {"type": "string"},
                },
                "required": ["genes", "disease_context"],
            },
        ),
        # ... 其他 tools
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "analyze":
        result = await run_pipeline(
            genes=arguments["genes"],
            disease=arguments["disease_context"],
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
```

**中期（1-2 月）：建立 LangGraph Agent**

在 MCP 的基礎上，自己建一個 agent loop，讓 LLM 能自主規劃多步研究流程。

```python
# enrichrag/agent/graph.py
from langgraph.graph import StateGraph, END

class ResearchState(TypedDict):
    query: str                    # 使用者原始問題
    plan: list[str]               # agent 規劃的步驟
    results: dict                 # 累積的分析結果
    gaps: list[str]               # 資訊缺口
    iteration: int                # 目前第幾輪
    final_answer: str             # 最終回答

def plan_step(state):
    """LLM 分析問題，決定需要哪些 tools"""
    ...

def execute_step(state):
    """執行 tools（analyze / search / kg_query）"""
    ...

def evaluate_step(state):
    """LLM 評估結果是否足夠"""
    ...

def synthesize_step(state):
    """產出最終報告"""
    ...

# 建構 graph
graph = StateGraph(ResearchState)
graph.add_node("plan", plan_step)
graph.add_node("execute", execute_step)
graph.add_node("evaluate", evaluate_step)
graph.add_node("synthesize", synthesize_step)

graph.set_entry_point("plan")
graph.add_edge("plan", "execute")
graph.add_edge("execute", "evaluate")
graph.add_conditional_edges(
    "evaluate",
    lambda state: "synthesize" if not state["gaps"] or state["iteration"] >= 3 else "plan",
)
graph.add_edge("synthesize", END)

agent = graph.compile()
```

**所需新增依賴**：

| 套件 | 用途 | 階段 |
|------|------|------|
| `mcp` | MCP server SDK | 短期 |
| `langgraph` | Agent graph framework | 中期 |
| `langgraph-checkpoint-sqlite` | Agent state persistence | 中期 |

---

### 2.5 完整使用情境範例

#### 情境：研究員想分析一組差異表達基因與阿茲海默症的關係

**使用者輸入**：
> 「我有一組 RNA-seq 差異表達基因：APP, PSEN1, PSEN2, APOE, TREM2, MAPT, CLU, BIN1。
> 幫我分析跟 Alzheimer's disease 的關係，特別想知道有沒有新的 drug target。」

**Agent 執行過程**：

```
🤔 Agent 思考 (Step 1):
   使用者提供了 8 個基因 + 疾病 context + 特別要求看 therapeutic
   → 先跑完整的 enrichRAG pipeline

🔧 Agent 行動: enrichrag_analyze(
     genes=["APP","PSEN1","PSEN2","APOE","TREM2","MAPT","CLU","BIN1"],
     disease_context="Alzheimer's disease"
   )

📊 Agent 收到結果:
   - GO enrichment: amyloid-beta formation, tau phosphorylation, ...
   - 12 relations extracted, 但只有 1 條是 therapeutic 相關
   - Graph: 45 nodes, 67 edges

🤔 Agent 思考 (Step 2):
   使用者特別問 drug target，但 therapeutic 資料只有 1 條不夠。
   TREM2 最近有很多 clinical trial，但 pipeline 結果裡沒提到。
   → 針對 TREM2 therapeutic 補查 PubMed

🔧 Agent 行動: pubmed_search(
     query="TREM2 therapeutic target Alzheimer clinical trial 2024-2026"
   )

📊 Agent 收到: 5 篇新論文，其中 2 篇提到 anti-TREM2 antibody trials

🤔 Agent 思考 (Step 3):
   有一篇提到 Phase 2 結果，我想看完整 PDF 確認數據
   → 讀取 PDF

🔧 Agent 行動: pdf_reader(url="https://...")

📊 Agent 收到: Phase 2 trial 的完整數據

🤔 Agent 思考 (Step 4):
   現在資料夠了，用 enrichRAG chat 做 grounded synthesis

🔧 Agent 行動: enrichrag_chat(
     question="Based on the analysis and the additional TREM2 therapeutic data,
               what are the most promising drug targets?",
     context=<pipeline_result + supplementary_papers>
   )

📝 Agent 最終輸出:
   一份結合 pipeline 結果 + 補充文獻的完整報告，
   特別標注了 TREM2 作為 therapeutic target 的最新 clinical evidence。
```

**對比 Pipeline（現在）會怎麼做**：

```
Pipeline:  跑完 6 步 → 輸出報告 → therapeutic 資料不足就是不足，使用者自己去補查
Agent:     跑完 6 步 → 發現不足 → 自動補查 → 綜合所有資料輸出報告
```

---

## 附錄

### A. 術語對照表

| 英文 | 中文 | 白話解釋 |
|------|------|---------|
| RAG | 檢索增強生成 | 先查資料再讓 AI 回答 |
| Embedding | 向量嵌入 | 把文字轉成一串數字，方便計算相似度 |
| Cross-encoder | 交叉編碼器 | 把 query 和 document 一起輸入模型打相關性分數 |
| Re-ranking | 重新排序 | 用更精準的方法對搜尋結果重新排序 |
| Hallucination | 幻覺 | AI 一本正經地胡說八道 |
| Context window | 上下文視窗 | LLM 一次能「看到」的文字量上限 |
| Token | 詞元 | LLM 處理文字的最小單位，大約 1 個中文字 ≈ 1-2 tokens |
| MCP | Model Context Protocol | 讓 AI 工具呼叫外部服務的標準協議 |
| Tool / Function calling | 工具呼叫 | LLM 根據需要自動呼叫外部工具 |
| Agent loop | 代理迴圈 | 觀察 → 思考 → 行動 → 觀察 → ... 的循環 |
| Structured output | 結構化輸出 | 讓 LLM 輸出固定格式的 JSON/object |
| Multi-hop | 多跳 | 需要多次檢索、逐步推理才能回答的問題 |

### B. 參考資源

- [LangGraph 官方文件](https://langchain-ai.github.io/langgraph/) — Agent graph framework
- [MCP 規範](https://modelcontextprotocol.io/) — Model Context Protocol
- [RAGAS](https://docs.ragas.io/) — RAG evaluation framework
- [Sentence Transformers](https://www.sbert.net/) — Cross-encoder re-ranking
- [LangChain Contextual Compression](https://python.langchain.com/docs/how_to/contextual_compression/) — 上下文壓縮
