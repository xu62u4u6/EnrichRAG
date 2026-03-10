import time
import pandas as pd
from typing import List, Optional
from itertools import combinations
from Bio import Entrez, Medline


class PubMedFetcher:
    """
    透過 Biopython Entrez API 查詢 PubMed，取得基因相關文獻摘要。
    """

    def __init__(self, email: str, max_results: int = 20):
        self.email = email
        self.max_results = max_results
        Entrez.email = email
        self.records: List[dict] = []

    def search(
        self,
        gene_list: List[str],
        mode: str = "batch",
        disease: Optional[str] = None,
    ) -> "PubMedFetcher":
        """
        搜尋 PubMed 並取得摘要。

        Parameters
        ----------
        gene_list : 基因列表
        mode : "batch" 全部基因一起查 | "pairwise" 兩兩配對查
        disease : 可選的疾病關鍵字，加入查詢條件
        """
        if mode == "pairwise":
            queries = self._build_pairwise_queries(gene_list, disease)
        else:
            queries = [self._build_batch_query(gene_list, disease)]

        all_pmids: set[str] = set()
        for query in queries:
            pmids = self._esearch(query)
            all_pmids.update(pmids)

        if all_pmids:
            self.records = self._efetch(list(all_pmids))

        print(f"共取得 {len(self.records)} 篇文獻摘要")
        return self

    def to_dataframe(self) -> pd.DataFrame:
        """將結果轉為 DataFrame。"""
        rows = []
        for rec in self.records:
            rows.append(
                {
                    "pmid": rec.get("PMID", ""),
                    "title": rec.get("TI", ""),
                    "abstract": rec.get("AB", ""),
                    "authors": "; ".join(rec.get("AU", [])),
                    "journal": rec.get("JT", ""),
                    "pub_date": rec.get("DP", ""),
                }
            )
        return pd.DataFrame(rows)

    # ── private methods ──

    def _build_batch_query(
        self, genes: List[str], disease: Optional[str] = None
    ) -> str:
        gene_terms = " OR ".join(f'"{g}"[Title/Abstract]' for g in genes)
        query = f"({gene_terms})"
        if disease:
            query += f' AND "{disease}"[Title/Abstract]'
        return query

    def _build_pairwise_queries(
        self, genes: List[str], disease: Optional[str] = None
    ) -> List[str]:
        queries = []
        for g1, g2 in combinations(genes, 2):
            q = f'"{g1}"[Title/Abstract] AND "{g2}"[Title/Abstract]'
            if disease:
                q += f' AND "{disease}"[Title/Abstract]'
            queries.append(q)
        return queries

    def _esearch(self, query: str) -> List[str]:
        """執行 PubMed 搜尋，回傳 PMID 列表。"""
        try:
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=self.max_results,
                sort="relevance",
            )
            result = Entrez.read(handle)
            handle.close()
            time.sleep(0.34)  # NCBI rate limit: 3 requests/sec
            return result.get("IdList", [])
        except Exception as e:
            print(f"esearch 失敗: {e}")
            return []

    def _efetch(self, pmids: List[str]) -> List[dict]:
        """根據 PMID 列表取得文獻詳細資訊。"""
        try:
            handle = Entrez.efetch(
                db="pubmed",
                id=",".join(pmids),
                rettype="medline",
                retmode="text",
            )
            records = list(Medline.parse(handle))
            handle.close()
            return records
        except Exception as e:
            print(f"efetch 失敗: {e}")
            return []
