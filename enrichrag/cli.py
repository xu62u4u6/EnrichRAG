"""Typer CLI for EnrichRAG."""

import json
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
) -> None:
    """Run the full enrichment + LLM analysis pipeline."""
    if output is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output = output_dir / "result.json"

    import pandas as pd
    from langchain_core.output_parsers import StrOutputParser
    from langchain_openai import ChatOpenAI

    from enrichrag.core.enricher import GeneEnricher
    from enrichrag.logging import logger
    from enrichrag.prompts.generator import PromptGenerator
    from enrichrag.settings import settings

    if settings.openai_api_key:
        logger.info("OpenAI API key loaded")
    else:
        logger.error("OPENAI_API_KEY not found — create a .env file in the project root")
        raise typer.Exit(1)

    logger.info(f"Analyzing genes: {genes}")

    # 1. Enrichment analysis
    enricher = GeneEnricher(gene_list=genes)
    enricher.run_enrichment()
    enricher.filter(pval_threshold=0.05)

    # 2. LLM chain
    base_dir = Path(__file__).resolve().parent
    template_path = base_dir / "prompts" / "templates" / "enrichment_analysis.yaml"

    insight = ""
    try:
        generator = PromptGenerator(template_path=str(template_path))
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=0.2,
            api_key=settings.openai_api_key,
        )
        parser = StrOutputParser()
        chain = generator.prompt_template | llm | parser

        go_table = enricher.filtered_results.get("GO", pd.DataFrame()).to_markdown(index=False)
        kegg_table = enricher.filtered_results.get("KEGG", pd.DataFrame()).to_markdown(index=False)

        inputs = {
            "context": f"Disease context: {disease}",
            "genes": ", ".join(genes),
            "go_table": go_table if go_table else "No significant enrichment results",
            "kegg_table": kegg_table if kegg_table else "No significant enrichment results",
        }

        logger.info("Generating analysis report...")
        insight = chain.invoke(inputs)

        logger.info("Report generated successfully")
        typer.echo(insight)

    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        insight = f"Error generating insight: {e}"

    # 3. Output JSON
    output_data = {
        "input_genes": genes,
        "disease_context": disease,
        "enrichment_results": {
            label: df.to_dict(orient="records")
            for label, df in enricher.filtered_results.items()
        },
        "llm_insight": insight,
    }

    with open(output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Results saved to: {output}")


if __name__ == "__main__":
    app()
