"""Shared builders for chat context derived from pipeline results."""

from __future__ import annotations

import json
from typing import Dict, Iterable


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n... [truncated for token limit]"


def _compact_relations(relations: Iterable[dict], max_rows: int = 40) -> str:
    rows = list(relations or [])
    if not rows:
        return "No extracted relations available."

    lines = []
    for row in rows[:max_rows]:
        pmid = row.get("pmid", "")
        source = row.get("source", "")
        relation = row.get("relation", "")
        target = row.get("target", "")
        lines.append(f"- {source} -[{relation}]-> {target} ({pmid})")
    if len(rows) > max_rows:
        lines.append(f"... and {len(rows) - max_rows} more relations")
    return "\n".join(lines)


def _compact_enrichment(result: dict, max_terms_per_db: int = 15) -> str:
    enrichment_results = result.get("enrichment_results") or {}
    if not enrichment_results:
        return "No significant enrichment results."

    lines = []
    for db_name, rows in enrichment_results.items():
        db_rows = list(rows or [])
        lines.append(f"{db_name} ({len(db_rows)} terms)")
        for row in db_rows[:max_terms_per_db]:
            term = row.get("term", "")
            p = row.get("p_adjusted", row.get("p_value", "n/a"))
            overlap = row.get("overlap", "")
            genes = str(row.get("genes", "")).replace(";", ", ")
            lines.append(f"- {term} (p={p}, {overlap}): {genes}")
        if len(db_rows) > max_terms_per_db:
            lines.append(f"... and {len(db_rows) - max_terms_per_db} more {db_name} terms")
        lines.append("")
    return "\n".join(lines).strip()


def _compact_sources(result: dict, max_items: int = 8) -> str:
    sources = result.get("sources") or {}
    web_sources = list(sources.get("web") or [])
    pubmed_sources = list(sources.get("pubmed") or [])
    if not web_sources and not pubmed_sources:
        return "No sources available."

    lines = []
    if pubmed_sources:
        lines.append("PubMed sources:")
        for row in pubmed_sources[:max_items]:
            pmid = row.get("pmid", "")
            title = row.get("title", "")
            journal = row.get("journal", "")
            lines.append(f"- PMID {pmid}: {title} ({journal})")
        if len(pubmed_sources) > max_items:
            lines.append(f"... and {len(pubmed_sources) - max_items} more PubMed sources")
    if web_sources:
        if lines:
            lines.append("")
        lines.append("Web sources:")
        for row in web_sources[:max_items]:
            title = row.get("title", "")
            url = row.get("url", "")
            lines.append(f"- {title}: {url}")
        if len(web_sources) > max_items:
            lines.append(f"... and {len(web_sources) - max_items} more web sources")
    return "\n".join(lines)


def _compact_graph(result: dict) -> str:
    graph = result.get("graph") or {}
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    if not nodes and not edges:
        return "No graph data available."
    return f"Graph summary: {len(nodes)} nodes, {len(edges)} edges."


def _compact_validation(result: dict) -> str:
    validation = result.get("gene_validation")
    if not validation:
        return "No validation details available."

    summary = validation.get("summary") or {}
    rows = list(validation.get("rows") or [])
    lines = [
        "Gene validation summary:",
        (
            f"- accepted={summary.get('accepted', 0)}, "
            f"remapped={summary.get('remapped', 0)}, "
            f"rejected={summary.get('rejected', 0)}, "
            f"total={summary.get('total', 0)}"
        ),
    ]
    for row in rows[:20]:
        lines.append(
            f"- {row.get('input_gene', '')} -> {row.get('normalized_gene', '-')}"
            f" [{row.get('status', '')}]"
        )
    if len(rows) > 20:
        lines.append(f"... and {len(rows) - 20} more validation rows")
    return "\n".join(lines)


def build_chat_prompt_inputs(result: Dict, question: str) -> Dict[str, str]:
    """Build prompt variables for chat from the full pipeline result."""
    disease = result.get("disease_context", "Analysis")
    genes = ", ".join(result.get("input_genes") or [])
    query_plan = result.get("query_plan") or {}
    report = result.get("llm_insight") or "No report generated."

    compact_result = {
        "disease_context": disease,
        "input_genes": result.get("input_genes") or [],
        "query_plan": query_plan,
        "sources": result.get("sources") or {},
    }

    return {
        "context": f"Disease context: {disease}",
        "genes": genes or "No genes provided.",
        "report": report,
        "query_plan": query_plan.get("summary", "No query plan summary available."),
        "enrichment": _compact_enrichment(result),
        "relations": _compact_relations(result.get("gene_relations") or []),
        "sources": _compact_sources(result),
        "graph": _compact_graph(result),
        "validation": _compact_validation(result),
        "result_json": _truncate(json.dumps(compact_result, ensure_ascii=False, indent=2), 4000),
        "question": question,
    }
