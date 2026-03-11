"""Shared pipeline logic for CLI and API."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from enrichrag.core.enricher import GeneEnricher
from enrichrag.core.graph_builder import build_graph_json
from enrichrag.core.pubmed import PubMedFetcher
from enrichrag.core.relation_extractor import RelationExtractor
from enrichrag.core.web_search import WebSearcher
from enrichrag.logging import logger
from enrichrag.prompts.generator import PromptGenerator
from enrichrag.settings import settings


def run_pipeline(
    genes: List[str],
    disease: str = "cancer",
    pval_threshold: float = 0.05,
    on_progress: Optional[Callable[[str, str], None]] = None,
) -> Dict:
    """Run the full enrichment + LLM analysis pipeline.

    Args:
        genes: List of gene symbols.
        disease: Disease context string.
        pval_threshold: Adjusted p-value cutoff.
        on_progress: Optional callback ``(step, message)`` for progress updates.

    Returns:
        Dict with input_genes, disease_context, enrichment_results, llm_insight.
    """

    def _progress(step: str, message: str) -> None:
        logger.info(message)
        if on_progress:
            on_progress(step, message)

    # 1. Enrichment
    _progress("enrichment", f"Running enrichment analysis for {len(genes)} genes...")
    enricher = GeneEnricher(gene_list=genes)
    enricher.run_enrichment()
    enricher.filter(pval_threshold=pval_threshold)
    _progress("enrichment", "Enrichment analysis complete.")

    # 2. Parallel Search (Web + PubMed)
    _progress("search", "Searching web and PubMed in parallel...")
    web_context, web_sources, pubmed_context, pubmed_sources, pubmed_df = _parallel_search(
        genes, disease, enricher.filtered_results, _progress,
    )

    # 3. Relation Extraction from PubMed abstracts
    relations_df = pd.DataFrame()
    entities_df = pd.DataFrame()
    if settings.openai_api_key and pubmed_df is not None and not pubmed_df.empty:
        _progress("extraction", "Extracting biomedical relations from abstracts...")
        try:
            llm = ChatOpenAI(
                model=settings.llm_model,
                temperature=0,
                api_key=settings.openai_api_key,
            )
            extractor = RelationExtractor(llm=llm)
            relations_df = extractor.extract(pubmed_df)
            entities_df = extractor.get_entities()
            _progress("extraction", f"Extracted {len(relations_df)} relations, {len(entities_df)} entities.")
        except Exception as e:
            logger.error(f"Relation extraction failed: {e}")
            _progress("extraction", f"Relation extraction failed: {e}")
    else:
        _progress("extraction", "Skipping relation extraction.")

    # 4. LLM
    insight = ""
    if not settings.openai_api_key:
        _progress("llm", "Skipping LLM — OPENAI_API_KEY not set.")
    else:
        _progress("llm", "Generating LLM analysis report...")
        base_dir = Path(__file__).resolve().parent.parent
        template_path = base_dir / "prompts" / "templates" / "enrichment_analysis.yaml"

        try:
            generator = PromptGenerator(template_path=str(template_path))
            llm = ChatOpenAI(
                model=settings.llm_model,
                temperature=0.2,
                api_key=settings.openai_api_key,
            )
            chain = generator.prompt_template | llm | StrOutputParser()

            go_table = enricher.filtered_results.get("GO", pd.DataFrame()).to_markdown(index=False)
            kegg_table = enricher.filtered_results.get("KEGG", pd.DataFrame()).to_markdown(
                index=False
            )

            inputs = {
                "context": f"Disease context: {disease}",
                "genes": ", ".join(genes),
                "go_table": go_table if go_table else "No significant enrichment results",
                "kegg_table": kegg_table if kegg_table else "No significant enrichment results",
                "web_search": web_context if web_context else "No web search results available.",
                "pubmed": pubmed_context if pubmed_context else "No PubMed results available.",
                "relations": relations_df.to_markdown(index=False) if not relations_df.empty else "No extracted relations available.",
            }
            insight = chain.invoke(inputs)
            _progress("llm", "LLM report generated.")
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            insight = f"Error generating insight: {e}"
            _progress("llm", f"LLM generation failed: {e}")

    # 5. Build graph
    graph_json = build_graph_json(
        input_genes=genes,
        enrichment_results=enricher.filtered_results,
        relations_df=relations_df,
        entities_df=entities_df if not entities_df.empty else None,
    )

    # 6. Build result
    result = {
        "input_genes": genes,
        "disease_context": disease,
        "enrichment_results": {
            label: df.to_dict(orient="records")
            for label, df in enricher.filtered_results.items()
        },
        "llm_insight": insight,
        "sources": {
            "web": web_sources,
            "pubmed": pubmed_sources,
        },
        "gene_relations": relations_df.to_dict(orient="records") if not relations_df.empty else [],
        "graph": graph_json,
    }

    _progress("done", "Pipeline complete.")
    return result


def _parallel_search(
    genes: List[str],
    disease: str,
    enrichment_results: Dict,
    _progress: Callable,
) -> Tuple[str, list, str, list, Optional[pd.DataFrame]]:
    """Run web search and PubMed fetch in parallel threads."""

    web_context = ""
    web_sources: list = []
    pubmed_context = ""
    pubmed_sources: list = []
    pubmed_df: Optional[pd.DataFrame] = None

    def _web_search() -> Tuple[str, list]:
        if not settings.tavily_api_key:
            _progress("search", "Skipping web search — TAVILY_API_KEY not set.")
            return "", []
        _progress("search", "Searching for related literature...")
        try:
            searcher = WebSearcher(max_results=3, api_key=settings.tavily_api_key)
            searcher.search_smart(
                gene_list=genes,
                disease=disease,
                enrichment_results=enrichment_results,
            )
            _progress("search", f"Found {len(searcher.results)} unique web results.")
            return searcher.to_context(), searcher.to_sources()
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            _progress("search", f"Web search failed: {e}")
            return "", []

    def _pubmed_search() -> Tuple[str, list, Optional[pd.DataFrame]]:
        if not settings.pubmed_email or settings.pubmed_email == "your@email.com":
            _progress("pubmed", "Skipping PubMed — PUBMED_EMAIL not configured.")
            return "", [], None
        _progress("pubmed", "Fetching PubMed abstracts...")
        try:
            fetcher = PubMedFetcher(email=settings.pubmed_email, max_results=10)
            fetcher.search(gene_list=genes, mode="batch", disease=disease)
            df = fetcher.to_dataframe()
            if df.empty:
                _progress("pubmed", "No PubMed abstracts found.")
                return "", [], None
            parts = []
            sources = []
            for _, row in df.iterrows():
                parts.append(f"[PMID:{row['pmid']}] {row['title']}\n{row['abstract']}")
                sources.append({
                    "pmid": row["pmid"],
                    "title": row["title"],
                    "abstract": row["abstract"],
                    "authors": row["authors"],
                    "journal": row["journal"],
                    "pub_date": row["pub_date"],
                })
            _progress("pubmed", f"Fetched {len(df)} PubMed abstracts.")
            return "\n\n".join(parts), sources, df
        except Exception as e:
            logger.error(f"PubMed fetch failed: {e}")
            _progress("pubmed", f"PubMed fetch failed: {e}")
            return "", [], None

    with ThreadPoolExecutor(max_workers=2) as executor:
        web_future = executor.submit(_web_search)
        pubmed_future = executor.submit(_pubmed_search)

        for future in as_completed([web_future, pubmed_future]):
            if future is web_future:
                web_context, web_sources = future.result()
            else:
                pubmed_context, pubmed_sources, pubmed_df = future.result()

    _progress("search", "All searches complete.")
    return web_context, web_sources, pubmed_context, pubmed_sources, pubmed_df


def save_result(result: Dict, output: Path) -> None:
    """Save pipeline result to JSON file."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"Results saved to: {output}")
