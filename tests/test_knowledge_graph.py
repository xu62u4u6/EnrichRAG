from pathlib import Path

from enrichrag.knowledge_graph import KnowledgeGraph, KnowledgeGraphDB


def test_knowledge_graph_lookup(tmp_path: Path):
    db_path = tmp_path / "kg.db"
    db = KnowledgeGraphDB(db_path)
    db.initialize()
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO edges(
                source, source_type, target, target_type, relation,
                evidence, pmid, source_db, score, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("TP53", "gene", "MDM2", "gene", "interact", "test", "PMID:1", "unit", 0.9, "{}"),
        )

    kg = KnowledgeGraph(db_path)
    result = kg.lookup(["TP53"])

    assert len(result) == 1
    assert result.iloc[0]["source"] == "TP53"
    assert result.iloc[0]["target"] == "MDM2"


def test_knowledge_graph_resolves_via_gene_id_map(tmp_path: Path):
    """Lookup resolves input names to canonical symbols via gene_id_map."""
    db_path = tmp_path / "kg.db"
    db = KnowledgeGraphDB(db_path)
    db.initialize()
    with db.connect() as conn:
        # Insert gene_id_map entry: P53 -> TP53
        conn.execute(
            "INSERT INTO gene_id_map(input_id, canonical_symbol, source) VALUES (?, ?, ?)",
            ("P53", "TP53", "ncbi_synonym"),
        )
        conn.execute(
            """
            INSERT INTO edges(
                source, source_type, target, target_type, relation,
                evidence, pmid, source_db, score, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("TP53", "gene", "MDM2", "gene", "interact", "test", "PMID:1", "unit", 0.9, "{}"),
        )

    kg = KnowledgeGraph(db_path)
    result = kg.lookup(["P53"])

    assert len(result) == 1
    assert result.iloc[0]["source"] == "TP53"
    assert result.iloc[0]["target"] == "MDM2"


def test_build_gene_map(tmp_path: Path):
    """build_gene_map produces correct TSV from NCBI gene_info."""
    from enrichrag.knowledge_graph.build_gene_map import build_gene_map, load_gene_map

    gene_info = tmp_path / "Homo_sapiens.gene_info"
    gene_info.write_text(
        "#tax_id\tGeneID\tSymbol\tLocusTag\tSynonyms\n"
        "9606\t7157\tTP53\t-\tP53|LFS1\n"
        "9606\t672\tBRCA1\t-\tBRCA1/BRCA2-containing complex subunit 1\n",
        encoding="utf-8",
    )

    output = tmp_path / "gene_id_map.tsv"
    build_gene_map(gene_info, output_path=output)

    gene_map = load_gene_map(output)
    assert gene_map["7157"] == "TP53"
    assert gene_map["TP53"] == "TP53"
    assert gene_map["P53"] == "TP53"
    assert gene_map["LFS1"] == "TP53"
    assert gene_map["672"] == "BRCA1"


def test_loader_load_all(tmp_path: Path):
    """loader.load_all reads TSVs and populates SQLite."""
    from enrichrag.knowledge_graph.loader import load_all

    processed = tmp_path / "processed"
    processed.mkdir()

    # gene_id_map
    (processed / "gene_id_map.tsv").write_text(
        "input_id\tcanonical_symbol\tsource\n"
        "7157\tTP53\tncbi_geneid\n",
        encoding="utf-8",
    )
    # edge TSV
    (processed / "test_edges.tsv").write_text(
        "source\tsource_type\ttarget\ttarget_type\trelation\tevidence\tpmid\tsource_db\tscore\tmetadata_json\n"
        "TP53\tgene\tMDM2\tgene\tinteract\ttest\tPMID:1\ttest\t0.9\t{}\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "kg.db"
    result = load_all(db_path, processed)

    assert result["gene_id_map"] == 1
    assert result["test"] == 1
