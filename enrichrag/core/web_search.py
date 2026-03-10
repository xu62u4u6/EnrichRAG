from typing import List, Optional

import pandas as pd
from langchain_tavily import TavilySearch

from enrichrag.logging import logger


class WebSearcher:
    """
    Searches for latest clinical/biomedical information using Tavily Search API.
    Requires TAVILY_API_KEY environment variable.
    """

    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        self.tool = TavilySearch(
            max_results=max_results,
            topic="general",
            include_raw_content=False,
        )
        self.results: List[dict] = []

    def search(
        self,
        gene_list: List[str],
        disease: Optional[str] = None,
        custom_query: Optional[str] = None,
    ) -> "WebSearcher":
        """
        Search for latest gene-related information.

        Parameters
        ----------
        gene_list : List of gene symbols
        disease : Optional disease keyword
        custom_query : Custom query; if provided, gene_list and disease are ignored
        """
        if custom_query:
            query = custom_query
        else:
            genes_str = " ".join(gene_list)
            query = f"{genes_str} gene function mechanism"
            if disease:
                query += f" {disease}"

        try:
            raw = self.tool.invoke(query)
            if isinstance(raw, dict) and "results" in raw:
                self.results = raw["results"]
            elif isinstance(raw, list):
                self.results = raw
            else:
                self.results = [raw]
            logger.info(f"Found {len(self.results)} search results")
        except Exception as e:
            logger.error(f"Search failed: {e}")
            self.results = []

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
