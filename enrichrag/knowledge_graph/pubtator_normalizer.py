"""Normalize PubTator relation2pubtator3 to canonical gene symbols."""

from __future__ import annotations

import logging
from pathlib import Path

from enrichrag.knowledge_graph.build_gene_map import load_gene_map
from enrichrag.knowledge_graph.progress import ProgressEvent, ProgressReporter

logger = logging.getLogger(__name__)

EDGE_HEADER = "source\tsource_type\ttarget\ttarget_type\trelation\tevidence\tpmid\tsource_db\tscore\tmetadata_json\n"

# Estimated total lines in relation2pubtator3 for progress reporting
_ESTIMATED_TOTAL_LINES = 39_000_000


def _parse_entity(raw: str, gene_map: dict[str, str]) -> tuple[str, str] | None:
    """Parse 'Type|ID' entity, resolve Gene IDs. Returns (name, type) or None."""
    if "|" not in raw:
        return None
    entity_type, entity_id = raw.split("|", 1)
    entity_type_lower = entity_type.lower()

    if entity_type_lower == "gene":
        symbol = gene_map.get(entity_id)
        if not symbol:
            return None
        return symbol, "gene"
    elif entity_type_lower in ("disease", "chemical"):
        return entity_id, entity_type_lower
    else:
        return entity_id, entity_type_lower


def normalize_pubtator(
    relation_path: str | Path,
    gene_map_path: str | Path,
    output_path: str | Path,
    progress: ProgressReporter | None = None,
) -> int:
    """Stream-parse relation2pubtator3, resolve gene IDs, write TSV."""
    gene_map = load_gene_map(gene_map_path)
    relation_path = Path(relation_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_size = relation_path.stat().st_size
    count = 0
    skipped = 0
    lines_read = 0

    with open(relation_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8", newline="") as fout:
        fout.write(EDGE_HEADER)
        for line in fin:
            lines_read += 1
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue

            pmid = parts[0]
            relation_type = parts[1]
            raw_entity1 = parts[2]
            raw_entity2 = parts[3]

            if "Gene|" not in raw_entity1 and "Gene|" not in raw_entity2:
                continue

            parsed1 = _parse_entity(raw_entity1, gene_map)
            parsed2 = _parse_entity(raw_entity2, gene_map)
            if not parsed1 or not parsed2:
                skipped += 1
                continue

            name1, type1 = parsed1
            name2, type2 = parsed2

            fout.write(
                f"{name1}\t{type1}\t{name2}\t{type2}\t{relation_type}\t"
                f"PubTator relation\tPMID:{pmid}\tpubtator\t1.0\t{{}}\n"
            )
            count += 1

            if progress and lines_read % 500_000 == 0:
                progress.report(ProgressEvent(
                    step="normalize_pubtator",
                    message=f"PubTator: {lines_read:,} lines, {count:,} edges",
                    current=lines_read, total=_ESTIMATED_TOTAL_LINES, unit="lines",
                ))

    if progress:
        progress.report(ProgressEvent(
            step="normalize_pubtator",
            message=f"PubTator: {count:,} edges, {skipped:,} skipped",
            current=lines_read, total=lines_read, unit="lines", done=True,
        ))
    logger.info("PubTator: %d edges written, %d skipped (unmapped)", count, skipped)
    return count
