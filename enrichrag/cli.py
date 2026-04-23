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


def _collect_genes(cli_genes: list[str] | None, file: Path | None) -> list[str]:
    """Merge genes from CLI arguments and/or a file (one symbol per line)."""
    result: list[str] = []
    if cli_genes:
        result.extend(cli_genes)
    if file:
        text = file.read_text(encoding="utf-8")
        for line in text.splitlines():
            token = line.strip()
            if token and not token.startswith("#"):
                result.extend(token.split())
    if not result:
        typer.secho("No genes provided. Pass symbols as arguments or use --file.", fg=typer.colors.RED)
        raise typer.Exit(1)
    return result


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
    genes: List[str] = typer.Argument(None, help="Gene symbols to analyze"),
    file: Path = typer.Option(None, "--file", "-f", help="Read gene symbols from a file (one per line)"),
    disease: str = typer.Option("cancer", "--disease", "-d", help="Disease context"),
    output: Path = typer.Option(None, "--output", "-o", help="Output JSON path"),
    pval: float = typer.Option(0.05, "--pval", "-p", help="P-value threshold"),
    validate_first: bool = typer.Option(
        False,
        "--validate-first",
        help="Validate and normalize genes before running the pipeline. Warns on rejected genes but continues with accepted/remapped ones. Use --strict to abort on any rejection.",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="With --validate-first, abort if any genes are rejected (default: warn and continue).",
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

    gene_list = _collect_genes(genes, file)
    run_genes = gene_list
    if validate_first:
        service = GeneValidationService()
        validation = service.validate(gene_list)
        if json_output:
            _dump_json(validation)
        else:
            _render_validation_summary(validation)

        rejected = validation.get("rejected", [])
        rejected_names = [r.get("input_gene", "") for r in rejected] if rejected else []
        normalized = validation.get("normalized_genes", [])

        if rejected and strict:
            typer.secho("Validation failed: rejected genes found (--strict mode).", fg=typer.colors.RED)
            raise typer.Exit(2)
        if rejected:
            typer.secho(
                f"Warning: {len(rejected)} rejected gene(s) skipped: {', '.join(rejected_names)}",
                fg=typer.colors.YELLOW,
            )
        if not normalized:
            typer.secho("Validation produced no usable genes — all rejected.", fg=typer.colors.RED)
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
    genes: List[str] = typer.Argument(None, help="Gene symbols to validate"),
    file: Path = typer.Option(None, "--file", "-f", help="Read gene symbols from a file (one per line)"),
    json_output: bool = typer.Option(False, "--json", help="Print raw validation JSON"),
) -> None:
    """Validate genes against local mappings and report remaps/rejections."""
    from enrichrag.core.gene_validation import GeneValidationService

    gene_list = _collect_genes(genes, file)
    service = GeneValidationService()
    result = service.validate(gene_list)
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


def _load_result(result_path: Path) -> dict[str, Any]:
    """Load and return a pipeline result JSON file."""
    return json.loads(result_path.read_text(encoding="utf-8"))


@result_app.command("summary")
def result_summary(
    result_path: Path = typer.Argument(..., exists=True, readable=True, help="Path to pipeline result JSON"),
    json_output: bool = typer.Option(False, "--json", help="Print raw result JSON"),
) -> None:
    """Summarize a saved pipeline result JSON."""
    data = _load_result(result_path)
    if json_output:
        _dump_json(data)
        return
    _print_result_summary(data)


@result_app.command("papers")
def result_papers(
    result_path: Path = typer.Argument(..., exists=True, readable=True, help="Path to pipeline result JSON"),
    limit: int = typer.Option(0, "--limit", "-n", help="Max papers to show (0 = all)"),
    json_output: bool = typer.Option(False, "--json", help="Print raw sources JSON"),
) -> None:
    """List all PubMed and web sources from a result."""
    data = _load_result(result_path)
    sources = data.get("sources", {})

    if json_output:
        _dump_json(sources)
        return

    pubmed = sources.get("pubmed", [])
    web = sources.get("web", [])

    if pubmed:
        rows = pubmed[:limit] if limit else pubmed
        table = Table(title=f"PubMed Sources ({len(pubmed)} total)")
        table.add_column("#", justify="right")
        table.add_column("PMID", justify="right")
        table.add_column("Title")
        table.add_column("Journal")
        table.add_column("Date")
        for i, row in enumerate(rows, 1):
            table.add_row(
                str(i),
                str(row.get("pmid", "")),
                str(row.get("title", "")),
                str(row.get("journal", "")),
                str(row.get("pub_date", "")),
            )
        console.print(table)
    else:
        typer.echo("No PubMed sources.")

    if web:
        rows = web[:limit] if limit else web
        table = Table(title=f"Web Sources ({len(web)} total)")
        table.add_column("#", justify="right")
        table.add_column("Title")
        table.add_column("URL")
        for i, row in enumerate(rows, 1):
            table.add_row(str(i), str(row.get("title", "")), str(row.get("url", "")))
        console.print(table)
    else:
        typer.echo("No web sources.")


