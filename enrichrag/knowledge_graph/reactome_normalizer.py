"""Normalize Reactome FIsInGene_with_annotations to canonical gene symbols."""

from __future__ import annotations

import logging
from pathlib import Path

from enrichrag.knowledge_graph.build_gene_map import load_gene_map

logger = logging.getLogger(__name__)

EDGE_HEADER = "source\tsource_type\ttarget\ttarget_type\trelation\tevidence\tpmid\tsource_db\tscore\tmetadata_json\n"


def normalize_reactome(
    fi_path: str | Path,
    gene_map_path: str | Path,
    output_path: str | Path,
) -> int:
    """Parse FIsInGene_with_annotations.txt, write TSV.

    Expected format: Gene1\\tGene2\\tAnnotation\\tDirection\\tScore
    Returns the number of edges written.
    """
    gene_map = load_gene_map(gene_map_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(fi_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8", newline="") as fout:
        fout.write(EDGE_HEADER)
        header_skipped = False
        for line in fin:
            line = line.rstrip("\n")
            if not line:
                continue
            # Skip header line
            if not header_skipped:
                header_skipped = True
                if line.startswith("Gene1") or line.startswith("#"):
                    continue

            parts = line.split("\t")
            if len(parts) < 2:
                continue

            gene1 = parts[0].strip()
            gene2 = parts[1].strip()
            annotation = parts[2].strip() if len(parts) > 2 else ""
            direction = parts[3].strip() if len(parts) > 3 else ""
            score = parts[4].strip() if len(parts) > 4 else "1.0"

            # Resolve via gene_map, fall back to raw name
            sym1 = gene_map.get(gene1, gene1)
            sym2 = gene_map.get(gene2, gene2)

            relation = annotation if annotation else "interact"
            try:
                score_val = float(score)
            except ValueError:
                score_val = 1.0

            metadata = "{}"
            if direction:
                metadata = f'{{"direction": "{direction}"}}'

            fout.write(
                f"{sym1}\tgene\t{sym2}\tgene\t{relation}\t"
                f"Reactome FI\t\treactome\t{score_val}\t{metadata}\n"
            )
            count += 1

    logger.info("Reactome: %d edges written", count)
    return count
