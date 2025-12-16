import gseapy as gp

GO_LIBRARY = "GO_Biological_Process_2021"

def run_go_ora(gene_set: list[str]) -> list[dict]:
    if not gene_set:
        return []

    enr = gp.enrichr(
        gene_list=list(set(gene_set)),
        gene_sets=GO_LIBRARY,
        organism="Human",
        outdir=None,
        cutoff=1.0
    )

    if enr.results is None:
        return []

    results = []
    for _, row in enr.results.iterrows():
        genes = row["Genes"].split(";") if isinstance(row["Genes"], str) else []
        results.append({
            "term_id": row["Term"],
            "term_name": row["Term"],
            "p_value": float(row["P-value"]),
            "adj_p_value": float(row["Adjusted P-value"]),
            "genes": genes,
        })

    return results
