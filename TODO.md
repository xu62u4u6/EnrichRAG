這是一份根據我們剛剛討論的 **Graph-RAG 架構 (v0.2/v0.3)** 所完善的 TODO 清單。我特別為你補充了你要求的 **關係提取表 (Relation Table)** 與 **多體學鄰接矩陣 (Multi-omics Adjacency Data)** 的具體範例。

### 📌 Updated Project TODO: EnrichRAG

#### **Main Framework (v0.1 - Completed)**

- [x] **GeneEnricher**: ORA analysis (GO/KEGG)
- [x] **PromptGenerator**: Basic XML-based prompting

#### **Retrieval (v0.2 - In Progress)**

* [ ] **LLM Integration**: Connect `PromptGenerator` output to GPT-4/Claude API.
* [ ] **Web Search function**: Implement Tavily/Google Search tool for latest clinical infomations.

#### Graph
* [ ] Merge with PPI graph neighbors (StringDB/BioGRID).
* [ ] PubMed knowledge graph neighbors.

#### **The "PubMed knowledge graph" Module**

* [ ] **Crawl/Retrieve PubMed Abstracts**
* [ ] **Extract Gene Relation (LLM-based Extraction)**
* [ ] Design Extraction Prompt (Few-shot).
* [ ] **Table Example (Output Schema):**
*(這是 LLM 讀完摘要後要輸出的標準格式，對應你筆記中的 Tokenize)*


    | Source Gene | Target Gene | Relation (Sign) | Omics Layer | Confidence | Evidence Fragment |
    | --- | --- | --- | --- | --- | --- |
    | **TP53** | **EGFR** | **+** (Upregulate) | **RNA** (mRNA Exp) | High | "...mutations significantly upregulate EGFR expression..." |
    | **RBM10** | **MYC** | **-** (Inhibit) | **DNA** (Transcription) | High | "...binds to promoter inhibiting transcription..." |
    | **KRAS** | **PI3K** | **+** (Bind) | **Protein** (Phospho) | Medium | "...physically interacts with PI3K..." |
* [ ] merge table & integration
* [ ] **Multi-Omics Adjacency Matrix Construction**
* [ ] Convert extraction table to Graph Edges.
* [ ] **Data Structure Example (NetworkX Edge List):**
*(這就是你的 "Matrix" 在程式中的實際長相，支援多層級屬性)*


    ```python
    # MultiDiGraph (多重有向圖) 結構範例
    edges = [
        # (Source, Target, {Attributes})
        ("TP53",  "EGFR", {"sign": 1,  "layer": "RNA", "weight": 0.9}),
        ("RBM10", "MYC",  {"sign": -1, "layer": "DNA", "weight": 0.85}),
        ("TP53",  "MYC",  {"sign": -1, "layer": "Protein", "weight": 0.4}) 
    ]
    # 轉為 Matrix 時，這會是一個三維張量 (N x N x Layers) 或帶有屬性的稀疏矩陣

    ```
* [ ] 使用 `NetworkX` (記憶體內) 或 `Neo4j` (持久化) 建立圖譜。

### Find N neighbors module
* [ ] Insert genes to Graph Database
* [ ] **Find N Neighbors (Graph Algorithm)**
* [ ] Implement `ego_graph(radius=N)` to find local network.
* [ ] Implement `PageRank` or `Degree Centrality` to filter top critical neighbors.
* [ ] Random walk?