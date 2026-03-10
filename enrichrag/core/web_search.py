import pandas as pd
from typing import List, Optional
from langchain_tavily import TavilySearch


class WebSearcher:
    """
    使用 Tavily Search API 搜尋最新臨床/生物醫學資訊。
    需要設定環境變數 TAVILY_API_KEY。
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
        搜尋基因相關的最新資訊。

        Parameters
        ----------
        gene_list : 基因列表
        disease : 可選的疾病關鍵字
        custom_query : 自訂查詢，若提供則忽略 gene_list 和 disease
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
            print(f"搜尋到 {len(self.results)} 筆結果")
        except Exception as e:
            print(f"搜尋失敗: {e}")
            self.results = []

        return self

    def to_dataframe(self) -> pd.DataFrame:
        """將搜尋結果轉為 DataFrame。"""
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
        """將搜尋結果轉為可直接塞入 prompt 的文字。"""
        parts = []
        for i, item in enumerate(self.results, 1):
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")
            parts.append(f"[{i}] {title}\n{content}\nSource: {url}")
        return "\n\n".join(parts)
