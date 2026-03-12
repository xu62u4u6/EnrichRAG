"""Normalize STRING protein links to canonical gene symbols."""

from __future__ import annotations

import csv
import logging
import os
from pathlib import Path

from enrichrag.knowledge_graph.build_gene_map import load_gene_map
from enrichrag.knowledge_graph.progress import ProgressEvent, ProgressReporter

logger = logging.getLogger(__name__)

EDGE_HEADER = "source\tsource_type\ttarget\ttarget_type\trelation\tevidence\tpmid\tsource_db\tscore\tmetadata_json\n"


def normalize_string(
    links_path: str | Path,
    gene_map_path: str | Path,
    output_path: str | Path,
    score_threshold: int = 700,
    progress: ProgressReporter | None = None,
) -> int:
    """Read STRING protein links, resolve to gene symbols, write TSV."""
    gene_map = load_gene_map(gene_map_path)
    links_path = Path(links_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_size = links_path.stat().st_size
    count = 0
    skipped = 0
    bytes_read = 0

    with open(links_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8", newline="") as fout:
        fout.write(EDGE_HEADER)
        reader = csv.DictReader(fin, delimiter=" ")
        for row in reader:
            combined = row["combined_score"]
            if combined.isdigit() and int(combined) < score_threshold:
                continue

            p1 = row["protein1"]
            p2 = row["protein2"]
            sym1 = gene_map.get(p1)
            sym2 = gene_map.get(p2)
            if not sym1 or not sym2:
                skipped += 1
                continue

            score = float(combined) / 1000.0
            fout.write(
                f"{sym1}\tgene\t{sym2}\tgene\tinteract\t"
                f"STRING protein-protein interaction\t\tstring\t{score}\t{{}}\n"
            )
            count += 1

            if progress and count % 100_000 == 0:
                bytes_read = fin.buffer.tell() if hasattr(fin, "buffer") else 0
                progress.report(ProgressEvent(
                    step="normalize_string", message=f"STRING: {count:,} edges",
                    current=bytes_read, total=total_size, unit="bytes",
                ))

    if progress:
        progress.report(ProgressEvent(
            step="normalize_string", message=f"STRING: {count:,} edges, {skipped:,} skipped",
            current=total_size, total=total_size, unit="bytes", done=True,
        ))
    logger.info("STRING: %d edges written, %d skipped (unmapped)", count, skipped)
    return count
