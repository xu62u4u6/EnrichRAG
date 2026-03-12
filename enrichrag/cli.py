"""Typer CLI for EnrichRAG."""

from enum import Enum
from pathlib import Path
from typing import List

import typer

app = typer.Typer(
    name="enrichrag",
    help="Literature-augmented gene set enrichment framework.",
)
kg_app = typer.Typer(name="kg", help="Manage the local biomedical knowledge graph.")
app.add_typer(kg_app)


class KGSource(str, Enum):
    ncbi = "ncbi"
    string = "string"
    kegg = "kegg"
    pubtator = "pubtator"
    reactome = "reactome"
    all = "all"


@app.command()
def version() -> None:
    """Show version."""
    typer.echo("enrichrag 0.1.0")


@app.command()
def analyze(
    genes: List[str] = typer.Argument(..., help="Gene symbols to analyze"),
    disease: str = typer.Option("cancer", "--disease", "-d", help="Disease context"),
    output: Path = typer.Option(None, "--output", "-o", help="Output JSON path"),
    pval: float = typer.Option(0.05, "--pval", "-p", help="P-value threshold"),
) -> None:
    """Run the full enrichment + LLM analysis pipeline."""
    from enrichrag.core.pipeline import run_pipeline, save_result
    from enrichrag.logging import logger
    from enrichrag.settings import settings

    if not settings.openai_api_key:
        logger.error("OPENAI_API_KEY not found — create a .env file in the project root")
        raise typer.Exit(1)

    if output is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output = output_dir / "result.json"

    def on_progress(step: str, message: str, **_: object) -> None:
        typer.echo(message)

    result = run_pipeline(genes, disease, pval, on_progress)
    if result.get("llm_insight"):
        typer.echo(result["llm_insight"])
    save_result(result, output)


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
