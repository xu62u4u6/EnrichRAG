## EnrichRAG UI 問題分析

以下是逐頁自動化操作後，整理出的 **UI 問題** 與 **模板感過重** 的原因：

***

### 一、UI 問題（功能/視覺缺陷）

#### 1. Navbar Tab 截斷 — SOURCES 與 INSIGHT REPORT 無法完整顯示 [140.129.69](http://140.129.69.143:9001/test0948395013/)
Results 頁面底部的子 tab bar（PIPELINE / GENES / ENRICHMENT / SOURCES / NETWORK / INSIGHT REPORT）在 375px 寬度下會被截斷，最後幾個 tab 只顯示部分文字（如「INSIGHT REPO…」），且沒有橫向滾動提示，使用者很難發現更多 tab 的存在。

#### 2. Enrichment 表格欄位被截斷 [140.129.69](http://140.129.69.143:9001/test0948395013/)
ENRICHMENT 子頁面的 table 欄位（TERM / OVERLAP / P-VALUE / ADJ. P-VALUE / **C...**）最後一欄被截斷，內容無法完整閱讀，且沒有橫向滾動條可見提示（scroll bar 很細且隱藏）。

#### 3. Gene Validation 表格同樣有截斷問題 [140.129.69](http://140.129.69.143:9001/test0948395013/)
GENES 子頁面的 Gene Validation table，SOURCE 欄位顯示不全（只看到 `ncbi_sy…`），使用者無法在不滑動的情況下讀到完整內容，且缺乏視覺提示（如陰影或箭頭）表示右側還有更多內容。

#### 4. p-value 數值顯示精度異常 [140.129.69](http://140.129.69.143:9001/test0948395013/)
`P-VALUE THRESHOLD` 的實際 input value 為 `0.05000000074505806`（浮點數精度問題），雖然畫面上顯示 `0.05`，但底層 DOM 值有問題，可能在傳遞到後端時造成誤差。

#### 5. 頂部 header 缺乏功能分群 [140.129.69](http://140.129.69.143:9001/test0948395013/)
Header 區塊有 logo + 名稱左對齊，右側只有一個「登出」icon button（`→` 箭頭），沒有 tooltip，辨識度低，使用者難以直覺判斷這是登出功能。

#### 6. History 頁的刪除按鈕（垃圾桶）無確認機制感 [140.129.69](http://140.129.69.143:9001/test0948395013/)
每筆歷史紀錄都有刪除按鈕，且頁頂有「CLEAR HISTORY」按鈕，但兩者沒有任何視覺上的危險提示（紅色、警告色等），容易誤觸且無二次確認提示。

#### 7. Pipeline Execution 步驟視圖缺乏時間資訊 [140.129.69](http://140.129.69.143:9001/test0948395013/)
Pipeline 流程圖（ENRICHMENT → PLANNING → PARALLEL RETRIEVAL → EXTRACTION → SYNTHESIS → REPORT）每個節點只顯示 icon + 名稱，沒有執行時間或狀態 timestamp，對研究者來說難以判斷哪個步驟最耗時。

#### 8. "ANALYSIS COMPLETE" badge 與頁面標題視覺層級混亂 [140.129.69](http://140.129.69.143:9001/test0948395013/)
Results 頁面頂部同時有：`ANALYSIS COMPLETE`（小綠字 badge）→ `cancer`（大 h1 標題）→ `Targeting 12 genes`（副文字），這三層資訊視覺重量排列不自然，`cancer` 反而比分析狀態更突出，容易讓使用者誤認「cancer」是頁面的主 action，而非 context 輸入值。

***

### 二、模板感過重的原因

#### 1. 全站使用標準 monochrome 設計語言，無品牌個性化 [140.129.69](http://140.129.69.143:9001/test0948395013/)
整體配色為純白背景 + 黑色文字 + 少量灰色邊框，按鈕、卡片、分隔線全部遵循同一個極簡模板，缺乏任何能讓人記住「這是 EnrichRAG」的品牌色調或視覺錨點。

#### 2. 按鈕樣式千篇一律 [140.129.69](http://140.129.69.143:9001/test0948395013/)
`VALIDATE GENES`、`RUN PIPELINE`、`ASK ASSISTANT`、`COPY`、`JSON` 全部為同樣的全寬矩形 outlined/filled 按鈕，字體大小、間距完全一致，沒有依照功能重要性做視覺差異化（primary / secondary / tertiary 層級模糊）。

#### 3. 統計數字卡片（KPI cards）是典型 dashboard 模板套件風格 [140.129.69](http://140.129.69.143:9001/test0948395013/)
「12 INPUT GENES」、「108 ENRICHED TERMS」、「521 RELATIONS」、「20 SOURCES」這四張 KPI card，使用大數字 + 小標題 + icon 的佈局，幾乎是 Tailwind UI / shadcn / Material Dashboard 的標準 stat widget，缺乏任何與生物資訊分析場景相符的視覺元素。

#### 4. Label 全部使用 ALL CAPS 小字的 overline 樣式 [140.129.69](http://140.129.69.143:9001/test0948395013/)
`GENE SYMBOLS`、`DISEASE CONTEXT`、`P-VALUE THRESHOLD` 等 form label 全部使用 tracking-widest 的全大寫細字，是典型後台模板 UI 的 label 設計慣例，缺乏設計主體性。

