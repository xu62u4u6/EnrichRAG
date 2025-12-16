def integrate_results(
    raw_results: dict[str, list[dict]],
    input_genes: list[str]
) -> tuple[dict, list]:

    input_set = set(input_genes)

    for source, terms in raw_results.items():
        for t in terms:
            t["coverage"] = len(set(t["genes"]) & input_set)
            t["source"] = source

    # v0.1：不做 cross-db clustering
    integrated = []

    return raw_results, integrated
