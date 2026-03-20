以下是我逐頁操作後整理的 **UI 問題** 與 **模板感重的原因**，附上截圖對應位置說明：

***

## 🔴 UI 問題（功能性 / 視覺 Bug）

### 1. **Results 頁面在無選取歷史時完全空白，缺乏引導**
（初始 Results 頁面） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- 點擊左側 "Results" 導航項目後，頁面完全空白、無任何內容提示。
- 使用者不知道要先從 History 點進去才能看到 Results。
- **應該有一個 empty state（空狀態提示），引導使用者去選歷史紀錄或執行新分析。**

### 2. **頁首標題區塊缺乏層級感**
（Results 頁） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- 結果頁標題「cancer」直接用 `h2` 大字但沒有 subtitle 或 breadcrumb，無法判斷這是從哪個操作來的。
- "ANALYSIS COMPLETE" 標籤（左上角小綠字）視覺比重太弱，容易被忽略。

### 3. **New Analysis 頁面在 Validate 後 Gene Validation 表格直接出現在表單下方，毫無過渡感**
（New Analysis 現在的狀態） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- 表單卡片與下方的 Gene Validation 表格之間沒有明確的分隔或動畫，視覺上像是「頁面往下長了一截」。
- **兩個區塊邊框相近但語義完全不同，應有更清楚的視覺分層。**

### 4. **tab 導覽欄（PIPELINE / GENES / ENRICHMENT / SOURCES / NETWORK / INSIGHT REPORT）過長，小視窗時有截斷風險**
（Results 的 tab bar） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- 6 個 tab 全部以文字顯示 + 數字 badge，寬度緊繃。
- 在 1366px 以下的解析度很可能溢出或換行。
- 沒有響應式 dropdown 折疊機制。

### 5. **History 頁面的 List items 無法點擊整行（只能點文字）**
（History 頁） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- 每筆 history item 視覺上看起來是「整行可點擊」的卡片，但如果點到空白處（timestamp 右側區域）可能沒有反應，違反使用者直覺（hit area 不夠大）。

### 6. **Ask Assistant drawer 的 loading 動畫（teal 球）出現在標題區與內容卡片之間的空檔，位置突兀**
（Assistant drawer 剛打開時的截圖） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- loading 圓球懸浮在 drawer header 下方、卡片上方的空白處，位置不直覺，看起來像布局錯誤。

### 7. **INSIGHT REPORT tab 的 Context 標籤列過於簡陋**
- 「Context: cancer」只有小小的標籤，旁邊是一個無說明的時鐘 icon，hover 才能知道功能，違反 discoverability 原則。

***

## 🟡 模板感重的原因

### 1. **四個 Summary Card 設計高度公版化**
（Results 統計卡片區） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- 四欄等寬、等高的 stat card（數字 + 小 label），帶小 icon，這是幾乎所有 SaaS dashboard 都會用的樣板佈局（Tailwind UI / shadcn/ui 的 `StatsCard`）。
- **icon 選用也很通用（基因、圖表、關係、書本），沒有針對生物資訊領域客製化。**

### 2. **Sidebar 結構過於標準 Admin Template**
（左側 sidebar） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- Logo 上方、三個導覽項目（icon + 文字）、底部 user info + logout，這是 SaaS admin template（Sidebar Layout）的標配，沒有任何針對分析工具或生物資訊工具的特色設計。
- "LITERATURE AUG." 副標題在視覺上字元間距太大、字級太小，不像品牌設計決定，更像是忘記調整的 placeholder 樣式。

### 3. **表單卡片（Configure Analysis）的 label 樣式**
（New Analysis 表單） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- `GENE SYMBOLS`、`DISEASE CONTEXT`、`P-VALUE THRESHOLD` 全大寫 + tracking 字距，這是典型的 Tailwind/shadcn form label 預設樣式（`text-xs font-semibold uppercase tracking-wide text-muted-foreground`），整個表單看起來像從 component library 直接貼上而非設計過。

### 4. **按鈕組合（VALIDATE GENES + RUN PIPELINE）視覺對比不足**
（表單底部按鈕） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- `VALIDATE GENES` 是 outline 白底、`RUN PIPELINE` 是深色實心，此為 primary/secondary action 的標準搭配，但字體全大寫 + 字距讓整體看起來是 boilerplate 按鈕，缺少品牌個性。

### 5. **History 列表是純粹的 list row 樣板**
（Analysis History 頁） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- 每一筆紀錄：左邊 disease name（粗體）+ badge + genes 預覽，右邊 timestamp + delete icon，這是標準的 "資料列表 item" 樣板（如 Notion、Linear 的 list item），沒有針對分析紀錄做任何差異化視覺設計（例如分析狀態顏色、基因數量的視覺 bar 等）。

### 6. **INSIGHT REPORT 排版像 Markdown 輸出**
（Insight Report tab） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- 標題層級（H2 → H3 → bullet point）、橫線分隔，是 LLM 輸出直接套 `prose` CSS class 的典型結果，沒有針對報告做 custom 版面設計，讀起來像 ChatGPT 的輸出直接貼上。

