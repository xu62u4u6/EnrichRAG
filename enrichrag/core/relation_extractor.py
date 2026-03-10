import pandas as pd
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import load_prompt
from langchain_core.language_models import BaseChatModel


class GeneRelation(BaseModel):
    """單一基因調控關係。"""
    source_gene: str = Field(description="調控方基因符號，例如 TP53")
    target_gene: str = Field(description="被調控方基因符號，例如 BAX")
    relation: Literal["up", "down"] = Field(
        description="調控方向：up（上調/促進/活化）或 down（下調/抑制）"
    )
    evidence: str = Field(description="原文中支持此關係的句子")


class ExtractionResult(BaseModel):
    """一篇摘要的完整抽取結果。"""
    genes: List[str] = Field(description="摘要中提到的所有基因符號")
    relations: List[GeneRelation] = Field(
        default_factory=list,
        description="基因間的調控關係列表，若無明確關係則為空",
    )


class RelationExtractor:
    """
    從 PubMed 摘要中使用 LLM 提取基因間調控關係。
    使用 Pydantic structured output 確保輸出格式。
    """

    def __init__(self, llm: BaseChatModel, template_path: Optional[str] = None):
        self.llm = llm
        if template_path is None:
            import os
            template_path = os.path.join(
                os.path.dirname(__file__),
                "..", "prompts", "templates", "get_genes_relation.yaml",
            )
        self.prompt_template = load_prompt(template_path)
        self.structured_llm = llm.with_structured_output(ExtractionResult)
        self.chain = self.prompt_template | self.structured_llm
        self.raw_results: List[ExtractionResult] = []

    def extract(self, abstracts_df: pd.DataFrame) -> pd.DataFrame:
        """
        對每篇摘要執行 LLM 關係抽取，回傳合併的 Relation Table。

        Parameters
        ----------
        abstracts_df : PubMedFetcher.to_dataframe() 的輸出，
                       需要有 pmid, title, abstract 欄位
        """
        self.raw_results = []
        sources: List[str] = []

        for _, row in abstracts_df.iterrows():
            abstract = row.get("abstract", "")
            if not abstract:
                continue

            pmid = row.get("pmid", "")
            source = f"PMID:{pmid}" if pmid else "unknown"

            try:
                result: ExtractionResult = self.chain.invoke(
                    {"text": abstract, "source": source}
                )
                self.raw_results.append(result)
                sources.append(source)
            except Exception as e:
                print(f"抽取失敗 ({source}): {e}")

        print(f"成功抽取 {len(self.raw_results)} 篇文獻的關係")
        return self._to_relation_table(sources)

    def _to_relation_table(self, sources: List[str]) -> pd.DataFrame:
        """將所有抽取結果合併為一張 Relation Table。"""
        rows = []
        for result, source in zip(self.raw_results, sources):
            for rel in result.relations:
                rows.append(
                    {
                        "source_gene": rel.source_gene,
                        "target_gene": rel.target_gene,
                        "relation": rel.relation,
                        "evidence": rel.evidence,
                        "pmid": source,
                    }
                )

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.drop_duplicates(
                subset=["source_gene", "target_gene", "relation"], keep="first"
            )
        return df
