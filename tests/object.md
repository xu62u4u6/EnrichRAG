# AI 驅動基因集富集分析：學理正確性評估框架

## 概述

本框架評估 AI 富集分析報告的「學理正確性」——不只是抓到正確路徑名稱，而是具備領域專家的學理邏輯。基於五組核心癌症標誌（Cancer Hallmarks）基因模組：

| # | 模組 | 基因數 | 疾病脈絡 |
|---|------|--------|----------|
| 1 | DNA Repair | 8 | cancer |
| 2 | EMT | 7 | cancer |
| 3 | Glycolysis / Warburg Effect | 5 | cancer |
| 4 | Autophagy | 6 | cancer |
| 5 | Angiogenesis | 7 | cancer |

---

## 模組一：DNA 修復與基因體穩定性

**基因集：** `BRCA1, MLH1, MSH2, RAD51, FANCD2, ERCC1, XPA, LIG4`

### 預期富集路徑

- Reactome: DNA Repair (R-HSA-73894)
- KEGG: Homologous recombination, Mismatch repair, Fanconi anemia pathway

### 學理正確性 Claims

1. **次級路徑精準歸類** — MLH1/MSH2 屬於錯配修復 (MMR)；BRCA1/RAD51/FANCD2 屬於同源重組 (HR) / 范可尼貧血 (FA) 途徑；ERCC1/XPA 屬於核苷酸切除修復 (NER)；LIG4 屬於非同源性末端接合 (NHEJ)
2. **病理暗示** — 這些基因的突變或表現異常導致基因體不穩定性 (Genomic instability)，與癌症易感性症候群高度相關

---

## 模組二：上皮間質轉化 (EMT)

**基因集：** `SNAI1, TWIST1, ZEB1, VIM, CDH2, FN1, TGFB1`

### 預期富集路徑

- GO BP: epithelial to mesenchymal transition (GO:0001837)
- MSigDB: HALLMARK_EPITHELIAL_MESENCHYMAL_TRANSITION

### 學理正確性 Claims

1. **上游誘導因子** — TGFB1 是驅動 EMT 最經典的細胞激素/上游信號誘導者
2. **核心轉錄因子歸類** — SNAI1/TWIST1/ZEB1 為 EMT-TFs，負責啟動間質基因並抑制上皮基因
3. **間質標記物定義** — VIM (Vimentin)、CDH2 (N-cadherin)、FN1 (Fibronectin) 為 EMT 完成後的間質結構標記物，暗示細胞獲得高遷移性與侵襲性

---

## 模組三：糖解作用與代謝重編程

**基因集：** `HK2, PKM, LDHA, PGK1, SLC2A1`

### 預期富集路徑

- KEGG: Glycolysis / Gluconeogenesis (hsa00010)
- MSigDB: HALLMARK_GLYCOLYSIS

### 學理正確性 Claims

1. **瓦堡效應推論** — 看到這組核心基因富集，AI 必須自發推論並提及「瓦堡效應 (Warburg effect)」或有氧糖解 (Aerobic glycolysis)，指出這是缺氧腫瘤微環境下的經典標誌
2. **酵素功能串聯** — SLC2A1 (GLUT1) 為葡萄糖轉運蛋白；HK2/PKM (PKM2) 為糖解限速酶；LDHA 將丙酮酸轉化為乳酸，導致腫瘤微環境酸化

---

## 模組四：細胞自噬

**基因集：** `ULK1, BECN1, ATG5, ATG7, LC3B, SQSTM1`

### 預期富集路徑

- GO BP: autophagy (GO:0006914)
- KEGG: Regulation of autophagy (hsa04140)

### 學理正確性 Claims

1. **自噬複合體功能拆解** — ULK1 為起始激酶複合體；BECN1 參與 PI3K 複合體負責成核 (Nucleation)；ATG5/ATG7/LC3B 構成類泛素化結合系統負責膜延伸 (Elongation)；SQSTM1 (p62) 為自噬受體/降解底物
2. **自噬通量學理暗示** — LC3B 與 SQSTM1 同步高度表現，可能暗示自噬通量 (Autophagic flux) 阻斷或溶酶體降解受損，而非單純的自噬活化

---

## 模組五：血管新生與內皮細胞信號

**基因集：** `VEGFA, KDR, FLT1, ANGPT1, ANGPT2, TEK, CDH5`

### 預期富集路徑

- GO BP: angiogenesis (GO:0001525)
- KEGG: VEGF signaling pathway (hsa04370)

### 學理正確性 Claims

1. **雙重信號軸辨識** — VEGF-VEGFR 軸 (VEGFA → KDR/FLT1) 驅動內皮增殖/遷移/血管通透性；Angiopoietin-Tie2 軸 (ANGPT1/ANGPT2 → TEK) 負責血管重塑與穩定性調控
2. **內皮完整性與病理特徵** — CDH5 (VE-cadherin) 維持內皮間黏附；ANGPT2 + VEGFA 協同反映腫瘤異常微血管生成，與抗血管新生療法（如 Bevacizumab）臨床反應性相關
