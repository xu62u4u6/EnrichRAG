"""Local gene validation and profile lookup using KG SQLite + gene_info.gz."""

from __future__ import annotations

import csv
import gzip
from pathlib import Path
from typing import Iterable

from enrichrag.knowledge_graph.base import KnowledgeGraphDB
from enrichrag.settings import settings


class GeneValidationService:
    """Validate genes against local mappings and expose cached local profiles."""

    def __init__(self, db_path: str | Path | None = None):
        self.db = KnowledgeGraphDB(db_path or settings.kg_db_path)
        self.db.initialize()

    def validate(self, genes: Iterable[str]) -> dict:
        raw_genes = [gene.strip() for gene in genes if gene and gene.strip()]
        if not raw_genes:
            return {
                "normalized_genes": [],
                "accepted": [],
                "remapped": [],
                "rejected": [],
                "rows": [],
                "summary": {"accepted": 0, "remapped": 0, "rejected": 0, "total": 0},
            }

        mapping = self._resolve_inputs(raw_genes)
        canonical_genes = []
        for gene in raw_genes:
            entry = mapping.get(gene)
            if entry:
                canonical = entry["canonical_symbol"]
                if canonical not in canonical_genes:
                    canonical_genes.append(canonical)

        profiles = self._ensure_profiles(canonical_genes)
        accepted = []
        remapped = []
        rejected = []
        rows = []

        for gene in raw_genes:
            entry = mapping.get(gene)
            if not entry:
                row = {
                    "input_gene": gene,
                    "normalized_gene": "",
                    "status": "rejected",
                    "source": "",
                    "gene_id": "",
                    "official_name": "",
                    "description": "",
                }
                rejected.append(row)
                rows.append(row)
                continue

            canonical = entry["canonical_symbol"]
            profile = profiles.get(canonical, {})
            status = "accepted" if canonical.upper() == gene.upper() else "remapped"
            row = {
                "input_gene": gene,
                "normalized_gene": canonical,
                "status": status,
                "source": entry.get("source", ""),
                "gene_id": profile.get("gene_id", ""),
                "official_name": profile.get("official_full_name", ""),
                "description": profile.get("description", ""),
            }
            if status == "accepted":
                accepted.append(row)
            else:
                remapped.append(row)
            rows.append(row)

        return {
            "normalized_genes": canonical_genes,
            "accepted": accepted,
            "remapped": remapped,
            "rejected": rejected,
            "rows": rows,
            "summary": {
                "accepted": len(accepted),
                "remapped": len(remapped),
                "rejected": len(rejected),
                "total": len(raw_genes),
            },
        }

    def get_profile(self, symbol: str) -> dict | None:
        canonical = self._resolve_symbol(symbol)
        if not canonical:
            canonical = symbol.strip().upper()
        profiles = self._ensure_profiles([canonical])
        profile = profiles.get(canonical)
        if not profile:
            return None
        return profile

    def normalize_genes(self, genes: Iterable[str]) -> list[str]:
        return self.validate(genes)["normalized_genes"]

    def _resolve_symbol(self, symbol: str) -> str | None:
        rows = self._resolve_inputs([symbol.strip()])
        entry = rows.get(symbol.strip())
        return entry["canonical_symbol"] if entry else None

    def _resolve_inputs(self, genes: list[str]) -> dict[str, dict]:
        variants = []
        for gene in genes:
            variants.append(gene)
            upper = gene.upper()
            if upper != gene:
                variants.append(upper)

        ordered_variants = list(dict.fromkeys(variants))
        placeholders = ",".join("?" for _ in ordered_variants)
        with self.db.connect() as conn:
            found = conn.execute(
                f"SELECT input_id, canonical_symbol, source FROM gene_id_map WHERE input_id IN ({placeholders})",
                ordered_variants,
            ).fetchall()

        by_input = {row["input_id"]: dict(row) for row in found}
        resolved = {}
        for gene in genes:
            resolved[gene] = by_input.get(gene) or by_input.get(gene.upper())
        return resolved

    def _ensure_profiles(self, canonical_genes: list[str]) -> dict[str, dict]:
        if not canonical_genes:
            return {}
        placeholders = ",".join("?" for _ in canonical_genes)
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM gene_profiles WHERE canonical_symbol IN ({placeholders})",
                canonical_genes,
            ).fetchall()
        profiles = {row["canonical_symbol"]: dict(row) for row in rows}
        missing = [gene for gene in canonical_genes if gene not in profiles]
        if missing:
            self._load_profiles_from_gene_info(missing)
            with self.db.connect() as conn:
                rows = conn.execute(
                    f"SELECT * FROM gene_profiles WHERE canonical_symbol IN ({placeholders})",
                    canonical_genes,
                ).fetchall()
            profiles = {row["canonical_symbol"]: dict(row) for row in rows}
        return profiles

    def _load_profiles_from_gene_info(self, canonical_genes: list[str]) -> None:
        gene_info_path = self._find_gene_info_path()
        if not gene_info_path:
            return

        target = set(canonical_genes)
        batch = []
        opener = gzip.open if gene_info_path.suffix == ".gz" else open
        with opener(gene_info_path, "rt", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                symbol = row.get("Symbol", "")
                if symbol not in target:
                    continue
                batch.append(
                    (
                        symbol,
                        row.get("GeneID", ""),
                        row.get("Symbol_from_nomenclature_authority", "") or symbol,
                        row.get("Full_name_from_nomenclature_authority", ""),
                        "" if row.get("Synonyms", "-") == "-" else row.get("Synonyms", ""),
                        row.get("description", ""),
                        row.get("type_of_gene", ""),
                        row.get("chromosome", ""),
                        row.get("map_location", ""),
                        row.get("dbXrefs", ""),
                        row.get("Modification_date", ""),
                        int(row.get("#tax_id", "9606") or "9606"),
                    )
                )
                target.discard(symbol)
                if not target:
                    break

        if not batch:
            return

        with self.db.connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO gene_profiles(
                    canonical_symbol, gene_id, official_symbol, official_full_name,
                    synonyms, description, type_of_gene, chromosome, map_location,
                    dbxrefs, modification_date, tax_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )

    def _find_gene_info_path(self) -> Path | None:
        candidates = [
            Path(settings.kg_data_dir).expanduser() / "downloads" / "Homo_sapiens.gene_info.gz",
            Path("~/.enrichrag/downloads/ncbi/Homo_sapiens.gene_info.gz").expanduser(),
            Path(settings.kg_data_dir).expanduser() / "downloads" / "Homo_sapiens.gene_info",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None
