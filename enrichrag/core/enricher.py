from typing import Dict, List, Optional

import gseapy as gp
import pandas as pd

from enrichrag.logging import logger


class GeneEnricher:
    """Performs gene set enrichment analysis with multiple databases and result filtering."""

    DEFAULT_DBS = {"GO": "GO_Biological_Process_2021",
                   "KEGG": "KEGG_2021_Human"}

    def __init__(self, gene_list: List[str], organism: str = "human"):
        self.gene_list = gene_list
        self.organism = organism
        self.results: Dict[str, pd.DataFrame] = {}
        self.filtered_results: Dict[str, pd.DataFrame] = {}

    def run_enrichment(self, gene_sets: Optional[Dict[str, str]] = None):
        """Run enrichment analysis with initial formatting."""
        target_dbs = gene_sets if gene_sets else self.DEFAULT_DBS

        for label, db_name in target_dbs.items():
            logger.info(f"Running {label} ({db_name}) analysis...")
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
                logger.error(f"{label} analysis failed: {e}")
        return self

    def _format_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Format column names and convert values."""
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

        df[["overlap_gene_count", "term_gene_set_size"]] = (
            df["overlap"].str.split("/", expand=True).astype(int)
        )
        return df

    def filter(self, pval_threshold: float = 0.05, min_genes: int = 2):
        """Filter results by statistical significance and gene count."""
        for label, df in self.results.items():
            mask = (df["p_adjusted"] <= pval_threshold) & (df["overlap_gene_count"] >= min_genes)
            self.filtered_results[label] = df[mask].copy()
        return self

    def get_top_terms(self, label: str, n: int = 10) -> pd.DataFrame:
        """Get top N most significant terms."""
        if label not in self.filtered_results:
            return pd.DataFrame()
        return self.filtered_results[label].nsmallest(n, "p_adjusted")
