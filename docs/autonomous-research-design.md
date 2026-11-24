# enrichRAG 自主研究能力設計

> 撰寫日期：2026-05-19
> 延續：[rag-advancement-and-agent-research.md](./rag-advancement-and-agent-research.md)
> 範疇：把「pipeline 結果不夠好」這個模糊問題拆成可動手的設計

---

## 起點：問題定位

目前 enrichRAG 是固定 6 步 pipeline，使用者體感的弱點常被描述為「報告不夠強」。但根本原因通常**不是 synthesis prompt 寫得不好**，而是：

1. Pipeline 跑完之後沒有「自我檢查」機制 — 不知道結果完整度
2. 使用者透過 chat 追問時，系統只能用 pipeline 留下的舊 context 答題，**沒有補查能力**

這兩個問題**獨立**，應該分開處理。

---

## 兩層架構

| | Layer 1: Baseline 計分 | Layer 2: Chat 補查 |
|---|---|---|
| **觸發時機** | Pipeline 跑完 Step 5 之後 | 使用者在 chat 提問時 |
| **知不知道使用者意圖** | 不知道（只有 genes + disease） 
| 知道（問題本身就是意圖） |
| **「夠」的定義** | 結構性指標 | 「能否回答這個具體問題」 |
| **失敗的後果** | 報告品質警示 | Chat 回答不出來或瞎掰 |
| **是不是 agentic** | 不是，純規則 metrics | 是，agent 入口 |

兩層的關鍵差別：Layer 1 **不**主動補查（因為不知道往哪個方向補），只負責**標記缺口讓使用者知道**；Layer 2 由使用者的具體問題驅動補查方向。

---

## Layer 1: Baseline 計分

### 目的
Pipeline 跑完當下，給使用者一個「本次分析完整度」的客觀視角，並讓開發團隊有 metrics 可以**量化比較不同改進的效果**。

「完整度」包含兩個面向：
- **Input quality**：search 階段抓回的資料是否充足、多樣、連貫
- **Output quality**：報告本身是否忠實使用了抓回的資料、claim 是否有 source 支持

兩個面向都要量，缺一不可。

### 不做什麼
- **不**自動觸發補查（baseline 沒有方向訊號）
- **不**用 LLM 打分（純計算就夠，LLM judge 留給 Layer 2）
- **不**用來 block 報告生成（只是補充資訊）

### Input Quality 指標（三個）

#### Gene Coverage（基因覆蓋）
列出輸入基因中**沒有出現在 relations 表**的，當作警示資訊。

- 不當 pass/fail 硬指標 — 有些基因本來文獻就少
- 進階版：先查該基因在 KG 中是否有任何收錄，沒收錄的標 `low-prior`，不算系統失敗
- 顯示形式：報告底部「本次分析中以下基因證據較少：XXX、YYY（可透過 chat 追問補充）」

#### Source Diversity（來源多樣性）
避免單一資料庫壟斷整張圖。

- 我們有 6 個來源：STRING、KEGG、Reactome、PubTator、PubMed extraction、Tavily
- 計算：`max(每個 source 的 relations 數) / 總數`
- 警示閾值：> 60%
- 為什麼重要：若 80% 都是 STRING (PPI)，整張圖只反映蛋白質互動，pathway/therapeutic 面向缺席

#### Graph Connectivity（圖連通性）
衡量基因之間有沒有被串成 coherent story。

- Connected component = 圖裡互相能走到的一群節點
- 8 個基因都互相連 → 1 個 component（理想）
- 5+3 兩團獨立 → 2 個 components（可接受）
- 各自孤立 → 8 個 components（差）
- 警示閾值：> 2

### Output Quality 指標（四個）

**前提**：以下指標都需要報告已改成 claim 結構（見「報告結構改造」一節）。沒有 claim 結構就無法計算，這也是為什麼報告結構化排在 Phase 1。

#### Faithfulness（忠實度）
有 source 支持的 claim 佔比。

- 計算：`claims_with_sources / total_claims`
- 警示閾值：< 95%（即至少 95% 的 claim 要有 source）
- 0 source 的 claim = 幻覺風險
- v2 可加 LLM 二次驗證：source 是否真的支持那條 claim（NLI 或 LLM judge）

#### Evidence Utilization（證據使用率）
報告引用的 unique sources 數 ÷ pipeline 抓回的 unique sources 數。

- 低 = 抓回一堆資料但報告沒用上，浪費 token 也浪費抓取成本
- 目標：> 50%
- 過低時的可能原因：synthesis prompt 沒讀完整個 context，或 context 太長被截斷

