"""Query interface for the local biomedical knowledge graph."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from enrichrag.knowledge_graph.base import KnowledgeGraphDB


class KnowledgeGraph:
    """Look up local relations using the same schema as RelationExtractor."""

    def __init__(self, db_path: str | Path):
        self.db = KnowledgeGraphDB(db_path)
        self.db.initialize()

    def is_ready(self) -> bool:
        with self.db.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM edges").fetchone()
        return bool(row["count"])

    def _resolve_symbols(self, genes: list[str]) -> list[str]:
        """Resolve input gene names to canonical symbols via gene_id_map."""
        if not genes:
            return genes
        placeholders = ",".join("?" for _ in genes)
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT input_id, canonical_symbol FROM gene_id_map WHERE input_id IN ({placeholders})",
                genes,
            ).fetchall()
        resolved = {row["input_id"]: row["canonical_symbol"] for row in rows}
        # Use resolved symbol if found, otherwise keep original
        return list({resolved.get(g, g) for g in genes})

    COLUMNS = [
        "source", "source_type", "target", "target_type",
        "relation", "evidence", "pmid", "source_db",
    ]

    def lookup(
        self,
        genes: Iterable[str],
        disease: str | None = None,
        limit: int = 500,
        per_source_limit: int = 200,
    ) -> pd.DataFrame:
        gene_list = sorted({gene.strip() for gene in genes if gene and gene.strip()})
        if not gene_list:
            return pd.DataFrame(columns=self.COLUMNS)

        # Resolve to canonical symbols
        canonical = self._resolve_symbols(gene_list)

        # Take top N per source_db so no single source dominates
        placeholders = ",".join("?" for _ in canonical)
        params = list(canonical) + list(canonical) + [per_source_limit]
        sql = f"""
            SELECT source, source_type, target, target_type,
                   relation, evidence, pmid, source_db
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY source_db
                           ORDER BY score DESC, id ASC
                       ) AS rn
                FROM edges
                WHERE source IN ({placeholders})
                   OR target IN ({placeholders})
            )
            WHERE rn <= ?
        """

        df = self._query(sql, params)
        dedup_cols = ["source", "target", "relation", "pmid", "source_db"]
        df = df.drop_duplicates(subset=dedup_cols, keep="first")

        if disease:
            disease_lower = disease.lower()
            disease_hits = df["target"].astype(str).str.lower().eq(disease_lower)
            disease_hits |= df["source"].astype(str).str.lower().eq(disease_lower)
            if disease_hits.any():
                df = pd.concat([df[disease_hits], df[~disease_hits]], ignore_index=True)

        # Balanced sampling: take up to limit/n_sources per source, then fill remainder
        source_dbs = df["source_db"].unique()
        n_sources = len(source_dbs)
        if n_sources > 0 and len(df) > limit:
            per_src = max(limit // n_sources, 1)
            parts = []
            for sdb in source_dbs:
                parts.append(df[df["source_db"] == sdb].head(per_src))
            result = pd.concat(parts, ignore_index=True)
            # Fill remaining quota from leftover rows
            if len(result) < limit:
                used_idx = result.index
                remaining = df[~df.index.isin(used_idx)]
                result = pd.concat(
                    [result, remaining.head(limit - len(result))],
                    ignore_index=True,
                )
            return result
        return df.head(limit)

    def _query(self, sql: str, params: list[object]) -> pd.DataFrame:
        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return pd.DataFrame([dict(row) for row in rows])
