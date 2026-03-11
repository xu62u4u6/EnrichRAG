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
from enrichrag.core.query_planner import QueryPlan, QueryPlanner
from enrichrag.core.relation_extractor import RelationExtractor
from enrichrag.core.web_search import WebSearcher
from enrichrag.logging import logger
from enrichrag.prompts.generator import PromptGenerator
from enrichrag.settings import settings


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, appending a note if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n... [truncated for token limit]"


def _compact_relations(df: pd.DataFrame, max_rows: int = 30) -> str:
    """Convert relations DataFrame to compact text for LLM input.

    Produces: source -[relation]-> target (PMID:xxx)
    """
    if df.empty:
        return "No extracted relations available."
    lines = []
    for _, row in df.head(max_rows).iterrows():
        pmid = row.get("pmid", "")
        lines.append(
            f"- {row['source']} -[{row['relation']}]-> {row['target']} ({pmid})"
        )
    if len(df) > max_rows:
        lines.append(f"... and {len(df) - max_rows} more relations")
    return "\n".join(lines)


def _compact_enrichment(df: pd.DataFrame, max_rows: int = 15) -> str:
    """Convert enrichment DataFrame to a compact text format for LLM input.

    Instead of full markdown table, produces one line per term:
      - term_name (p=1.2e-06, 5/80): GENE1, GENE2, GENE3
    """
    if df.empty:
        return "No significant enrichment results"
    lines = []
    sort_col = "p_adjusted" if "p_adjusted" in df.columns else "p_value"
    sorted_df = df.sort_values(sort_col, ascending=True).head(max_rows)
    for _, row in sorted_df.iterrows():
        term = row.get("term", "")
        p = row.get("p_adjusted", row.get("p_value", 1))
        overlap = row.get("overlap", "")
        genes_str = str(row.get("genes", "")).replace(";", ", ")
        lines.append(f"- {term} (p={p:.1e}, {overlap}): {genes_str}")
    if len(df) > max_rows:
        lines.append(f"... and {len(df) - max_rows} more terms")
    return "\n".join(lines)


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

    def _progress(step: str, message: str, **kwargs) -> None:
        logger.info(message)
        if on_progress:
            on_progress(step, message, **kwargs)

    # 1. Enrichment
    _progress("enrichment", f"Running enrichment analysis for {len(genes)} genes...")
    enricher = GeneEnricher(gene_list=genes)
    enricher.run_enrichment()
    enricher.filter(pval_threshold=pval_threshold)
    _progress("enrichment", "Enrichment analysis complete.", data={
        "enrichment_results": {
            label: df.to_dict(orient="records")
            for label, df in enricher.filtered_results.items()
        },
    })

    # 1.5. Query Planning
    _progress("planning", "Generating search strategy from enrichment results...")
    planner = QueryPlanner()
    query_plan = planner.plan(
        enricher.filtered_results, genes, disease,
        api_key=settings.openai_api_key or None,
        model=settings.llm_model,
    )
    _progress("planning", query_plan.summary)

    # Optional LLM refinement
    if settings.openai_api_key and settings.query_planning_llm_refine:
        all_terms = []
        for df in enricher.filtered_results.values():
            if not df.empty and "term" in df.columns:
                all_terms.extend(df["term"].tolist())
        query_plan = planner.refine_with_llm(
            query_plan, all_terms, disease,
            api_key=settings.openai_api_key,
            model=settings.llm_model,
        )

    # 2. Parallel Search (Web + PubMed)
    _progress("search", "Searching web and PubMed in parallel...")
    web_context, web_sources, pubmed_context, pubmed_sources, pubmed_df = _parallel_search(
        genes, disease, enricher.filtered_results, _progress,
        query_plan=query_plan,
    )

    # 3. Relation Extraction from PubMed abstracts
    relations_df = pd.DataFrame()
    entities_df = pd.DataFrame()
    if settings.openai_api_key and pubmed_df is not None and not pubmed_df.empty:
        total_abs = len(pubmed_df)
        _progress("extraction", f"Extracting relations from {total_abs} abstracts...")
        try:
            llm = ChatOpenAI(
                model=settings.llm_model,
                temperature=0,
                api_key=settings.openai_api_key,
            )
            extractor = RelationExtractor(llm=llm)
            relations_df = extractor.extract(
                pubmed_df,
                on_progress=lambda i, n: _progress(
                    "extraction", f"Extracting abstract {i}/{n}..."
                ),
            )
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

            go_df = enricher.filtered_results.get("GO", pd.DataFrame())
            kegg_df = enricher.filtered_results.get("KEGG", pd.DataFrame())

            relations_text = (
                _compact_relations(relations_df)
                if not relations_df.empty
                else "No extracted relations available."
            )

            inputs = {
                "context": f"Disease context: {disease}",
                "genes": ", ".join(genes),
                "go_table": _compact_enrichment(go_df),
                "kegg_table": _compact_enrichment(kegg_df),
                "web_search": _truncate(web_context, 2000) if web_context else "No web search results available.",
                "pubmed": _truncate(pubmed_context, 4000) if pubmed_context else "No PubMed results available.",
                "relations": relations_text,
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
        "query_plan": {
            "summary": query_plan.summary,
            "intents": [i.model_dump() for i in query_plan.intents],
            "top_genes": query_plan.top_genes,
        },
    }

    _progress("done", "Pipeline complete.")
    return result


def _parallel_search(
    genes: List[str],
    disease: str,
    enrichment_results: Dict,
    _progress: Callable,
    query_plan: Optional[QueryPlan] = None,
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
            if query_plan and query_plan.intents:
                searcher.search_from_plan(query_plan.intents)
            else:
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
            fetcher = PubMedFetcher(email=settings.pubmed_email, max_results=5)
            if query_plan and query_plan.intents:
                fetcher.search_from_plan(query_plan.intents)
            else:
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

    _progress("search", "All searches complete.", data={
        "sources": {
            "web": web_sources,
            "pubmed": pubmed_sources,
        },
    })
    return web_context, web_sources, pubmed_context, pubmed_sources, pubmed_df


def save_result(result: Dict, output: Path) -> None:
    """Save pipeline result to JSON file."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"Results saved to: {output}")
