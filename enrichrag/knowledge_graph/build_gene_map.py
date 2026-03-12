"""Build master gene ID mapping from NCBI gene_info and STRING aliases."""

from __future__ import annotations

import csv
import gzip
import logging
from pathlib import Path

from enrichrag.knowledge_graph.progress import NullProgressReporter, ProgressEvent, ProgressReporter

logger = logging.getLogger(__name__)

TSV_HEADER = "input_id\tcanonical_symbol\tsource\n"


def build_gene_map(
    ncbi_path: str | Path,
    string_aliases_path: str | Path | None = None,
    output_path: str | Path = "gene_id_map.tsv",
    progress: ProgressReporter | None = None,
) -> Path:
    """Build gene_id_map.tsv from NCBI gene_info and optionally STRING aliases.

    Returns the output path.
    """
    ncbi_path = Path(ncbi_path)
    output_path = Path(output_path)

    # Phase 1: Parse NCBI gene_info
    gene_map: dict[str, tuple[str, str]] = {}  # input_id -> (canonical_symbol, source)
    canonical_symbols: set[str] = set()

    opener = gzip.open if ncbi_path.suffix == ".gz" else open
    with opener(ncbi_path, "rt", encoding="utf-8", newline="") as handle:  # type: ignore[call-overload]
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if row.get("#tax_id") and int(row["#tax_id"]) != 9606:
                continue
            symbol = row["Symbol"]
            gene_id = row["GeneID"]
            canonical_symbols.add(symbol)

            # GeneID -> Symbol
            gene_map[gene_id] = (symbol, "ncbi_geneid")
            # Symbol -> Symbol (identity)
            gene_map[symbol] = (symbol, "ncbi_symbol")
            # Synonyms -> Symbol
            synonyms = row.get("Synonyms", "-")
            if synonyms and synonyms != "-":
                for syn in synonyms.split("|"):
                    syn = syn.strip()
                    if syn and syn not in gene_map:
                        gene_map[syn] = (symbol, "ncbi_synonym")

    logger.info("NCBI gene_info: %d mappings, %d canonical symbols", len(gene_map), len(canonical_symbols))
    if progress:
        progress.report(ProgressEvent(
            step="build_gene_map", message=f"NCBI: {len(gene_map):,} mappings, {len(canonical_symbols):,} symbols",
            current=len(gene_map), total=0, unit="entries",
        ))

    # Phase 2: Parse STRING aliases (optional)
    if string_aliases_path:
        string_path = Path(string_aliases_path)
        string_opener = gzip.open if string_path.suffix == ".gz" else open
        string_count = 0
        with string_opener(string_path, "rt", encoding="utf-8", newline="") as handle:  # type: ignore[call-overload]
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                source_field = row.get("source", "")
                if source_field not in ("Ensembl_HGNC", "BioMart_HUGO"):
                    continue
                protein_id = row["#string_protein_id"]
                alias = row["alias"]
                # Only keep if alias is a known canonical symbol
                if alias in canonical_symbols and protein_id not in gene_map:
                    gene_map[protein_id] = (alias, f"string_{source_field}")
                    string_count += 1
        logger.info("STRING aliases: added %d protein ID mappings", string_count)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        f.write(TSV_HEADER)
        for input_id, (symbol, src) in sorted(gene_map.items()):
            f.write(f"{input_id}\t{symbol}\t{src}\n")

    logger.info("Wrote %d entries to %s", len(gene_map), output_path)
    if progress:
        progress.report(ProgressEvent(
            step="build_gene_map", message=f"Gene map: {len(gene_map):,} entries",
            current=len(gene_map), total=len(gene_map), unit="entries", done=True,
        ))
    return output_path


def load_gene_map(path: str | Path) -> dict[str, str]:
    """Load gene_id_map.tsv into a dict: input_id -> canonical_symbol."""
    result: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            result[row["input_id"]] = row["canonical_symbol"]
    return result
