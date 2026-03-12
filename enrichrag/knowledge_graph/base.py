"""SQLite storage for the local biomedical knowledge graph."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class KnowledgeGraphDB:
    """Manage the SQLite database used by the local knowledge graph."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS gene_id_map (
                    input_id TEXT PRIMARY KEY,
                    canonical_symbol TEXT NOT NULL,
                    source TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    evidence TEXT DEFAULT '',
                    pmid TEXT DEFAULT '',
                    source_db TEXT NOT NULL,
                    score REAL DEFAULT 0,
                    metadata_json TEXT DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_edges_source
                    ON edges(source);
                CREATE INDEX IF NOT EXISTS idx_edges_target
                    ON edges(target);
                CREATE INDEX IF NOT EXISTS idx_edges_relation
                    ON edges(relation);
                CREATE INDEX IF NOT EXISTS idx_edges_source_db
                    ON edges(source_db);
                CREATE INDEX IF NOT EXISTS idx_gene_id_map_symbol
                    ON gene_id_map(canonical_symbol);
                """
            )
