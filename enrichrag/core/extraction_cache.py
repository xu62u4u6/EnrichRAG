"""SQLite cache for PubMed extraction results."""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from enrichrag.logging import logger

_DEFAULT_DB = Path.home() / ".enrichrag" / "cache.db"


class ExtractionCache:
    """Caches LLM extraction results keyed by PMID.

    Schema: pmid TEXT PRIMARY KEY, result_json TEXT, created_at TIMESTAMP
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or _DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS extraction_cache ("
            "  pmid TEXT PRIMARY KEY,"
            "  result_json TEXT NOT NULL,"
            "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        self._conn.commit()

    def get(self, pmid: str) -> Optional[dict]:
        """Return cached result dict or None."""
        row = self._conn.execute(
            "SELECT result_json FROM extraction_cache WHERE pmid = ?", (pmid,)
        ).fetchone()
        if row:
            return json.loads(row[0])
        return None

    def put(self, pmid: str, result: dict) -> None:
        """Store extraction result."""
        self._conn.execute(
            "INSERT OR REPLACE INTO extraction_cache (pmid, result_json) VALUES (?, ?)",
            (pmid, json.dumps(result, ensure_ascii=False)),
        )
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM extraction_cache").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self._conn.close()
