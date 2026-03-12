"""Load processed TSV files into SQLite."""

from __future__ import annotations

import csv
import logging
import sqlite3
from pathlib import Path

from enrichrag.knowledge_graph.base import KnowledgeGraphDB
from enrichrag.knowledge_graph.progress import ProgressEvent, ProgressReporter

logger = logging.getLogger(__name__)

BATCH_SIZE = 50_000


def _load_tsv_edges(
    conn: sqlite3.Connection, tsv_path: Path,
    progress: ProgressReporter | None = None, step: str = "load",
) -> int:
    """Load a single edge TSV into the edges table."""
    count = 0
    batch: list[tuple] = []
    with open(tsv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            batch.append((
                row["source"],
                row["source_type"],
                row["target"],
                row["target_type"],
                row["relation"],
                row["evidence"],
                row["pmid"],
                row["source_db"],
                float(row.get("score", 0)),
                row.get("metadata_json", "{}"),
            ))
            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    """INSERT INTO edges(
                        source, source_type, target, target_type, relation,
                        evidence, pmid, source_db, score, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    batch,
                )
                count += len(batch)
                batch.clear()
                if progress:
                    progress.report(ProgressEvent(
                        step=step, message=f"Loading {tsv_path.stem}: {count:,} rows",
                        current=count, total=0, unit="rows",
                    ))
    if batch:
        conn.executemany(
            """INSERT INTO edges(
                source, source_type, target, target_type, relation,
                evidence, pmid, source_db, score, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            batch,
        )
        count += len(batch)
    return count


def _load_gene_id_map(
    conn: sqlite3.Connection, tsv_path: Path,
    progress: ProgressReporter | None = None,
) -> int:
    """Load gene_id_map.tsv into gene_id_map table."""
    count = 0
    batch: list[tuple] = []
    with open(tsv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            batch.append((row["input_id"], row["canonical_symbol"], row.get("source", "")))
            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    "INSERT OR REPLACE INTO gene_id_map(input_id, canonical_symbol, source) VALUES (?, ?, ?)",
                    batch,
                )
                count += len(batch)
                batch.clear()
                if progress:
                    progress.report(ProgressEvent(
                        step="load_gene_map", message=f"Loading gene map: {count:,} entries",
                        current=count, total=0, unit="entries",
                    ))
    if batch:
        conn.executemany(
            "INSERT OR REPLACE INTO gene_id_map(input_id, canonical_symbol, source) VALUES (?, ?, ?)",
            batch,
        )
        count += len(batch)
    return count


def load_all(
    db_path: str | Path,
    processed_dir: str | Path,
    progress: ProgressReporter | None = None,
) -> dict[str, int]:
    """Load all processed TSV files into the SQLite database."""
    db = KnowledgeGraphDB(db_path)
    db.initialize()
    processed_dir = Path(processed_dir)
    result: dict[str, int] = {}

    with db.connect() as conn:
        conn.execute("DELETE FROM gene_id_map")
        conn.execute("DELETE FROM edges")

        gene_map_path = processed_dir / "gene_id_map.tsv"
        if gene_map_path.exists():
            n = _load_gene_id_map(conn, gene_map_path, progress)
            result["gene_id_map"] = n
            logger.info("Loaded %d gene ID mappings", n)
            if progress:
                progress.report(ProgressEvent(
                    step="load_gene_map", message=f"Loaded {n:,} gene ID mappings",
                    current=n, total=n, unit="entries", done=True,
                ))

        for tsv_path in sorted(processed_dir.glob("*_edges.tsv")):
            source_name = tsv_path.stem.replace("_edges", "")
            step = f"load_{source_name}"
            n = _load_tsv_edges(conn, tsv_path, progress, step)
            result[source_name] = n
            logger.info("Loaded %d edges from %s", n, source_name)
            if progress:
                progress.report(ProgressEvent(
                    step=step, message=f"Loaded {n:,} {source_name} edges",
                    current=n, total=n, unit="rows", done=True,
                ))

        if progress:
            progress.report(ProgressEvent(
                step="load_analyze", message="Running ANALYZE...",
                current=0, total=0, unit="",
            ))
        conn.execute("ANALYZE")

    return result