@result_app.command("graph-stats")
def result_graph_stats(
    result_path: Path = typer.Argument(..., exists=True, readable=True, help="Path to pipeline result JSON"),
    top: int = typer.Option(10, "--top", "-n", help="Number of top hub genes to show"),
    json_output: bool = typer.Option(False, "--json", help="Print raw stats JSON"),
) -> None:
    """Show graph statistics: node types, hub genes, relation type distribution."""
    data = _load_result(result_path)
    graph = data.get("graph", {})
    relations = data.get("gene_relations", [])
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # Node type distribution
    node_types = Counter(n.get("type", "unknown") for n in nodes)
    # Edge type distribution
    edge_types = Counter(e.get("type", "unknown") for e in edges)
    # Relation type distribution (from gene_relations)
    relation_types = Counter(r.get("relation", "unknown") for r in relations)
    # Relation group distribution
    relation_groups = Counter(r.get("relation_group", "unknown") for r in relations)
    # Hub genes: count edges per node
    degree: dict[str, int] = {}
    for e in edges:
        for endpoint in (e.get("source", ""), e.get("target", "")):
            degree[endpoint] = degree.get(endpoint, 0) + 1
    hub_genes = sorted(degree.items(), key=lambda x: -x[1])[:top]

    if json_output:
        _dump_json({
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
            "relation_types": dict(relation_types),
            "relation_groups": dict(relation_groups),
            "hub_genes": [{"node": n, "degree": d} for n, d in hub_genes],
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "total_relations": len(relations),
        })
        return

    table = Table(title=f"Graph Overview ({len(nodes)} nodes, {len(edges)} edges)")
    table.add_column("Node Type")
    table.add_column("Count", justify="right")
    for kind, count in sorted(node_types.items(), key=lambda x: -x[1]):
        table.add_row(kind, str(count))
    console.print(table)

    if edge_types:
        table = Table(title="Edge Types")
        table.add_column("Type")
        table.add_column("Count", justify="right")
        for kind, count in sorted(edge_types.items(), key=lambda x: -x[1]):
            table.add_row(kind, str(count))
        console.print(table)

    if relation_types:
        table = Table(title=f"Relation Types ({len(relations)} total)")
        table.add_column("Relation")
        table.add_column("Group")
        table.add_column("Count", justify="right")
        group_lookup: dict[str, str] = {}
        for r in relations:
            grp = r.get("relation_group")
            if grp and isinstance(grp, str):
                group_lookup[r.get("relation", "")] = grp
        for kind, count in sorted(relation_types.items(), key=lambda x: -x[1]):
            table.add_row(kind, group_lookup.get(kind, ""), str(count))
        console.print(table)

    if hub_genes:
        table = Table(title=f"Top {top} Hub Nodes (by degree)")
        table.add_column("Node")
        table.add_column("Degree", justify="right")
        for node, deg in hub_genes:
            table.add_row(node, str(deg))
        console.print(table)