#### 5. Pipeline 流程步驟卡片是 stepper/wizard 套件的直接套用 [140.129.69](http://140.129.69.143:9001/test0948395013/)
PIPELINE 頁的各步驟（圓形 check icon + 標題 + 副標題）是標準的 stepper component，沒有根據 RAG pipeline 的特殊性（如平行執行的 PARALLEL RETRIEVAL 群組）做有意義的視覺差異化，仍用同樣的單一樣式呈現。

#### 6. Insight Report 樣式缺乏信息密度設計 [140.129.69](http://140.129.69.143:9001/test0948395013/)
INSIGHT REPORT 頁的內容完全是純文字（h1 + h2 + bullet list），與一個基本的 Markdown renderer 渲染結果無異，沒有任何圖表、highlight 區塊、或與 enrichment 資料動態連結的互動元素，顯得像模板化的文字輸出。

***

### 總結建議優先順序

| 優先 | 問題 |
|------|------|
| 🔴 高 | Tab bar 截斷（SOURCES / INSIGHT REPORT 不可見） |
| 🔴 高 | Table 欄位截斷（無明確橫向滾動提示） |
| 🟡 中 | CLEAR HISTORY / 刪除無確認機制 |
| 🟡 中 | 登出按鈕缺乏 tooltip |
| 🟢 低 | KPI card、按鈕、pipeline 樣式的品牌個性化 |


## 解決方案
這份分析非常精確，直接戳中了目前許多 AI/生物資訊工具在從「功能原型 (MVP)」轉向「專業產品」時常見的痛點：過度依賴 UI 組件庫導致的視覺疲勞與響應式佈景的細節缺失。針對你提出的問題，我將解決方案分為「交互功能修復」與「品牌感去模板化」兩個維度來執行：一、 核心交互與佈局修復（解決 🔴高/🟡中 優先級問題）1. 解決導覽與表格截斷 (Tab/Table Overflow)在行動端或窄螢幕下，單純的截斷是致命的。導覽列 (Tabs)： 引入 「漸變遮罩 (Gradient Fade)」。在右側加入一個由透明轉白色的漸變，暗示右側還有內容，並啟用底層的 overflow-x: auto。更好的做法是檢測到截斷時顯示一個小的「向右箭頭」。表格 (Tables)： 實施 「首欄固定 (Sticky First Column)」。確保 TERM 或 GENE SYMBOL 在橫向滾動時始終可見，並在滾動區域邊緣加入動態陰影（Box-shadow），讓使用者直覺感知滾動深度。2. 修正數值精度與狀態回饋p-value 精度： 這通常是 JavaScript 浮點數運算或 Input 類型的問題。應在前端組件層級強制執行 toFixed(2) 或根據科學計數法格式化。在傳遞給後端前，確保使用 parseFloat() 處理，避免 $0.050000000745$ 這種擾民的數值出現。刪除確認機制： 不要只改顏色。建議引入 「雙重確認 (Double-tap/Confirmation Modal)」。點擊垃圾桶後，按鈕變形成「確定刪除？」文字，或跳出帶有「危險紅色」警示案的對話框。3. 優化 Header 與資訊層級登出按鈕： 必須加入 Tooltip。圖示建議改為更通用的 LogOut (門加箭頭) 而非單純的箭頭。視覺層級 (Visual Hierarchy)： 調整 Results 頁頂部。將 ANALYSIS COMPLETE 置於副標題位置。將 cancer 改為標籤 (Tag) 樣式或麵包屑 (Breadcrumb) 的一部分，明確它是「搜尋參數」而非「頁面動作」。二、 去模板化與品牌感重塑（解決 🟢低 優先級問題）要脫離「Shadcn/Tailwind 默認感」，需要注入生物資訊學的 領域特徵 (Domain-specific Design)。1. 引入「生物資訊專屬」色調與元素配色方案： 放棄純黑白。引入一組代表「實驗室/精準科技」的配色。例如：深海軍藍 (#1A2B3C) 作為主要文字色，搭配電漿綠 (#00F5D4) 作為成功/完成狀態色。KPI 卡片升級： * 不要只用 Lucide 標準 icon。在卡片背景加入淡淡的 「基因序列水印」 或 「蛋白質互作網路」的抽象線條。2. 增強 Pipeline 視圖的資訊密度時間軸化： 在 Pipeline 每個節點下方加入微小的 Duration (e.g., 1.2s)。動態狀態： PARALLEL RETRIEVAL 不應只是圓圈，應設計成一個「分支再匯聚」的視覺流向，體現 RAG 的併發特性。3. 提升 Insight Report 的可讀性內容分塊： 捨棄純文字 Markdown。對關鍵基因使用 「代碼高亮」 或 「藥丸標籤 (Pill Tags)」。在段落旁加入一個「跳轉至來源表格」的快捷 icon，打破報告與數據之間的隔閡。建議修改對照表現狀 (模板感)修改後 (專業感)預期效果全大寫 Overline LabelTitle Case + 適度字重 (Medium)提升可讀性，降低機械感全寬黑色按鈕具備深度感 (Drop Shadow) 的品牌色按鈕明確主動作 (CTA)隱藏的滾動條帶有導引陰影的滾動容器解決截斷導致的功能盲區靜態標題 cancer帶有 Context: 標籤的輸入回顯減少使用者認知負荷下一步建議：您希望我針對上述哪一個特定組件（例如 Pipeline 流程圖 或 Result 頁面 Header）提供更具體的 React/Tailwind 代碼修正建議，或是為您生成一份符合「生物資訊專業感」的新配色方案？