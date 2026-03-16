"""Build a graph JSON structure from enrichment results and extracted relations."""

import math
from typing import Dict, List

import pandas as pd

from enrichrag.knowledge_graph.relation_taxonomy import get_group, normalize


def _clean_scalar(value: object, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, float) and not math.isfinite(value):
        return default
    text = str(value).strip()
    return text if text and text.lower() != "nan" else default


def build_graph_json(
    input_genes: List[str],
    enrichment_results: Dict[str, pd.DataFrame],
    relations_df: pd.DataFrame,
    entities_df: pd.DataFrame | None = None,
) -> Dict:
    """
    Build a graph JSON for frontend rendering.

    Nodes:
      - gene nodes (from input_genes + relation participants)
      - term nodes (from enrichment GO/KEGG terms)
      - disease/drug/pathway nodes (from extracted entities)

    Edges:
      - gene → term (from enrichment overlap)
      - entity → entity (from RelationExtractor)

    Returns:
        {"nodes": [...], "edges": [...]}
    """
    nodes: Dict[str, dict] = {}
    edges: List[dict] = []

    # --- Input gene nodes ---
    for gene in input_genes:
        gid = f"gene:{gene}"
        nodes[gid] = {
            "id": gid,
            "label": gene,
            "type": "gene",
            "is_input": True,
        }

    # --- Entity nodes from extraction ---
    if entities_df is not None and not entities_df.empty:
        for _, row in entities_df.iterrows():
            etype = row.get("type", "other")
            name = row.get("name", "")
            nid = f"{etype}:{name}"
            if nid not in nodes:
                nodes[nid] = {
                    "id": nid,
                    "label": name,
                    "type": etype,
                    "is_input": False,
                }

    # --- Enrichment term nodes + gene-term edges ---
    for db_label, df in enrichment_results.items():
        if isinstance(df, list):
            df = pd.DataFrame(df)
        if df.empty:
            continue

        term_type = "go" if db_label == "GO" else "kegg"
        for _, row in df.iterrows():
            term_name = row.get("term", row.get("Term", ""))
            p_adj = row.get("p_adjusted", row.get("Adjusted P-value", 1.0))
            genes_str = row.get("genes", row.get("Genes", ""))

            tid = f"{term_type}:{term_name}"
            if tid not in nodes:
                nodes[tid] = {
                    "id": tid,
                    "label": term_name,
                    "type": term_type,
                    "p_adjusted": p_adj,
                }

            # Parse gene overlap
            if isinstance(genes_str, str):
                overlap_genes = [g.strip() for g in genes_str.replace(";", ",").split(",") if g.strip()]
            elif isinstance(genes_str, list):
                overlap_genes = genes_str
            else:
                overlap_genes = []

            for gene in overlap_genes:
                gid = f"gene:{gene}"
                if gid not in nodes:
                    nodes[gid] = {
                        "id": gid,
                        "label": gene,
                        "type": "gene",
                        "is_input": gene in input_genes,
                    }
                edges.append({
                    "source": gid,
                    "target": tid,
                    "type": "enrichment",
                    "relation": "enrichment",
                })

    # --- Relation edges ---
    if not relations_df.empty:
        for _, row in relations_df.iterrows():
            src_name = _clean_scalar(row.get("source", ""))
            src_type = _clean_scalar(row.get("source_type", "gene"), "gene")
            tgt_name = _clean_scalar(row.get("target", ""))
            tgt_type = _clean_scalar(row.get("target_type", "gene"), "gene")
            relation = _clean_scalar(row.get("relation", "associate"), "associate")
            evidence = _clean_scalar(row.get("evidence", ""))
            pmid = _clean_scalar(row.get("pmid", ""))

            if not src_name or not tgt_name:
                continue

            src_id = f"{src_type}:{src_name}"
            tgt_id = f"{tgt_type}:{tgt_name}"

            if src_id not in nodes:
                nodes[src_id] = {
                    "id": src_id,
                    "label": src_name,
                    "type": src_type,
                    "is_input": src_name in input_genes,
                }
            if tgt_id not in nodes:
                nodes[tgt_id] = {
                    "id": tgt_id,
                    "label": tgt_name,
                    "type": tgt_type,
                    "is_input": tgt_name in input_genes,
                }

            source_db = _clean_scalar(row.get("source_db", ""))
            norm_relation = normalize(relation, source_db)
            edges.append({
                "source": src_id,
                "target": tgt_id,
                "type": "relation",
                "relation": norm_relation,
                "relation_group": get_group(norm_relation),
                "evidence": evidence,
                "pmid": pmid,
                "source_db": source_db,
            })

    # Deduplicate edges
    seen = set()
    unique_edges = []
    for e in edges:
        key = (
            e["source"],
            e["target"],
            e["type"],
            e.get("relation", ""),
            e.get("source_db", ""),
            e.get("pmid", ""),
        )
        if key not in seen:
            seen.add(key)
            unique_edges.append(e)

    return {
        "nodes": list(nodes.values()),
        "edges": unique_edges,
    }
