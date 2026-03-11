from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Dict, List, Optional

import pandas as pd
from langchain_tavily import TavilySearch

from enrichrag.logging import logger

if TYPE_CHECKING:
    from enrichrag.core.query_planner import SearchIntent


class WebSearcher:
    """
    Searches for latest clinical/biomedical information using Tavily Search API.
    Requires TAVILY_API_KEY environment variable.
    """

    def __init__(self, max_results: int = 3, api_key: Optional[str] = None):
        self.max_results = max_results
        kwargs = dict(
            max_results=max_results,
            topic="general",
            include_raw_content=False,
        )
        if api_key:
            kwargs["tavily_api_key"] = api_key
        self.tool = TavilySearch(**kwargs)
        self.results: List[dict] = []

    def search(
        self,
        gene_list: List[str],
        disease: Optional[str] = None,
        custom_query: Optional[str] = None,
    ) -> "WebSearcher":
        """Single-query search (legacy interface)."""
        if custom_query:
            query = custom_query
        else:
            genes_str = " ".join(gene_list[:10])
            query = f"{genes_str} gene function mechanism"
            if disease:
                query += f" {disease}"

        self._invoke_query(query)
        return self

    def search_smart(
        self,
        gene_list: List[str],
        disease: str,
        enrichment_results: Dict[str, pd.DataFrame],
        top_n_genes: int = 5,
        top_n_terms: int = 3,
    ) -> "WebSearcher":
        """Smart search using top enrichment terms + top genes + disease.

        Strategy:
        1. Find the top N genes (most frequently appearing in enrichment results).
        2. Find the top N pathway/GO terms (by p-value).
        3. Build targeted queries: each top term + top genes + disease.
        4. Deduplicate results by URL.
        """
        # --- Find top genes by frequency across enrichment results ---
        gene_counter: Counter = Counter()
        for df in enrichment_results.values():
            if df.empty or "genes" not in df.columns:
                continue
            for genes_str in df["genes"].dropna():
                for g in str(genes_str).replace(",", ";").split(";"):
                    g = g.strip().upper()
                    if g:
                        gene_counter[g] += 1

        # Fall back to input list if enrichment has no gene info
        if gene_counter:
            top_genes = [g for g, _ in gene_counter.most_common(top_n_genes)]
        else:
            top_genes = gene_list[:top_n_genes]

        # --- Find top terms by adjusted p-value ---
        top_terms: List[str] = []
        for df in enrichment_results.values():
            if df.empty or "term" not in df.columns:
                continue
            sort_col = "p_adjusted" if "p_adjusted" in df.columns else "p_value"
            sorted_df = df.sort_values(sort_col, ascending=True)
            top_terms.extend(sorted_df["term"].head(top_n_terms).tolist())

        if not top_terms:
            top_terms = ["gene function mechanism"]

        # --- Build queries and search ---
        genes_str = " ".join(top_genes)
        queries = []
        for term in top_terms[:top_n_terms]:
            queries.append(f"{term} {genes_str} {disease}")

        logger.info(f"Smart search: {len(queries)} queries, top genes={top_genes}")

        seen_urls: set = set()
        all_results: List[dict] = []

        for query in queries:
            hits = self._invoke_query(query)
            for hit in hits:
                url = hit.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(hit)

        self.results = all_results
        logger.info(f"Smart search total: {len(self.results)} unique results")
        return self

    def _invoke_query(self, query: str) -> List[dict]:
        """Run a single Tavily query and return results."""
        try:
            raw = self.tool.invoke(query)
            if isinstance(raw, dict) and "results" in raw:
                hits = raw["results"]
            elif isinstance(raw, list):
                hits = raw
            else:
                hits = [raw]
            logger.info(f"Query [{query[:60]}...] → {len(hits)} results")
            return hits
        except Exception as e:
            logger.error(f"Search failed for query [{query[:60]}]: {e}")
            return []

    def search_from_plan(self, intents: List[SearchIntent]) -> "WebSearcher":
        """Search using structured intents from QueryPlanner.

        Uses each intent's tavily_query, deduplicates results by URL.
        """
        seen_urls: set = set()
        all_results: List[dict] = []

        for intent in intents:
            query = intent.tavily_query
            hits = self._invoke_query(query)
            for hit in hits:
                url = hit.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(hit)

        self.results = all_results
        logger.info(f"Plan-based search total: {len(self.results)} unique results")
        return self

    def to_dataframe(self) -> pd.DataFrame:
        """Convert search results to a DataFrame."""
        rows = []
        for item in self.results:
            rows.append(
                {
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                }
            )
        return pd.DataFrame(rows)

    def to_context(self) -> str:
        """Convert search results to text suitable for prompt injection."""
        parts = []
        for i, item in enumerate(self.results, 1):
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")
            parts.append(f"[{i}] {title}\n{content}\nSource: {url}")
        return "\n\n".join(parts)

    def to_sources(self) -> List[dict]:
        """Return structured source list for frontend display."""
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            }
            for item in self.results
        ]
