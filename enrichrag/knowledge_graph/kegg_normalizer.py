"""Normalize KEGG KGML pathway relations to canonical gene symbols."""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from enrichrag.knowledge_graph.build_gene_map import load_gene_map

logger = logging.getLogger(__name__)

EDGE_HEADER = "source\tsource_type\ttarget\ttarget_type\trelation\tevidence\tpmid\tsource_db\tscore\tmetadata_json\n"


def normalize_kegg(
    kgml_paths: list[str | Path],
    gene_map_path: str | Path,
    output_path: str | Path,
) -> int:
    """Parse KGML files, keep original subtypes, write TSV.

    Returns the number of edges written.
    """
    gene_map = load_gene_map(gene_map_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(output_path, "w", encoding="utf-8", newline="") as fout:
        fout.write(EDGE_HEADER)
        for kgml_path in kgml_paths:
            kgml_path = Path(kgml_path)
            try:
                root = ET.parse(kgml_path).getroot()
            except ET.ParseError:
                logger.warning("Failed to parse %s", kgml_path)
                continue

            pathway_name = root.attrib.get("title", kgml_path.stem)

            # Build entry ID -> gene symbols
            entries: dict[str, list[str]] = {}
            for entry in root.findall("entry"):
                if entry.attrib.get("type") != "gene":
                    continue
                names = entry.attrib.get("name", "")
                symbols = []
                for token in names.split():
                    if ":" not in token:
                        continue
                    _, value = token.split(":", 1)
                    symbols.extend(part for part in value.split("/") if part)
                entries[entry.attrib["id"]] = symbols

            for relation in root.findall("relation"):
                src_genes = entries.get(relation.attrib.get("entry1", ""), [])
                tgt_genes = entries.get(relation.attrib.get("entry2", ""), [])
                subtype_el = relation.find("subtype")
                subtype_name = (
                    subtype_el.attrib.get("name", "association")
                    if subtype_el is not None
                    else "association"
                )
                metadata = json.dumps(
                    {"pathway": pathway_name, "subtype": subtype_name},
                    ensure_ascii=False,
                )

                for src in src_genes:
                    # Validate via gene_map, fall back to raw symbol
                    canonical_src = gene_map.get(src, src)
                    for tgt in tgt_genes:
                        canonical_tgt = gene_map.get(tgt, tgt)
                        fout.write(
                            f"{canonical_src}\tgene\t{canonical_tgt}\tgene\t{subtype_name}\t"
                            f"KEGG {pathway_name}: {subtype_name}\t\tkegg\t1.0\t{metadata}\n"
                        )
                        count += 1

    logger.info("KEGG: %d edges from %d pathways", count, len(kgml_paths))
    return count