#### Citation Density（引用密度）
每條 claim 平均引用幾個 source。

- 計算：`sum(sources per claim) / total_claims`
- 越高 = 多來源交叉驗證，可信度越高
- 目標：≥ 1.5（平均每條 claim 至少 1.5 個 source）

#### Claim Specificity（具體度）
每條 claim 提到幾個具名實體（gene / pathway / drug / PMID / 數值）。

- 計算：對每條 claim 用簡單 NER 或關鍵字統計實體數
- 低 = 空泛敘述（「BRCA1 跟疾病有關」）；高 = 具體可驗證（「BRCA1 透過 HR pathway 影響 PARP inhibitor 反應，見 PMID 12345」）
- 目標：平均每條 claim ≥ 2 個具名實體

### 用途
- 報告底部加一個「分析完整度」區塊，顯示 input + output 共 7 個指標的具體數值
- **跨版本比較**：改 pipeline 任何一步之後，跑同樣 case，看 metrics 有沒有變好 — 這是整套設計的目的函數
- 不做自動補查決策（補查是 Layer 2 的事）

---

## Layer 2: Chat 觸發的補查

### 目的
讓 chat 不只是「在現有 context 上做 grounded Q&A」，而是能**判斷現有 state 不足以回答 → 自主補查 → 把新證據加進 state → 再答**。

### 設計決策

#### A. 「能否回答」由 LLM 判斷
小型 LLM judge prompt：
```
給定以下 claims（含 source）和使用者問題：
- 現有 claims 是否能完整支持回答？
- 如果不能，缺什麼維度的證據？輸出補查方向。
```

走 LLM 判斷而非規則的原因：chat 問題太多樣，規則寫不完。

**前提**：這個 judge 能運作的關鍵是報告本身要先**結構化成多條 claim**（見下方「報告結構改造」）。

#### B. 多 view 設計
補查回來的東西要寫回 graph，但需要可區分：

- **View 1: Pipeline Snapshot** — 原始分析結果，不可變
- **View 2: Enriched** — 加上 chat 補查累積的新節點/邊，用不同顏色或樣式標記
- （未來可選）**View 3: Per-Question** — 只看某次 chat 追問補進來的子集

UI 提供切換按鈕，預設顯示 Enriched（最新狀態），但使用者可以回看原始版本對照。

#### C. 補一次不夠就誠實認輸
一個 chat turn **最多觸發一次補查**。理由：
- 避免單一問題引爆連鎖 API 呼叫
- 避免無限 loop 的終止條件設計
- 補完還是答不出 → 老實告訴使用者「目前文獻證據不足以回答這個問題」

這是 UX 取捨：寧可少做也不要過度承諾。

#### D. 思考路徑透明化
補查過程要透過 SSE stream 即時顯示（跟現在 pipeline 進度動畫同樣機制）：

```
🤔 評估現有證據是否能回答：「TREM2 有沒有 phase 2 臨床試驗？」
   → 現有 12 條 relations 中只有 1 條提及 TREM2 therapeutic
   → 判定：證據不足，需補查
🔍 補查方向：TREM2 clinical trial Alzheimer 2024-2026
   → PubMed 抓回 5 篇新 abstract
   → 抽出 3 條新 relations，加入 graph
✍️ 重新組合回答...
```

理由：建立信任 + 讓使用者能在中途中斷或修正方向。

---

## 關鍵子議題：報告結構改造（最優先）

這個原本被列為 Phase 2，但討論中釐清它其實是**整套改造的前提**，應該最優先實作。理由見下方「為什麼這是 Phase 1」。

### 現況
Synthesis 產出的是**敘事 Markdown**（Summary / Interpretation / Caveats / Hypotheses 四個段落），source 引用混在文字裡。

### 問題
Layer 2 的 LLM judge 要判斷「現有聲明能不能回答 X」，但**敘事文章無法逐條檢查支持度**。如果一段話講了 3 個論點，其中 1 個有 source、2 個沒有，judge 沒辦法精確指認缺口。

### 改造方向
報告改成 **claim-based + 來源標註** 結構：

```markdown
## Summary
- **Claim**: APP 和 PSEN1 共同參與 amyloid-beta precursor processing pathway
  Sources: [STRING], [KEGG hsa05010], [PMID: 12345678]
- **Claim**: TREM2 變異與 microglia 功能異常相關
  Sources: [PMID: 23456789], [PubTator: TREM2-microglia co-occurrence]

## Therapeutic Implications
- **Claim**: Anti-TREM2 antibody 為目前主要 drug development 方向
  Sources: [PMID: 34567890]
  Confidence: low (僅 1 篇 abstract 支持)
- ...
```