### 7. **Pipeline 流程圖的節點設計過於簡單**
（PIPELINE tab） [140.129.69](http://140.129.69.143:9001/test0948395013/)
- 圓形節點 + 勾勾 + 文字 label 的 flowchart，接近 CSS flowchart library 的預設範例（如 React Flow 的入門 demo），缺乏動態感與資訊密度的設計巧思。

***

## 總結建議優先處理項目

| 優先級 | 問題 |
|--------|------|
| 🔴 高 | Results 空白頁缺乏 empty state |
| 🔴 高 | Gene Validation 與表單的視覺斷層 |
| 🟡 中 | Tab bar 響應式問題 |
| 🟡 中 | Insight Report 缺乏客製化排版 |
| 🟢 低 | Sidebar / 按鈕 / 卡片的模板感優化（品牌一致性） |

這份分析非常專業，精確捕捉到了「開發者導向 UI (Developer-centric UI)」與「產品導向 UX (Product-led UX)」之間的鴻溝。目前的狀態確實像是一個基於 shadcn/ui 或 Tailwind UI 快速搭建的實驗室原型，而非一個成熟的生信分析平台。針對你提出的問題，我建議從以下幾個技術棧與設計思維進行「去模板化」改進：
一、 核心功能修復與組件建議 (🔴 UI 問題)1. 解決 Empty State 與引導 (Results 頁面)不要讓使用者面對白屏。建議組件： 使用 lucide-react 的 Database 或 Search 圖示配合微弱的波紋動畫。做法： 實作一個 EmptyState 組件。若 selectedHistoryId 為空，顯示：「尚未選擇分析結果。請從左側歷史紀錄選擇，或[開啟新分析]。」
2. 解決 Gene Validation 的過渡感 (New Analysis 頁面)目前「頁面長一截」是因為缺乏視覺深度。建議套件： framer-motion。做法： * 使用 AnimatePresence 包裹 Validation Table。當 isValidated 為 true 時，讓表格以 initial={{ opacity: 0, y: 20 }} 向上滑入。視覺分隔： 在表單與表格間加入一個 Separator (分線)，並標註「Step 2: Verify Genetic Input」，明確流程階段。3. 響應式 Tab 導覽 (Results 頁面)建議套件： @radix-ui/react-tabs 配合自定義 CSS。做法： * 實作 "Priority Plus" 模式：當寬度不足時，將最後兩個 Tab (Sources/Report) 收納進一個名為 More... 的 DropdownMenu 中。或者使用 overflow-x-auto 配合 CSS mask-image 製作左右漸變，提示可滑動。4. History 點擊區域與 Drawer LoadingHistory： 將 li 或 Card 組件直接包在 Link 或 button 內，確保 display: block; width: 100%;。Loading： 不要讓球懸浮。將 Loading 狀態直接實作在 AssistantDrawer 的 Content 區塊中心，或使用 Skeleton Screen (骨架屏) 代替單點 Loading，這能大幅減少視覺跳動感。二、 品牌感與「去模板化」策略 (🟡 模板感重)要讓 EnrichRAG 看起來像「昂貴的生信工具」而非「免費的 Admin Template」，關鍵在於 資訊密度 (Information Density) 與 領域語義。1. 統計卡片 (Summary Cards) 升級去樣板化： 不要只放數字。在數字後方加入一個微小的 Sparkline (迷你趨勢線) 或 分佈直方圖。領域圖標： 捨棄 Lucide 通用圖標。使用更具生物意義的 SVG（如：雙螺旋代表基因、網路拓撲代表 Relations）。
2. Sidebar 與品牌字體排版： 調整 LITERATURE AUG. 的字距 (Tracking)。取消 uppercase，改用 font-medium 與適度的 letter-spacing: -0.02em 增加現代感。背景： 給 Sidebar 一個非常微弱的磨砂玻璃效果 (backdrop-blur) 或非純黑的深色 (如 #0f172a)，與 Main Content 產生空間層次。
3. Insight Report 的「報告感」目前的 prose 樣式太像 Blog。建議套件： @tailwindcss/typography (自定義配置) + react-markdown。改進： * 為 Report 加入 Table of Contents (側邊目錄)。將關鍵基因自動轉化為可點擊的 Badge，點擊後彈出迷你資訊卡（甚至與左側數據聯動）。加入「匯出 PDF/JSON」的浮動按鈕，增加「正式報告」的嚴肅感。

4. Pipeline 流程圖的進化建議套件： React Flow 或 Mermaid.js。做法： * 不要用靜態圓圈。讓連接線具備「流動動畫」（CSS stroke-dashoffset），代表數據正在 RAG 流程中傳輸。節點內顯示微型狀態（如：Success: 20 papers retrieved），增加工具的透明度。三、 推薦改進的開發包 (Tech Stack Suggestions)類型推薦包用途動畫framer-motion解決頁面生硬跳轉、導覽過渡。圖表recharts / visx將 Summary Card 的數字視覺化，增加專業度。流程圖reactflow製作可縮放、具備互動性的 Pipeline 視圖。數據表格@tanstack/react-table實作固定首欄、虛擬滾動，解決截斷與效能問題。回饋sonner代替傳統 Alert，提供更精緻的執行狀態通知。
總結建議：
您的分析已經點出了核心矛盾：「通用 UI 框架」無法支撐「垂直領域專業工具」的複雜性。我建議優先處理 🔴 高優先級 的 Empty State 與 Gene Validation 斷層。這兩個修復能立即提升使用者的「操控感」。接著，針對 History 與 Insight Report 進行資訊密度的優化，這能讓產品看起來從「作業感」變成「專業工具感」。您希望我針對哪一個部分（例如：Framer Motion 的具體過渡程式碼，或 React Flow 的 Pipeline 實作建議）提供更深入的指導？