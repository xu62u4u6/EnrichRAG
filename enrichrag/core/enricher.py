import pandas as pd
import gseapy as gp
from typing import List, Dict, Optional

class GeneEnricher:
    """
    處理基因富集分析的類別，支援多個資料庫與結果篩選。
    """
    DEFAULT_DBS = {"GO": "GO_Biological_Process_2021", 
                   "KEGG": "KEGG_2021_Human"}

    def __init__(self, gene_list: List[str], organism: str = "human"):
        self.gene_list = gene_list
        self.organism = organism
        self.results: Dict[str, pd.DataFrame] = {}
        self.filtered_results: Dict[str, pd.DataFrame] = {}

    def run_enrichment(self, gene_sets: Optional[Dict[str, str]] = None):
        """執行富集分析並進行初步的格式化"""
        target_dbs = gene_sets if gene_sets else self.DEFAULT_DBS
        
        for label, db_name in target_dbs.items():
            print(f"正在執行 {label} ({db_name}) 分析...")
            try:
                enr = gp.enrichr(
                    gene_list=self.gene_list,
                    organism=self.organism,
                    gene_sets=db_name,
                    cutoff=1.0,
                    outdir=None
                )
                self.results[label] = self._format_dataframe(enr.res2d)
            except Exception as e:
                print(f"{label} 分析失敗: {e}")
        return self

    def _format_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """內部方法：處理欄位名稱與數值轉換"""
        target_columns = ["Term", "Overlap", "P-value", "Adjusted P-value", "Genes"]
        df = df[target_columns].copy()
        
        rename_map = {
            "Term": "term",
            "P-value": "p_value",
            "Adjusted P-value": "p_adjusted",
            "Genes": "genes",
            "Overlap": "overlap"
        }
        df.rename(columns=rename_map, inplace=True)
        
        # 拆分 Overlap 資訊 (例如 "5/764")
        df[["overlap_gene_count", "term_gene_set_size"]] = (
            df["overlap"].str.split("/", expand=True).astype(int)
        )
        return df

    def filter(self, pval_threshold: float = 0.05, min_genes: int = 2):
        """根據統計顯著性與基因數量過濾結果"""
        for label, df in self.results.items():
            mask = (df["p_adjusted"] <= pval_threshold) & (df["overlap_gene_count"] >= min_genes)
            self.filtered_results[label] = df[mask].copy()
        return self

    def get_top_terms(self, label: str, n: int = 10) -> pd.DataFrame:
        """取得前 N 名最顯著的結果"""
        if label not in self.filtered_results:
            return pd.DataFrame()
        return self.filtered_results[label].nsmallest(n, "p_adjusted")


