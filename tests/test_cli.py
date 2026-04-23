import gzip
import json
from pathlib import Path

from typer.testing import CliRunner

from enrichrag.cli import app
from enrichrag.settings import settings

runner = CliRunner()


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


def _seed_gene_validation_db(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "kg.db"
    gene_info_path = tmp_path / "Homo_sapiens.gene_info.gz"
    _write_gene_info(gene_info_path)

    monkeypatch.setattr(settings, "kg_db_path", str(db_path))
    monkeypatch.setattr(settings, "kg_data_dir", str(tmp_path))

    from enrichrag.core.gene_validation import GeneValidationService

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


def test_cli_genes_validate_reports_remaps_and_rejections(tmp_path: Path, monkeypatch):
    _seed_gene_validation_db(tmp_path, monkeypatch)

    result = runner.invoke(app, ["genes", "validate", "TP53", "P53", "NOPE"])

    assert result.exit_code == 2
    assert "Validation summary: 1 accepted, 1 remapped, 1 rejected" in result.stdout
    assert "Normalized genes: TP53" in result.stdout
    assert "P53" in result.stdout
    assert "NOPE" in result.stdout


def test_cli_gene_profile_shows_profile(tmp_path: Path, monkeypatch):
    _seed_gene_validation_db(tmp_path, monkeypatch)

    result = runner.invoke(app, ["genes", "profile", "TP53"])

    assert result.exit_code == 0
    assert "Gene Profile: TP53" in result.stdout
    assert "tumor protein p53" in result.stdout
    assert "7157" in result.stdout


def test_cli_analyze_validate_first_warns_on_rejected_gene(tmp_path: Path, monkeypatch):
    _seed_gene_validation_db(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "openai_api_key", "fake-key")

    output_path = tmp_path / "result.json"
    # Mock run_pipeline so we don't need real API keys
    import enrichrag.cli as cli_mod

    def fake_pipeline(genes, disease, pval, on_progress):
        return {"input_genes": genes, "llm_insight": ""}

    monkeypatch.setattr("enrichrag.core.pipeline.run_pipeline", fake_pipeline)
    monkeypatch.setattr("enrichrag.core.pipeline.save_result", lambda r, p: None)

    result = runner.invoke(
        app,
        [
            "analyze",
            "TP53",
            "NOPE",
            "--validate-first",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "Warning" in result.stdout
    assert "rejected" in result.stdout


def test_cli_analyze_validate_first_strict_blocks_rejected_gene(tmp_path: Path, monkeypatch):
    _seed_gene_validation_db(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "openai_api_key", "")

    output_path = tmp_path / "result.json"
    result = runner.invoke(
        app,
        [
            "analyze",
            "TP53",
            "NOPE",
            "--validate-first",
            "--strict",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 2
    assert "Validation failed" in result.stdout
    assert not output_path.exists()


def test_cli_genes_validate_from_file(tmp_path: Path, monkeypatch):
    _seed_gene_validation_db(tmp_path, monkeypatch)

    gene_file = tmp_path / "genes.txt"
    gene_file.write_text("TP53\nP53\n# comment\nNOPE\n", encoding="utf-8")

    result = runner.invoke(app, ["genes", "validate", "--file", str(gene_file)])

    assert result.exit_code == 2
    assert "1 accepted, 1 remapped, 1 rejected" in result.stdout


def test_cli_result_summary_prints_key_stats(tmp_path: Path):
    result_path = tmp_path / "result.json"
    payload = {
        "input_genes": ["BRCA1", "BRCA2"],
        "disease_context": "breast cancer",
        "enrichment_results": {
            "GO": [
                {"term": "DNA repair", "p_adjusted": 1.2e-5, "overlap": "2/100"},
            ],
            "KEGG": [
                {"term": "Homologous recombination", "p_adjusted": 2.5e-4, "overlap": "2/40"},
            ],
        },
        "sources": {
            "web": [{"title": "Example web"}],
            "pubmed": [{"pmid": "123", "title": "DNA repair study", "journal": "Nature"}],
        },
        "gene_relations": [{"source": "BRCA1", "target": "BRCA2", "relation": "interact"}],
        "graph": {
            "nodes": [
                {"id": "gene:BRCA1", "type": "gene"},
                {"id": "gene:BRCA2", "type": "gene"},
                {"id": "go:DNA repair", "type": "go"},
            ],
            "edges": [{"source": "gene:BRCA1", "target": "gene:BRCA2", "type": "relation"}],
        },
        "query_plan": {"intents": [{"category": "pathway_mechanism"}]},
        "llm_insight": "This gene set is dominated by DNA repair biology.",
    }
    result_path.write_text(json.dumps(payload), encoding="utf-8")

    result = runner.invoke(app, ["result", "summary", str(result_path)])

    assert result.exit_code == 0
    assert "Result Summary" in result.stdout
    assert "breast cancer" in result.stdout
    assert "Top GO Terms" in result.stdout
    assert "Top PubMed Sources" in result.stdout
    assert "Insight Preview" in result.stdout


# -- Shared fixture for result subcommand tests --

_SAMPLE_RESULT = {
    "input_genes": ["BRCA1", "BRCA2"],
    "disease_context": "breast cancer",
    "enrichment_results": {
        "GO": [
            {"term": "DNA repair", "p_adjusted": 1.2e-5, "overlap": "2/100", "genes": "BRCA1;BRCA2"},
        ],
        "KEGG": [
            {"term": "Homologous recombination", "p_adjusted": 2.5e-4, "overlap": "2/40", "genes": "BRCA1;BRCA2"},
        ],
    },
    "sources": {
        "web": [{"title": "Example web", "url": "https://example.com"}],
        "pubmed": [{"pmid": "123", "title": "DNA repair study", "journal": "Nature", "pub_date": "2024"}],
    },
    "gene_relations": [
        {"source": "BRCA1", "target": "BRCA2", "relation": "interact", "source_db": "kegg", "pmid": "123", "relation_group": "Interaction"},
    ],
    "graph": {
        "nodes": [
            {"id": "gene:BRCA1", "type": "gene"},
            {"id": "gene:BRCA2", "type": "gene"},
            {"id": "go:DNA repair", "type": "go"},
        ],
        "edges": [
            {"source": "gene:BRCA1", "target": "gene:BRCA2", "type": "relation"},
            {"source": "gene:BRCA1", "target": "go:DNA repair", "type": "enrichment"},
        ],
    },
    "query_plan": {"intents": [{"category": "pathway_mechanism"}]},
    "llm_insight": "This gene set is dominated by DNA repair biology.",
}


def _write_sample_result(path: Path) -> None:
    path.write_text(json.dumps(_SAMPLE_RESULT), encoding="utf-8")


def test_cli_result_papers(tmp_path: Path):
    result_path = tmp_path / "result.json"
    _write_sample_result(result_path)

    result = runner.invoke(app, ["result", "papers", str(result_path)])

    assert result.exit_code == 0
    assert "PubMed Sources" in result.stdout
    assert "123" in result.stdout
    assert "Web Sources" in result.stdout
    assert "Example web" in result.stdout


def test_cli_result_graph_stats(tmp_path: Path):
    result_path = tmp_path / "result.json"
    _write_sample_result(result_path)

    result = runner.invoke(app, ["result", "graph-stats", str(result_path)])

    assert result.exit_code == 0
    assert "Graph Overview" in result.stdout
    assert "gene" in result.stdout
    assert "Hub" in result.stdout


def test_cli_result_terms_filter_by_db(tmp_path: Path):
    result_path = tmp_path / "result.json"
    _write_sample_result(result_path)

    result = runner.invoke(app, ["result", "terms", str(result_path), "--db", "GO"])

    assert result.exit_code == 0
    assert "GO Terms" in result.stdout
    assert "DNA repair" in result.stdout


def test_cli_result_inspect_gene(tmp_path: Path):
    result_path = tmp_path / "result.json"
    _write_sample_result(result_path)

    result = runner.invoke(app, ["result", "inspect", str(result_path), "--gene", "BRCA1"])

    assert result.exit_code == 0
    assert "Inspect: BRCA1" in result.stdout
    assert "Enrichment Terms" in result.stdout
    assert "Relations" in result.stdout