### 帶來的好處
1. **報告品質可量化**：沒有 claim 結構就無法計算 faithfulness / citation density / evidence utilization（見下節）— 這是「沒有它就無法評估系統有沒有變好」的關鍵
2. **Chat judge 能 tractable 運作**：逐條檢查 claim 的 source 是否回答得了問題
3. **可追溯性大幅提升**：使用者點 source 標籤直接跳 PMID
4. **品質視覺化**：confidence 標記讓使用者看到「哪些 claim 證據強、哪些弱」
5. **天然的補查目標**：弱 confidence 的 claim 就是補查候選

### 為什麼這是 Phase 1
原本的順序是「先做 baseline metrics，再改報告結構」。但仔細想：
- Baseline metrics 只能量「search 階段抓回多少資料」（input quality）
- 但**完全量不到「報告有沒有用上這些資料」「報告講的東西有沒有 source 支持」**（output quality）
- 而 output quality 才是使用者真正感知到的「報告好不好」
- 沒有 claim 結構，output quality 永遠不可量化 → 任何後續改進都只能憑感覺說「好像比較好」

所以 claim 結構化是整套量化體系的基礎，必須最先做。

### 代價
- Synthesis prompt 要重寫（structured output 而非自由敘事）
- 前端要做 claim 的渲染（不是純 markdown）
- 報告整體可讀性可能下降（從散文變條列）— 可考慮在 UI 提供「敘事 / claim」兩種顯示模式

---

## 實作順序

### Phase 1: Baseline Metrics（1-2 天）
- 實作三個指標計算函式
- 在 pipeline.py 結束時呼叫，結果寫進 SSE 訊息和最終結果 JSON
- 前端在報告底部加「分析完整度」區塊
- **不**做任何自動補查邏輯

**驗收**：跑現有的測試 case，能看到具體數字，能感受到哪些 case 分數低。

### Phase 2: 報告結構改造（3-5 天）
- 改 `enrichment_analysis.yaml` prompt → structured output
- 定義 claim schema（claim text、sources[]、confidence）
- 改 synthesis 呼叫處用 Pydantic 接 structured output
- 前端報告 component 重寫支援 claim 渲染
- 保留 fallback：舊敘事格式作為 alternative view

**驗收**：報告每條 claim 都有 inline source、可點擊跳 PMID。

### Phase 3: Chat 補查能力（5-7 天）
- LLM judge prompt：給 claims + 問題 → 判斷夠不夠 + 缺口方向
- 補查執行：reuse 現有 PubMed / Tavily / KG 模組
- State 增量寫回：新 relations 加進 graph，標記 `source_type: chat_supplement`
- Frontend 多 view 切換 UI
- SSE 思考路徑 stream

**驗收**：使用者問一個現有 context 答不出的問題，系統會自己補查並把新證據顯示在 graph 上。

---

## 開放問題

以下決策還沒拍板，實作前要先想清楚：

1. **State 資料結構**：補查回來的 relations 怎麼合進現有 `result.relations` 表？另開欄位還是 union 後加標記欄？
2. **Judge prompt 設計**：要 few-shot 還是 zero-shot？輸出 JSON schema 怎麼定？
3. **思考路徑的詳細程度**：要 stream 每個內部步驟，還是只 stream 關鍵節點（避免噪音）？
4. **Confidence 怎麼算**：純 source 數量？還是再加 source quality（KG > PubMed extraction > Tavily）？
5. **Claim 渲染 vs 敘事的 UI 取捨**：預設哪個？切換還是並列？
6. **補查 budget**：一個 chat turn 最多花多少 API 成本？要不要顯示給使用者？
7. **Gene Coverage 的 low-prior 判定**：怎麼定義「這個基因本來就沒資料」？查 KG 收錄 vs 查 PubMed hit count vs 兩者都查？

---

## 跟 Part 2 (Agent 化) 的關係

這份設計**不是**完整的 agent 化，但 Layer 2 是往 agent 走的第一步：

- 仍然是「pipeline + chat 補查」兩段式結構，不是 LangGraph 那種全 agent loop
- LLM 只決定「要不要補、補什麼」，不決定「整體流程怎麼跑」
- 把 chat 補查做穩之後，再考慮把 pipeline 本身也 agentic 化

理由見 [rag-advancement-and-agent-research.md](./rag-advancement-and-agent-research.md) Part 2 的階段建議：先 MCP server → 再 LangGraph agent。本設計屬於 MCP server 階段之前的內部增強。
