from enrichrag.enrichment.go import run_go_ora
from enrichrag.enrichment.kegg import run_kegg_ora
from enrichrag.core.integrate import integrate_results

def enrich(
    gene_set: list[str],
    databases: list[str] = ["GO", "KEGG"]
) -> dict:

    if not isinstance(gene_set, list):
        raise TypeError("gene_set must be a list of gene symbols")

    raw_results = {}

    if "GO" in databases:
        raw_results["GO"] = run_go_ora(gene_set)
    else:
        raw_results["GO"] = []

    if "KEGG" in databases:
        raw_results["KEGG"] = run_kegg_ora(gene_set)
    else:
        raw_results["KEGG"] = []

    results, integrated = integrate_results(raw_results, gene_set)

    return {
        "input_genes": gene_set,
        "results": results,
        "integrated": integrated
    }
