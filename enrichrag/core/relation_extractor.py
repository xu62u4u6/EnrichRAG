from typing import List, Literal, Optional

import pandas as pd
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import load_prompt
from pydantic import BaseModel, Field

from enrichrag.logging import logger


class BioEntity(BaseModel):
    """A biomedical entity extracted from text."""
    name: str = Field(description="Entity name, e.g. TP53, irinotecan, breast cancer")
    type: Literal["gene", "disease", "drug", "pathway", "other"] = Field(
        description="Entity type"
    )


class BioRelation(BaseModel):
    """A relation between two biomedical entities."""
    source: str = Field(description="Source entity name")
    source_type: Literal["gene", "disease", "drug", "pathway", "other"] = Field(
        description="Source entity type"
    )
    target: str = Field(description="Target entity name")
    target_type: Literal["gene", "disease", "drug", "pathway", "other"] = Field(
        description="Target entity type"
    )
    relation: Literal[
        "upregulate", "downregulate", "inhibit", "activate",
        "associate", "treat", "cause", "biomarker", "interact",
    ] = Field(description="Relation type between source and target")
    evidence: str = Field(description="Supporting sentence from the source text")


class ExtractionResult(BaseModel):
    """Extraction result from a single abstract."""
    entities: List[BioEntity] = Field(
        default_factory=list,
        description="All biomedical entities mentioned in the text",
    )
    relations: List[BioRelation] = Field(
        default_factory=list,
        description="Relations between entities; empty if none found",
    )


# Keep backward-compatible aliases
GeneRelation = BioRelation


class RelationExtractor:
    """
    Extracts biomedical entity relations from PubMed abstracts using LLM
    with Pydantic structured output.

    Supports genes, diseases, drugs, pathways, and other biomedical entities.
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

    def get_entities(self) -> pd.DataFrame:
        """Return all extracted entities as a DataFrame."""
        rows = []
        for result in self.raw_results:
            for entity in result.entities:
                rows.append({"name": entity.name, "type": entity.type})
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.drop_duplicates(subset=["name", "type"], keep="first")
        return df

    def _to_relation_table(self, sources: List[str]) -> pd.DataFrame:
        """Merge all extraction results into a single Relation Table."""
        rows = []
        for result, source in zip(self.raw_results, sources):
            for rel in result.relations:
                rows.append(
                    {
                        "source": rel.source,
                        "source_type": rel.source_type,
                        "target": rel.target,
                        "target_type": rel.target_type,
                        "relation": rel.relation,
                        "evidence": rel.evidence,
                        "pmid": source,
                    }
                )

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.drop_duplicates(
                subset=["source", "target", "relation"], keep="first"
            )
        return df
