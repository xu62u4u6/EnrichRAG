import gseapy as gp
gene_sets = {
    "GO": "GO_Biological_Process_2021",
    "KEGG": "KEGG_2021_Human"
}

def enrich_genes(genes, gene_set, organism="human"):
    res = gp.enrichr(
        gene_list=genes,
        organism=organism,
        cutoff=1.0,
        outdir=None,
        gene_sets=gene_set
    )
    return res
gene_set = ["TP53", "KRAS", "EGFR", "TP63"]
target_columns = ["Term", "Overlap", "P-value", "Adjusted P-value", "Genes"]
res = enrich_genes(gene_set, gene_sets["GO"])
res.res2d