@result_app.command("terms")
def result_terms(
    result_path: Path = typer.Argument(..., exists=True, readable=True, help="Path to pipeline result JSON"),
    db: str = typer.Option("all", "--db", help="Filter by database: GO, KEGG, or all"),
    limit: int = typer.Option(0, "--limit", "-n", help="Max terms to show (0 = all)"),
    json_output: bool = typer.Option(False, "--json", help="Print raw enrichment JSON"),
) -> None:
    """List enrichment terms from a result, optionally filtered by database."""
    data = _load_result(result_path)
    enrichment = data.get("enrichment_results", {})

    db_upper = db.upper()
    if db_upper == "ALL":
        dbs = list(enrichment.keys())
    elif db_upper in enrichment:
        dbs = [db_upper]
    else:
        typer.secho(f"Database '{db}' not found. Available: {', '.join(enrichment.keys())}", fg=typer.colors.RED)
        raise typer.Exit(1)

    if json_output:
        filtered = {k: enrichment[k] for k in dbs}
        _dump_json(filtered)
        return

    for db_name in dbs:
        rows = enrichment.get(db_name, [])
        display = rows[:limit] if limit else rows
        table = Table(title=f"{db_name} Terms ({len(rows)} total)")
        table.add_column("#", justify="right")
        table.add_column("Term")
        table.add_column("Adj P", justify="right")
        table.add_column("Overlap", justify="right")
        table.add_column("Genes")
        for i, row in enumerate(display, 1):
            p_adj = row.get("p_adjusted")
            p_str = f"{p_adj:.2e}" if isinstance(p_adj, (int, float)) else str(p_adj)
            raw_genes = row.get("genes", "")
            if isinstance(raw_genes, list):
                genes_str = ", ".join(raw_genes)
            elif isinstance(raw_genes, str):
                genes_str = raw_genes.replace(";", ", ")
            else:
                genes_str = ""
            table.add_row(str(i), str(row.get("term", "")), p_str, str(row.get("overlap", "")), genes_str)
        console.print(table)


@result_app.command("inspect")
def result_inspect(
    result_path: Path = typer.Argument(..., exists=True, readable=True, help="Path to pipeline result JSON"),
    gene: str = typer.Option(..., "--gene", "-g", help="Gene symbol to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Print raw inspect JSON"),
) -> None:
    """Inspect a specific gene: its enrichment terms, relations, and paper mentions."""
    data = _load_result(result_path)
    gene_upper = gene.upper()

    # Enrichment terms containing this gene
    enrichment = data.get("enrichment_results", {})
    matched_terms: list[dict[str, Any]] = []
    for db_name, terms in enrichment.items():
        for term in terms:
            raw = term.get("genes", "")
            if isinstance(raw, list):
                term_genes = [g.upper() for g in raw]
            elif isinstance(raw, str):
                term_genes = [g.strip().upper() for g in raw.split(";") if g.strip()]
            else:
                term_genes = []
            if gene_upper in term_genes:
                matched_terms.append({"db": db_name, **term})

    # Relations involving this gene
    relations = data.get("gene_relations", [])
    matched_relations = [
        r for r in relations
        if r.get("source", "").upper() == gene_upper or r.get("target", "").upper() == gene_upper
    ]

    # Papers mentioning this gene (check relations' PMIDs)
    related_pmids = {r.get("pmid") for r in matched_relations if r.get("pmid")}
    pubmed = data.get("sources", {}).get("pubmed", [])
    matched_papers = [p for p in pubmed if p.get("pmid") in related_pmids]

    if json_output:
        _dump_json({
            "gene": gene_upper,
            "enrichment_terms": matched_terms,
            "relations": matched_relations,
            "papers": matched_papers,
        })
        return

    console.print(f"\n[bold]Inspect: {gene_upper}[/bold]\n")

    if matched_terms:
        table = Table(title=f"Enrichment Terms ({len(matched_terms)})")
        table.add_column("DB")
        table.add_column("Term")
        table.add_column("Adj P", justify="right")
        table.add_column("Overlap", justify="right")
        for t in matched_terms:
            p_adj = t.get("p_adjusted")
            p_str = f"{p_adj:.2e}" if isinstance(p_adj, (int, float)) else str(p_adj)
            table.add_row(t.get("db", ""), str(t.get("term", "")), p_str, str(t.get("overlap", "")))
        console.print(table)
    else:
        typer.echo(f"No enrichment terms found for {gene_upper}.")

    if matched_relations:
        table = Table(title=f"Relations ({len(matched_relations)})")
        table.add_column("Source")
        table.add_column("Relation")
        table.add_column("Target")
        table.add_column("Source DB")
        table.add_column("PMID", justify="right")
        for r in matched_relations:
            table.add_row(
                str(r.get("source", "")),
                str(r.get("relation", "")),
                str(r.get("target", "")),
                str(r.get("source_db", "")),
                str(r.get("pmid", "")),
            )
        console.print(table)
    else:
        typer.echo(f"No relations found for {gene_upper}.")

    if matched_papers:
        table = Table(title=f"Related Papers ({len(matched_papers)})")
        table.add_column("PMID", justify="right")
        table.add_column("Title")
        table.add_column("Journal")
        for p in matched_papers:
            table.add_row(str(p.get("pmid", "")), str(p.get("title", "")), str(p.get("journal", "")))
        console.print(table)
    else:
        typer.echo(f"No papers directly linked to {gene_upper} via relations.")


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
