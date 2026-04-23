"""Typer CLI for EnrichRAG."""

import json
from collections import Counter
from enum import Enum
from pathlib import Path
from typing import Any, List

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="enrichrag",
    help="Literature-augmented gene set enrichment framework.",
)
kg_app = typer.Typer(name="kg", help="Manage the local biomedical knowledge graph.")
genes_app = typer.Typer(name="genes", help="Validate genes and inspect local profiles.")
result_app = typer.Typer(name="result", help="Inspect saved pipeline results.")
app.add_typer(kg_app)
app.add_typer(genes_app)
app.add_typer(result_app)

console = Console()


class KGSource(str, Enum):
    ncbi = "ncbi"
    string = "string"
    kegg = "kegg"
    pubtator = "pubtator"
    reactome = "reactome"
    all = "all"


def _dump_json(data: Any) -> None:
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


def _render_validation_summary(result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    typer.echo(
        "Validation summary: "
        f"{summary.get('accepted', 0)} accepted, "
        f"{summary.get('remapped', 0)} remapped, "
        f"{summary.get('rejected', 0)} rejected"
    )
    normalized = result.get("normalized_genes", [])
    if normalized:
        typer.echo("Normalized genes: " + ", ".join(normalized))

    rows = result.get("rows", [])
    if not rows:
        return

    table = Table(title="Gene Validation")
    table.add_column("Input")
    table.add_column("Normalized")
    table.add_column("Status")
    table.add_column("Source")
    table.add_column("Gene ID")
    table.add_column("Official Name")
    for row in rows:
        table.add_row(
            str(row.get("input_gene", "")),
            str(row.get("normalized_gene", "")),
            str(row.get("status", "")),
            str(row.get("source", "")),
            str(row.get("gene_id", "")),
            str(row.get("official_name", "")),
        )
    console.print(table)


def _print_profile(profile: dict[str, Any]) -> None:
    table = Table(title=f"Gene Profile: {profile.get('canonical_symbol', '')}")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    fields = [
        ("Gene ID", "gene_id"),
        ("Official Symbol", "official_symbol"),
        ("Official Name", "official_full_name"),
        ("Description", "description"),
        ("Type", "type_of_gene"),
        ("Chromosome", "chromosome"),
        ("Map Location", "map_location"),
        ("Synonyms", "synonyms"),
        ("DBXrefs", "dbxrefs"),
        ("Modification Date", "modification_date"),
    ]
    for label, key in fields:
        value = str(profile.get(key, "") or "")
        if value:
            table.add_row(label, value)
    console.print(table)


def _print_result_summary(data: dict[str, Any], report_preview_chars: int = 800) -> None:
    enrichment = data.get("enrichment_results", {})
    sources = data.get("sources", {})
    graph = data.get("graph", {})
    query_plan = data.get("query_plan", {})
    relations = data.get("gene_relations", [])
    insight = data.get("llm_insight", "") or ""

    stats = Table(title="Result Summary")
    stats.add_column("Metric", style="bold")
    stats.add_column("Value", justify="right")
    stats.add_row("Disease", str(data.get("disease_context", "")))
    stats.add_row("Genes", str(len(data.get("input_genes", []))))
    stats.add_row("GO terms", str(len(enrichment.get("GO", []))))
    stats.add_row("KEGG terms", str(len(enrichment.get("KEGG", []))))
    stats.add_row("Web sources", str(len(sources.get("web", []))))
    stats.add_row("PubMed sources", str(len(sources.get("pubmed", []))))
    stats.add_row("Relations", str(len(relations)))
    stats.add_row("Graph nodes", str(len(graph.get("nodes", []))))
    stats.add_row("Graph edges", str(len(graph.get("edges", []))))
    stats.add_row("Query intents", str(len(query_plan.get("intents", []))))
    console.print(stats)

    for label in ("GO", "KEGG"):
        rows = enrichment.get(label, [])[:5]
        if not rows:
            continue
        table = Table(title=f"Top {label} Terms")
        table.add_column("Term")
        table.add_column("Adj P", justify="right")
        table.add_column("Overlap", justify="right")
        for row in rows:
            p_adjusted = row.get("p_adjusted")
            p_display = f"{p_adjusted:.2e}" if isinstance(p_adjusted, (int, float)) else str(p_adjusted)
            table.add_row(str(row.get("term", "")), p_display, str(row.get("overlap", "")))
        console.print(table)

    pubmed_rows = sources.get("pubmed", [])[:5]
    if pubmed_rows:
        table = Table(title="Top PubMed Sources")
        table.add_column("PMID", justify="right")
        table.add_column("Title")
        table.add_column("Journal")
        for row in pubmed_rows:
            table.add_row(
                str(row.get("pmid", "")),
                str(row.get("title", "")),
                str(row.get("journal", "")),
            )
        console.print(table)

    node_counter = Counter(node.get("type", "unknown") for node in graph.get("nodes", []))
    if node_counter:
        table = Table(title="Graph Node Types")
        table.add_column("Type")
        table.add_column("Count", justify="right")
        for kind, count in sorted(node_counter.items(), key=lambda item: (-item[1], item[0])):
            table.add_row(kind, str(count))
        console.print(table)

    if insight:
        preview = insight[:report_preview_chars]
        if len(insight) > report_preview_chars:
            preview += "\n\n... [truncated]"
        console.print("[bold]Insight Preview[/bold]")
        typer.echo(preview)


@app.command()
def version() -> None:
    """Show version."""
    from importlib.metadata import version as pkg_version

    try:
        ver = pkg_version("enrichrag")
    except Exception:
        ver = "unknown"
    typer.echo(f"enrichrag {ver}")


@app.command()
def analyze(
    genes: List[str] = typer.Argument(..., help="Gene symbols to analyze"),
    disease: str = typer.Option("cancer", "--disease", "-d", help="Disease context"),
    output: Path = typer.Option(None, "--output", "-o", help="Output JSON path"),
    pval: float = typer.Option(0.05, "--pval", "-p", help="P-value threshold"),
    validate_first: bool = typer.Option(
        False,
        "--validate-first",
        help="Validate and normalize genes before running the pipeline. Abort if any genes are rejected.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print validation details as JSON when used with --validate-first.",
    ),
) -> None:
    """Run the full enrichment + LLM analysis pipeline."""
    from enrichrag.core.pipeline import run_pipeline, save_result
    from enrichrag.core.gene_validation import GeneValidationService
    from enrichrag.logging import logger
    from enrichrag.settings import settings

    if output is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output = output_dir / "result.json"

    run_genes = genes
    if validate_first:
        service = GeneValidationService()
        validation = service.validate(genes)
        if json_output:
            _dump_json(validation)
        else:
            _render_validation_summary(validation)

        rejected = validation.get("rejected", [])
        if rejected:
            typer.secho("Validation failed: rejected genes found. Fix input before analysis.", fg=typer.colors.RED)
            raise typer.Exit(2)

        normalized = validation.get("normalized_genes", [])
        if not normalized:
            typer.secho("Validation produced no normalized genes.", fg=typer.colors.RED)
            raise typer.Exit(2)
        run_genes = normalized

    if not settings.openai_api_key:
        logger.error("OPENAI_API_KEY not found — create a .env file in the project root")
        raise typer.Exit(1)

    def on_progress(step: str, message: str, **_: object) -> None:
        typer.echo(message)

    result = run_pipeline(run_genes, disease, pval, on_progress)
    if result.get("llm_insight"):
        typer.echo(result["llm_insight"])
    save_result(result, output)


@genes_app.command("validate")
def genes_validate(
    genes: List[str] = typer.Argument(..., help="Gene symbols to validate"),
    json_output: bool = typer.Option(False, "--json", help="Print raw validation JSON"),
) -> None:
    """Validate genes against local mappings and report remaps/rejections."""
    from enrichrag.core.gene_validation import GeneValidationService

    service = GeneValidationService()
    result = service.validate(genes)
    if json_output:
        _dump_json(result)
        return
    _render_validation_summary(result)
    if result.get("summary", {}).get("rejected", 0):
        raise typer.Exit(2)


@genes_app.command("profile")
def gene_profile(
    symbol: str = typer.Argument(..., help="Gene symbol to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Print raw profile JSON"),
) -> None:
    """Show cached local gene profile information."""
    from enrichrag.core.gene_validation import GeneValidationService

    service = GeneValidationService()
    profile = service.get_profile(symbol)
    if profile is None:
        typer.secho(f"Gene profile not found: {symbol}", fg=typer.colors.RED)
        raise typer.Exit(1)
    if json_output:
        _dump_json(profile)
        return
    _print_profile(profile)


@result_app.command("summary")
def result_summary(
    result_path: Path = typer.Argument(..., exists=True, readable=True, help="Path to pipeline result JSON"),
    json_output: bool = typer.Option(False, "--json", help="Print raw result JSON"),
) -> None:
    """Summarize a saved pipeline result JSON."""
    data = json.loads(result_path.read_text(encoding="utf-8"))
    if json_output:
        _dump_json(data)
        return
    _print_result_summary(data)


@app.command()
def serve(
    host: str = typer.Option(None, "--host", "-h", help="Bind host"),
    port: int = typer.Option(None, "--port", "-p", help="Bind port"),
) -> None:
    """Start the web server."""
    import uvicorn

    from enrichrag.settings import settings

    uvicorn.run(
        "enrichrag.api.app:app",
        host=host or settings.server_host,
        port=port or settings.server_port,
        reload=False,
    )


@kg_app.command("build")
def kg_build(
    source: KGSource = typer.Option(KGSource.all, "--source", help="Dataset to import"),
    force: bool = typer.Option(False, "--force", help="Re-download source files"),
    detailed_string: bool = typer.Option(
        False,
        "--detailed-string",
        help="Use STRING detailed download with per-channel scores",
    ),
) -> None:
    """Download, normalize, and load knowledge graph datasets."""
    import logging
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from rich.console import Console

    from enrichrag.knowledge_graph import downloaders
    from enrichrag.knowledge_graph.rich_progress import RichProgressReporter
    from enrichrag.settings import settings

    logging.basicConfig(level=logging.WARNING)
    console = Console()
    data_dir = Path(settings.kg_data_dir)
    processed_dir = data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    sources = (
        [s for s in KGSource if s != KGSource.all]
        if source == KGSource.all
        else [source]
    )

    with RichProgressReporter(console) as progress:
        # ── Phase 1: Parallel downloads ──────────────────────────────
        ncbi_path = None
        string_paths: dict[str, Path] | None = None
        kgml_paths: list[Path] | None = None
        pubtator_path = None
        reactome_path = None

        download_futures = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            if KGSource.ncbi in sources:
                download_futures["ncbi"] = pool.submit(
                    downloaders.download_ncbi, data_dir, force, progress,
                )
            if KGSource.string in sources:
                download_futures["string"] = pool.submit(
                    downloaders.download_string, data_dir, force, detailed_string, progress,
                )
            if KGSource.kegg in sources:
                download_futures["kegg"] = pool.submit(
                    downloaders.download_kegg, data_dir, force, 0.3, progress,
                )
            if KGSource.pubtator in sources:
                download_futures["pubtator"] = pool.submit(
                    downloaders.download_pubtator, data_dir, force, progress,
                )
            if KGSource.reactome in sources:
                download_futures["reactome"] = pool.submit(
                    downloaders.download_reactome, data_dir, force, progress,
                )

            for future in as_completed(download_futures.values()):
                future.result()  # raise exceptions

        ncbi_path = download_futures["ncbi"].result() if "ncbi" in download_futures else None
        string_paths = download_futures["string"].result() if "string" in download_futures else None
        kgml_paths = download_futures["kegg"].result() if "kegg" in download_futures else None
        pubtator_path = download_futures["pubtator"].result() if "pubtator" in download_futures else None
        reactome_path = download_futures["reactome"].result() if "reactome" in download_futures else None

        # ── Phase 2: Build gene map (needs NCBI + STRING aliases) ────
        gene_map_path = processed_dir / "gene_id_map.tsv"
        if ncbi_path or not gene_map_path.exists():
            if not ncbi_path:
                ncbi_path = downloaders.download_ncbi(data_dir, force=force, progress=progress)

            from enrichrag.knowledge_graph.build_gene_map import build_gene_map

            string_aliases = string_paths["aliases"] if string_paths else None
            build_gene_map(ncbi_path, string_aliases, gene_map_path, progress=progress)

        # ── Phase 3: Parallel normalization ──────────────────────────
        normalize_futures = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            if string_paths:
                from enrichrag.knowledge_graph.string_normalizer import normalize_string
                normalize_futures["string"] = pool.submit(
                    normalize_string,
                    string_paths["links"], gene_map_path,
                    processed_dir / "string_edges.tsv",
                    700, progress,
                )

            if kgml_paths:
                from enrichrag.knowledge_graph.kegg_normalizer import normalize_kegg
                normalize_futures["kegg"] = pool.submit(
                    normalize_kegg,
                    kgml_paths, gene_map_path,
                    processed_dir / "kegg_edges.tsv",
                )

            if pubtator_path:
                from enrichrag.knowledge_graph.pubtator_normalizer import normalize_pubtator
                normalize_futures["pubtator"] = pool.submit(
                    normalize_pubtator,
                    pubtator_path, gene_map_path,
                    processed_dir / "pubtator_edges.tsv",
                    progress,
                )

            if reactome_path:
                from enrichrag.knowledge_graph.reactome_normalizer import normalize_reactome
                normalize_futures["reactome"] = pool.submit(
                    normalize_reactome,
                    reactome_path, gene_map_path,
                    processed_dir / "reactome_edges.tsv",
                )

            for future in as_completed(normalize_futures.values()):
                future.result()

        # ── Phase 4: Load into SQLite ────────────────────────────────
        from enrichrag.knowledge_graph.loader import load_all

        result = load_all(settings.kg_db_path, processed_dir, progress=progress)

    # Summary
    console.print()
    console.print("[bold green]Knowledge graph build complete.[/bold green]")
    for name, count in result.items():
        console.print(f"  {name}: {count:,}")


@kg_app.command("status")
def kg_status() -> None:
    """Show knowledge graph database status."""
    from rich.console import Console
    from rich.table import Table

    from enrichrag.knowledge_graph.base import KnowledgeGraphDB
    from enrichrag.settings import settings

    console = Console()
    db_path = Path(settings.kg_db_path)
    if not db_path.exists():
        console.print("[yellow]Knowledge graph database not found.[/yellow]")
        console.print(f"  Expected at: {db_path}")
        console.print("  Run [bold]enrichrag kg build[/bold] to create it.")
        return

    db = KnowledgeGraphDB(db_path)
    with db.connect() as conn:
        gene_map_count = conn.execute("SELECT COUNT(*) AS c FROM gene_id_map").fetchone()["c"]
        edge_count = conn.execute("SELECT COUNT(*) AS c FROM edges").fetchone()["c"]
        source_counts = conn.execute(
            "SELECT source_db, COUNT(*) AS c FROM edges GROUP BY source_db ORDER BY c DESC"
        ).fetchall()

    table = Table(title="Knowledge Graph Status")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Database", str(db_path))
    table.add_row("Size", f"{db_path.stat().st_size / 1024 / 1024:.1f} MB")
    table.add_row("Gene ID mappings", f"{gene_map_count:,}")
    table.add_row("Total edges", f"{edge_count:,}")

    if source_counts:
        table.add_section()
        for row in source_counts:
            table.add_row(f"  {row['source_db']}", f"{row['c']:,}")

    console.print(table)

    data_dir = Path(settings.kg_data_dir)
    processed = data_dir / "processed"
    if processed.exists():
        tsvs = list(processed.glob("*.tsv"))
        if tsvs:
            tsv_table = Table(title="Processed TSV Files")
            tsv_table.add_column("File")
            tsv_table.add_column("Size", justify="right")
            for tsv in sorted(tsvs):
                tsv_table.add_row(tsv.name, f"{tsv.stat().st_size / 1024 / 1024:.1f} MB")
            console.print(tsv_table)


if __name__ == "__main__":
    app()
