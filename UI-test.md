# EnrichRAG UI Test Checklist

> 手動驗證清單，逐項操作並勾選。每個區塊對應一個功能頁面或互動流程。

---

## 1. 帳號系統（Auth）

- [ ] **註冊** — 填寫 username, email, password, confirm password → 進入主畫面，出現 "Account ready" toast
- [ ] **登入** — 使用已註冊帳號登入 → 正常進入主畫面
- [ ] **密碼可見切換** — 點擊眼睛 icon 可切換密碼顯示/隱藏
password點眼睛應該要是正確襯線字體
- [ ] **表單切換** — Sign In ↔ Create Account 連結正常切換
- [ ] **登出** — 點擊側欄底部登出按鈕 → 回到登入頁

---

## 2. New Analysis（Configure Analysis）

### 輸入

- [ ] **Gene Symbols** — 貼入預設 12 個基因（BRCA1 BRCA2 RAD51 RAD52 ATM ATR CHEK1 CHEK2 MLH1 MSH2 MSH6 PMS2），monospace 字體，底線輸入樣式
- [ ] **Disease Context** — 輸入 `cancer`，底線輸入樣式與 P-value 一致
- [ ] **P-value Threshold** — 數字輸入，預設 0.05

### 操作

- [ ] **Validate Genes** — 點擊後出現 Gene Validation 表格：
  - 欄位：Input Gene / Normalized Gene / Status / Source / Gene ID / Official Name
  - 上方顯示 Accepted / Remapped / Rejected badge 計數
  - 底部顯示 "Analysis ran with N normalized genes."
- [ ] **Run Pipeline** — 自動跳轉至 Results 頁，Pipeline tab 開始執行
- [ ] **快捷鍵** — `Enter` 觸發驗證、`Ctrl+Enter` 觸發 Run Pipeline

---

## 3. Results — Pipeline Tab

- [ ] **初始狀態** — 所有節點灰色（pending），opacity 降低
- [ ] **執行中** — 當前節點亮起（深色邊框 + 放大 + Loader 旋轉 icon + 計時器），連接線呈虛線動畫
- [ ] **完成狀態** — 節點顯示 Check icon，連接線實線
- [ ] **節點順序** — Enrichment → Planning → Web Search / PubMed（分支）→ Extraction → Synthesis → Report
- [ ] **從 History 載入** — 所有節點直接顯示 done 狀態

---

## 4. Results — Genes Tab

- [ ] **表格顯示** — 6 欄：Input Gene / Normalized Gene / Status / Source / Gene ID / Official Name
- [ ] **狀態 badge** — Accepted（綠）/ Remapped（琥珀）/ Rejected（紅）正確著色
- [ ] **基因點擊** — 點擊 Normalized Gene 開啟 Gene Drawer，顯示基因詳細資料
- [ ] **資料來源** — 同時支援 pipeline result 的 `gene_validation` 與 validate 步驟的資料

---

## 5. Results — Enrichment Tab

- [ ] **子 tab 切換** — GO Biological Process / KEGG Pathways（pill 按鈕樣式）
- [ ] **表格欄位** — Term / Overlap / P-value / Adj. P-value / Genes
- [ ] **P-value 格式** — < 0.001 以科學記號顯示，其餘保留 4 位小數
- [ ] **Gene pills** — Genes 欄位中的基因以小型 pill 標籤顯示
- [ ] **顯著性高亮** — P-value 極低的列（sig-high / sig-mid）文字加粗

---

## 6. Results — Sources Tab

- [ ] **子 tab 切換** — PubMed / Web（pill 按鈕樣式）
- [ ] **PubMed 來源** — 顯示標題、PMID badge、期刊名、發表日期、作者、摘要
- [ ] **Web 來源** — 顯示標題、URL、snippet 摘要
- [ ] **來源 icon** — PubMed（琥珀色 BookOpen）/ Web（teal Globe）
- [ ] **連結** — 標題可點擊開啟外部連結

---

## 7. Results — Network Tab

- [ ] **圖譜渲染** — D3 force-directed graph 正常顯示
- [ ] **節點樣式** — Gene 節點較大（深色）、GO/KEGG/Disease/Drug 各有不同灰階與大小
- [ ] **Input 基因** — 更大圓圈 + 深色填充 + 粗體標籤
- [ ] **互動** — 拖曳節點、滾輪縮放、hover 高亮（非相連節點淡化）
- [ ] **點擊** — 點擊節點開啟 Gene Drawer

---

## 8. Results — Insight Report Tab

- [ ] **報告 banner** — 顯示 Disease Context 與時間戳
- [ ] **Markdown 渲染** — 標題、段落、列表、表格、code block、blockquote 正常排版
- [ ] **字體** — 使用 Lora 報告字體

---

## 9. 工具按鈕（Results Header）

- [ ] **Quick Stats** — 4 張卡片顯示 Input Genes / Enriched Terms / Relations / Sources，各有對應彩色 icon
- [ ] **Ask Assistant** — 開啟 Chat Drawer
- [ ] **Copy** — 複製報告至剪貼簿，顯示 toast
- [ ] **JSON** — 下載 JSON 檔案，顯示 toast
- [ ] **Stop** — 執行中出現紅色 Stop 按鈕，可中斷 pipeline

---

## 10. Chat Drawer（Ask Assistant）

- [ ] **開啟/關閉** — 點擊 Ask Assistant 開啟、X 或 backdrop 關閉
- [ ] **Suggested Questions** — 點擊建議問題自動送出
- [ ] **對話** — 輸入問題 → AI 回應，Markdown 格式正確
- [ ] **Send 按鈕** — 位於輸入框右側

---

## 11. Gene Drawer

- [ ] **開啟** — 從 Genes tab 或 Network 點擊基因名稱觸發
- [ ] **內容** — 顯示 canonical symbol、gene ID、official name、description、type、chromosome 等欄位
- [ ] **關閉** — 點擊 X 或 backdrop 關閉

---

## 12. History

- [ ] **列表顯示** — 顯示過往分析記錄（disease context、gene count、時間）
- [ ] **搜尋** — 搜尋框可篩選 history 項目
- [ ] **載入** — 點擊項目 → 載入結果至 Results 頁
    確認genes有沒有成功載入
- [ ] **刪除** — 點擊 Delete 按鈕移除單筆記錄
- [ ] **清除全部** — Clear All 按鈕清除所有記錄

---

## 13. 版面與樣式

- [ ] **側欄** — 桌面版固定不動（sticky），捲動內容時不跟著滾
- [ ] **品牌區** — Logo + "EnrichRAG" + "Literature Aug." 正常顯示
- [ ] **導覽按鈕** — New Analysis / Results / History，active 狀態高亮，History 顯示項目數 badge
- [ ] **Results 停用** — 無結果時 Results 按鈕 disabled
- [ ] **RWD** — 行動版側欄收合為頂部橫列，漢堡選單可展開
- [ ] **字體** — 標題 Source Serif 4、內文 Manrope、程式碼 JetBrains Mono、報告 Lora
- [ ] **Toast** — 操作回饋 toast 顯示在右下角


測試各內容分頁（Pipeline、Genes、Enrichment、Sources、Network、Insight Report）
測試 New Analysis 流程
測試 History 功能
測試 Ask Assistant 功能
測試 Copy / JSON 匯出功能
測試登出並重新登入


2. copy / json要參照舊版行為 短暫提示完成 並toast
3. Ask Assistant 也要對齊舊版行為 並確認有沒有提示正在等待回應？