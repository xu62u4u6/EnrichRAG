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

    def lookup(
        self,
        genes: Iterable[str],
        disease: str | None = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        gene_list = sorted({gene.strip() for gene in genes if gene and gene.strip()})
        if not gene_list:
            return pd.DataFrame(
                columns=[
                    "source",
                    "source_type",
                    "target",
                    "target_type",
                    "relation",
                    "evidence",
                    "pmid",
                ]
            )

        # Resolve to canonical symbols
        canonical = self._resolve_symbols(gene_list)

        placeholders = ",".join("?" for _ in canonical)
        params = list(canonical) + list(canonical) + [limit]
        sql = f"""
            SELECT
                source,
                source_type,
                target,
                target_type,
                relation,
                evidence,
                pmid
            FROM edges
            WHERE source IN ({placeholders})
               OR target IN ({placeholders})
            ORDER BY score DESC, id ASC
            LIMIT ?
        """

        df = self._query(sql, params)
        if disease:
            disease_lower = disease.lower()
            disease_hits = df["target"].astype(str).str.lower().eq(disease_lower)
            disease_hits |= df["source"].astype(str).str.lower().eq(disease_lower)
            if disease_hits.any():
                prioritized = pd.concat([df[disease_hits], df[~disease_hits]], ignore_index=True)
                return prioritized.drop_duplicates(
                    subset=["source", "target", "relation", "pmid"],
                    keep="first",
                )
        return df.drop_duplicates(subset=["source", "target", "relation", "pmid"], keep="first")

    def _query(self, sql: str, params: list[object]) -> pd.DataFrame:
        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return pd.DataFrame([dict(row) for row in rows])
