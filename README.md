# EnrichRAG

**EnrichRAG is a modular framework that performs canonical gene set enrichment and extends it with literature-augmented integration and interpretation.**

---

## 1. 問題定義（Problem Statement）

### 核心問題

給定一組基因（gene set），研究者希望知道：

1. 這組基因在**哪些生物功能／路徑中顯著富集**
2. 不同資料庫（GO、KEGG…）的結果是否**一致或互補**
3. 是否存在**文獻支持的隱含關聯**，解釋這些富集結果的生物學脈絡

### 現有方法的限制

* 傳統 enrichment（ORA / GSEA）：

  * 結果分散在多個資料庫
  * 缺乏整合與語境解釋
* 文獻閱讀：

  * 高成本、不可重現
* LLM 直接生成：

  * 缺乏可驗證的基礎結果

---

## 2. 系統目標（Design Goals）

EnrichRAG 的設計目標是：

1. **標準化**：以 canonical enrichment（GO / KEGG）作為基礎
2. **可整合**：跨資料庫整合 enrichment 結果
3. **可擴充**：未來可加入文獻與 RAG，但不破壞核心 API
4. **可解釋**：每一步都有清楚的輸入、輸出與假設

---

## 3. 系統整體架構（High-level Architecture）

```
Input: gene_set
   │
   ▼
[ Enrichment Layer ]
   ├── GO ORA
   ├── KEGG ORA
   │
   ▼
[ Integration Layer ]
   ├── term aggregation
   ├── gene coverage
   ├── cross-database consensus
   │
   ▼
[ (Optional) Interpretation Layer ]
   ├── literature retrieval
   ├── graph expansion
   └── RAG-based explanation
```

**第一版（v0.1）只實作前兩層**。

---

## 4. 模組級規格（Module Specifications）

---

### 4.1 Enrichment Layer

**Canonical Pathway Enrichment**

#### 功能

對輸入 gene set 執行標準 ORA。

#### 方法

* Statistical test：Hypergeometric / Fisher’s exact test
* Multiple testing correction：BH-FDR
* Background：user-defined 或預設全基因集合

#### 輸入

```text
gene_set: List[str]
```

#### 輸出（每個資料庫）

```json
[
  {
    "term_id": "GO:0006915",
    "term_name": "apoptotic process",
    "p_value": 1e-4,
    "adj_p_value": 1e-3,
    "genes": ["TP53", "BAX", "CASP3"]
  }
]
```

#### 專有名詞

> **Over-Representation Analysis (ORA)**
> **Canonical pathway databases**

---

### 4.2 Integration Layer

**Cross-database Enrichment Integration**

#### 功能

將多個 enrichment 結果整合為統一、可比較的結構。

#### 核心概念

* **Gene coverage**

  ```
  coverage = |genes ∩ input_gene_set|
  ```
* **Source annotation**（GO / KEGG / …）
* **Ranking normalization**

#### 輸入

```json
{
  "GO": [...],
  "KEGG": [...]
}
```

#### 輸出（統一格式）

```json
{
  "GO": [
    {
      "term_id": "...",
      "term_name": "...",
      "adj_p_value": ...,
      "genes": [...],
      "coverage": 3,
      "source": "GO"
    }
  ],
  "KEGG": [...]
}
```

#### 可擴充功能（未來）

* GO ↔ KEGG term overlap
* semantic similarity
* meta-enrichment score

#### 專有名詞

> **Meta-enrichment**
> **Gene coverage-based ranking**

---

## 5. 核心 API 規格（最重要）

### 5.1 主入口函數

```python
enrich(gene_set: List[str]) -> EnrichmentReport
```

#### 行為定義

1. 執行所有 canonical enrichment
2. 整合結果
3. 回傳結構化結果（不產生文字敘述）

---

### 5.2 EnrichmentReport（概念 schema）

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

這個 schema **未來不可破壞**，只可擴充。

---

## 6. Interpretation Layer（v0.2+，先定義不實作）

### 目的

回答 enrichment 本身無法回答的問題：

> 「這些 pathway 為什麼會一起出現？」

### 子模組（規劃）

1. **Literature retrieval**

   * PubMed abstract search
2. **Gene–gene interaction graph**

   * Co-occurrence / polarity-aware edges
3. **k-hop neighborhood expansion**
4. **RAG-based explanation**

#### 專有名詞

* Literature-derived gene network
* Retrieval-augmented biological interpretation

---

## 7. 版本里程碑（Roadmap）

### v0.1 — Canonical Enrichment Core

* enrich()
* GO + KEGG ORA
* integration schema

### v0.2 — Structured Interpretation

* rule-based summaries
* GO/KEGG overlap analysis

### v0.3 — Literature Augmentation

* PubMed retrieval
* gene interaction graph

### v1.0 — EnrichRAG

* Full RAG explanation layer
* Reproducible interpretation reports
