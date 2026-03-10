from typing import List, Literal, Optional

import pandas as pd
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import load_prompt
from pydantic import BaseModel, Field

from enrichrag.logging import logger


class GeneRelation(BaseModel):
    """A single gene regulatory relation."""
    source_gene: str = Field(description="Regulator gene symbol, e.g. TP53")
    target_gene: str = Field(description="Target gene symbol, e.g. BAX")
    relation: Literal["up", "down"] = Field(
        description="Direction: up (upregulate/promote/activate) or down (downregulate/inhibit)"
    )
    evidence: str = Field(description="Supporting sentence from the source text")


class ExtractionResult(BaseModel):
    """Extraction result from a single abstract."""
    genes: List[str] = Field(description="All gene symbols mentioned in the abstract")
    relations: List[GeneRelation] = Field(
        default_factory=list,
        description="Regulatory relations between genes; empty if none found",
    )


class RelationExtractor:
    """
    Extracts gene regulatory relations from PubMed abstracts using LLM
    with Pydantic structured output.
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
        Run LLM relation extraction on each abstract, return merged Relation Table.

        Parameters
        ----------
        abstracts_df : Output of PubMedFetcher.to_dataframe(),
                       must have pmid, title, abstract columns
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
                logger.error(f"Extraction failed ({source}): {e}")

        logger.info(f"Successfully extracted relations from {len(self.raw_results)} abstracts")
        return self._to_relation_table(sources)

    def _to_relation_table(self, sources: List[str]) -> pd.DataFrame:
        """Merge all extraction results into a single Relation Table."""
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
