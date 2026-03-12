import gzip
from pathlib import Path

from enrichrag.core.gene_validation import GeneValidationService


def _write_gene_info(path: Path) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(
            "#tax_id\tGeneID\tSymbol\tLocusTag\tSynonyms\tdbXrefs\tchromosome\tmap_location\t"
            "description\ttype_of_gene\tSymbol_from_nomenclature_authority\t"
            "Full_name_from_nomenclature_authority\tNomenclature_status\tOther_designations\t"
            "Modification_date\tFeature_type\n"
        )
        handle.write(
            "9606\t7157\tTP53\t-\tP53|BCC7\tHGNC:HGNC:11998\t17\t17p13.1\t"
            "tumor protein p53\tprotein-coding\tTP53\ttumor protein p53\tO\t-\t20260303\t-\n"
        )


def test_validate_and_profile_lookup(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "kg.db"
    gene_info_path = tmp_path / "Homo_sapiens.gene_info.gz"
    _write_gene_info(gene_info_path)

    from enrichrag.settings import settings

    monkeypatch.setattr(settings, "kg_db_path", str(db_path))
    monkeypatch.setattr(settings, "kg_data_dir", str(tmp_path))

    service = GeneValidationService()
    with service.db.connect() as conn:
        conn.execute(
            "INSERT INTO gene_id_map(input_id, canonical_symbol, source) VALUES (?, ?, ?)",
            ("TP53", "TP53", "ncbi_symbol"),
        )
        conn.execute(
            "INSERT INTO gene_id_map(input_id, canonical_symbol, source) VALUES (?, ?, ?)",
            ("P53", "TP53", "ncbi_synonym"),
        )

    result = service.validate(["TP53", "P53", "NOPE"])

    assert result["normalized_genes"] == ["TP53"]
    assert result["summary"] == {"accepted": 1, "remapped": 1, "rejected": 1, "total": 3}
    assert result["rows"][0]["gene_id"] == "7157"
    assert result["rows"][1]["status"] == "remapped"
    assert result["rows"][2]["status"] == "rejected"

    profile = service.get_profile("TP53")
    assert profile is not None
    assert profile["official_full_name"] == "tumor protein p53"
