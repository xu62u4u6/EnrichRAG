"""Typer CLI for EnrichRAG."""

from pathlib import Path
from typing import List

import typer

app = typer.Typer(
    name="enrichrag",
    help="Literature-augmented gene set enrichment framework.",
)


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

    def on_progress(step: str, message: str) -> None:
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


if __name__ == "__main__":
    app()
