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
from enrichrag.knowledge_graph import KnowledgeGraph
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


def _compact_enrichment(
    df: pd.DataFrame,
    term_categories: Optional[Dict[str, str]] = None,
    top_terms_per_category: int = 2,
) -> str:
    """Convert enrichment DataFrame to grouped compact format for LLM input.

    Groups terms by category (from QueryPlanner), shows top N per group:

        DNA damage response (6 terms, top p=5.5e-06):
          - DNA repair (8/150, p=5.5e-06): BRCA1, BRCA2, RAD51
          - double-strand break repair (5/80, p=8.2e-05): BRCA1, BRCA2
          ... and 4 more terms
          Key genes: BRCA1(6), ATM(5), RAD51(4)
    """
    if df.empty:
        return "No significant enrichment results"

    sort_col = "p_adjusted" if "p_adjusted" in df.columns else "p_value"
    sorted_df = df.sort_values(sort_col, ascending=True)

    # Group by category
    groups: Dict[str, list] = {}
    for _, row in sorted_df.iterrows():
        term = str(row.get("term", ""))
        if term_categories and term in term_categories:
            cat = term_categories[term]
        else:
            cat = term  # ungrouped fallback
        groups.setdefault(cat, []).append(row)

    # Sort categories by best p-value
    cat_order = sorted(
        groups.items(),
        key=lambda x: x[1][0].get(sort_col, 1),
    )

    lines = []
    for cat, rows in cat_order:
        best_p = rows[0].get(sort_col, rows[0].get("p_value", 1))
        lines.append(f"{cat} ({len(rows)} terms, top p={best_p:.1e}):")

        # Show top N terms
        for row in rows[:top_terms_per_category]:
            term = row.get("term", "")
            p = row.get(sort_col, row.get("p_value", 1))
            overlap = row.get("overlap", "")
            genes_str = str(row.get("genes", "")).replace(";", ", ")
            lines.append(f"  - {term} (p={p:.1e}, {overlap}): {genes_str}")
        if len(rows) > top_terms_per_category:
            lines.append(f"  ... and {len(rows) - top_terms_per_category} more terms")

        # Key genes with frequency
        gene_freq: Dict[str, int] = {}
        for row in rows:
            for g in str(row.get("genes", "")).replace(",", ";").split(";"):
                g = g.strip()
                if g:
                    gene_freq[g] = gene_freq.get(g, 0) + 1
        top_g = sorted(gene_freq.items(), key=lambda x: -x[1])[:5]
        if top_g:
            gene_parts = ", ".join(f"{g}({c})" for g, c in top_g)
            lines.append(f"  Key genes: {gene_parts}")

    return "\n".join(lines)


def run_pipeline(
    genes: List[str],
    disease: str = "cancer",
    pval_threshold: float = 0.05,
    on_progress: Optional[Callable[..., None]] = None,
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
    (
        web_context,
        web_sources,
        pubmed_context,
        pubmed_sources,
        pubmed_df,
        kg_relations_df,
    ) = _parallel_search(
        genes, disease, enricher.filtered_results, _progress,
        query_plan=query_plan,
    )

    # Phase 1: Local KG graph (before extraction)
    local_rels = kg_relations_df if kg_relations_df is not None and not kg_relations_df.empty else pd.DataFrame()
    phase1_graph = build_graph_json(
        input_genes=genes,
        enrichment_results=enricher.filtered_results,
        relations_df=local_rels,
    )
    _progress("graph_update", "Local knowledge graph ready", data={"graph": phase1_graph, "phase": "local"})

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

    if kg_relations_df is not None and not kg_relations_df.empty:
        relations_df = pd.concat([relations_df, kg_relations_df], ignore_index=True)
        relations_df = relations_df.drop_duplicates(
            subset=["source", "target", "relation", "pmid"],
            keep="first",
        )
        _progress("knowledge_graph", f"Merged {len(kg_relations_df)} local KG relations.")
    else:
        _progress("knowledge_graph", "No local KG relations found.")

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
                "go_table": _compact_enrichment(go_df, query_plan.term_categories),
                "kegg_table": _compact_enrichment(kegg_df, query_plan.term_categories),
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

    # 5. Build graph (Phase 2: full graph with literature relations)
    graph_json = build_graph_json(
        input_genes=genes,
        enrichment_results=enricher.filtered_results,
        relations_df=relations_df,
        entities_df=entities_df if not entities_df.empty else None,
    )
    _progress("graph_update", "Full network graph ready", data={"graph": graph_json, "phase": "full"})

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
) -> Tuple[str, list, str, list, Optional[pd.DataFrame], pd.DataFrame]:
    """Run web search, PubMed fetch, and local KG lookup in parallel threads."""
    web_context = ""
    web_sources: list = []
    pubmed_context = ""
    pubmed_sources: list = []
    pubmed_df: Optional[pd.DataFrame] = None
    kg_relations_df = pd.DataFrame()

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

    def _kg_search() -> pd.DataFrame:
        if not settings.kg_enabled:
            _progress("knowledge_graph", "Skipping local KG lookup.")
            return pd.DataFrame()
        try:
            kg = KnowledgeGraph(settings.kg_db_path)
            if not kg.is_ready():
                _progress("knowledge_graph", "Local KG database is empty.")
                return pd.DataFrame()
            _progress("knowledge_graph", "Querying local knowledge graph...")
            df = kg.lookup(genes, disease=disease)
            _progress("knowledge_graph", f"Found {len(df)} local KG relations.")
            return df
        except Exception as e:
            logger.error(f"Local KG lookup failed: {e}")
            _progress("knowledge_graph", f"Local KG lookup failed: {e}")
            return pd.DataFrame()

    with ThreadPoolExecutor(max_workers=3) as executor:
        web_future = executor.submit(_web_search)
        pubmed_future = executor.submit(_pubmed_search)
        kg_future = executor.submit(_kg_search)

        for future in as_completed([web_future, pubmed_future, kg_future]):
            if future is web_future:
                web_context, web_sources = future.result()
            elif future is pubmed_future:
                pubmed_context, pubmed_sources, pubmed_df = future.result()
            else:
                kg_relations_df = future.result()

    _progress("search", "All searches complete.", data={
        "sources": {
            "web": web_sources,
            "pubmed": pubmed_sources,
        },
    })
    return web_context, web_sources, pubmed_context, pubmed_sources, pubmed_df, kg_relations_df


def save_result(result: Dict, output: Path) -> None:
    """Save pipeline result to JSON file."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"Results saved to: {output}")
