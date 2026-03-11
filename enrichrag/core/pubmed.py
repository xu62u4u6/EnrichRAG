from __future__ import annotations

import time
from itertools import combinations
from typing import TYPE_CHECKING, List, Optional

import pandas as pd
from Bio import Entrez, Medline

from enrichrag.logging import logger

if TYPE_CHECKING:
    from enrichrag.core.query_planner import SearchIntent


class PubMedFetcher:
    """Fetches gene-related abstracts from PubMed via Biopython Entrez API."""

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
        Search PubMed and fetch abstracts.

        Parameters
        ----------
        gene_list : List of gene symbols
        mode : "batch" (all genes together) | "pairwise" (pairwise combinations)
        disease : Optional disease keyword to add to the query
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

        logger.info(f"Fetched {len(self.records)} abstracts")
        return self

    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to a DataFrame."""
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

    def search_from_plan(self, intents: List[SearchIntent]) -> "PubMedFetcher":
        """Search PubMed using structured intents from QueryPlanner.

        Uses each intent's pubmed_query. Deduplicates PMIDs across intents
        and fetches all at once.
        """
        all_pmids: set[str] = set()
        for intent in intents:
            pmids = self._esearch(intent.pubmed_query)
            all_pmids.update(pmids)
            logger.info(
                f"PubMed plan query [{intent.category}]: {len(pmids)} PMIDs"
            )

        if all_pmids:
            self.records = self._efetch(list(all_pmids))

        logger.info(f"Plan-based PubMed fetch: {len(self.records)} abstracts")
        return self

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
        """Execute PubMed search, return PMID list."""
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
            logger.error(f"esearch failed: {e}")
            return []

    def _efetch(self, pmids: List[str]) -> List[dict]:
        """Fetch article details by PMID list."""
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
            logger.error(f"efetch failed: {e}")
            return []
