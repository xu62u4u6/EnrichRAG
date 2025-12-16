from enrichrag.core.enrich import enrich

genes = ["TP53", "KRAS", "EGFR", "BRAF"]

res = enrich(genes)

print(res.keys())
print(len(res["results"]["GO"]), "GO terms")
print(len(res["results"]["KEGG"]), "KEGG terms")
print(res["results"])
