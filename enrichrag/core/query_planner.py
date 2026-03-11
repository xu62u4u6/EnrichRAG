"""Query planner: transforms enrichment results into structured search intents."""

import re
from collections import Counter, defaultdict
from typing import Dict, List, Literal, Optional

import pandas as pd
from pydantic import BaseModel

from enrichrag.logging import logger


# ── Data Models ──────────────────────────────────────────────────────────────

class SearchIntent(BaseModel):
    category: Literal["pathway_mechanism", "gene_interaction", "gene_disease", "therapeutic"]
    description: str
    tavily_query: str
    pubmed_query: str
    priority: int  # 1=high, 2=medium, 3=low
    source_terms: List[str]


class QueryPlan(BaseModel):
    intents: List[SearchIntent]
    top_genes: List[str]
    gene_clusters: Dict[str, List[str]]
    summary: str


# ── Term classification keywords ─────────────────────────────────────────────

_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "DNA damage response": [
        "repair", "damage", "checkpoint", "replication", "recombination",
        "mismatch", "nucleotide excision", "base excision", "double-strand",
    ],
    "cell death signaling": [
        "apoptosis", "death", "caspase", "autophagy", "necroptosis", "ferroptosis",
    ],
    "immune response": [
        "immune", "inflammatory", "cytokine", "interferon", "interleukin",
        "chemokine", "toll-like", "antigen", "t cell", "b cell", "nk cell",
    ],
    "signaling pathway": [
        "signal", "mapk", "pi3k", "wnt", "notch", "mtor", "ras", "jak",
        "stat", "hedgehog", "tgf", "nf-kb", "erk",
    ],
    "cell cycle regulation": [
        "cell cycle", "mitosis", "mitotic", "g1", "g2", "s phase", "m phase",
        "cyclin", "cdk", "spindle",
    ],
}

# ── Disease → MeSH mapping ───────────────────────────────────────────────────

_DISEASE_MESH: Dict[str, str] = {
    "cancer": "Neoplasms",
    "tumor": "Neoplasms",
    "tumour": "Neoplasms",
    "carcinoma": "Carcinoma",
    "leukemia": "Leukemia",
    "lymphoma": "Lymphoma",
    "melanoma": "Melanoma",
    "breast cancer": "Breast Neoplasms",
    "lung cancer": "Lung Neoplasms",
    "colon cancer": "Colonic Neoplasms",
    "colorectal cancer": "Colorectal Neoplasms",
    "prostate cancer": "Prostatic Neoplasms",
    "ovarian cancer": "Ovarian Neoplasms",
    "pancreatic cancer": "Pancreatic Neoplasms",
    "liver cancer": "Liver Neoplasms",
    "glioblastoma": "Glioblastoma",
    "diabetes": "Diabetes Mellitus",
    "alzheimer": "Alzheimer Disease",
    "parkinson": "Parkinson Disease",
    "asthma": "Asthma",
    "hypertension": "Hypertension",
}

# Therapeutic-related keywords in enrichment terms
_THERAPEUTIC_KEYWORDS = [
    "drug", "therapy", "therapeutic", "pharmacolog", "resistance",
    "sensitivity", "treatment", "inhibitor", "target",
]


def _clean_term(term: str) -> str:
    """Remove GO:/KEGG: prefixes and parenthesized IDs."""
    term = re.sub(r"\(GO:\d+\)", "", term)
    term = re.sub(r"\(hsa\d+\)", "", term)
    term = re.sub(r"^(GO|KEGG|REACTOME)[_:]?\s*", "", term, flags=re.IGNORECASE)
    return term.strip()


def _classify_term(term: str) -> str:
    """Classify an enrichment term into a category."""
    lower = term.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return _clean_term(term)


def _has_therapeutic_signal(terms: List[str]) -> bool:
    joined = " ".join(t.lower() for t in terms)
    return any(kw in joined for kw in _THERAPEUTIC_KEYWORDS)


# ── QueryPlanner ─────────────────────────────────────────────────────────────

class QueryPlanner:
    """Generates structured search intents from enrichment results."""

    MAX_TAVILY = 5
    MAX_PUBMED = 3

    def plan(
        self,
        enrichment_results: Dict[str, pd.DataFrame],
        genes: List[str],
        disease: str,
    ) -> QueryPlan:
        """Rule-based query planning from enrichment results.

        Returns a QueryPlan with up to 5 SearchIntents.
        """
        # Step 1: Gene clustering — group genes by shared enrichment terms
        gene_counter: Counter = Counter()
        category_genes: Dict[str, Counter] = defaultdict(Counter)
        all_terms: List[str] = []

        for df in enrichment_results.values():
            if df.empty or "genes" not in df.columns or "term" not in df.columns:
                continue
            for _, row in df.iterrows():
                term = str(row["term"])
                all_terms.append(term)
                category = _classify_term(term)
                genes_str = str(row.get("genes", ""))
                for g in genes_str.replace(",", ";").split(";"):
                    g = g.strip().upper()
                    if g:
                        gene_counter[g] += 1
                        category_genes[category][g] += 1

        top_genes = [g for g, _ in gene_counter.most_common(5)] or genes[:5]

        # Step 2: Build gene_clusters (category → top genes in that category)
        gene_clusters: Dict[str, List[str]] = {}
        for cat, counter in category_genes.items():
            gene_clusters[cat] = [g for g, _ in counter.most_common(5)]

        # Step 3: Generate intents
        intents: List[SearchIntent] = []

        # 3a. pathway_mechanism — one per top category (up to 2)
        sorted_categories = sorted(
            category_genes.items(),
            key=lambda x: sum(x[1].values()),
            reverse=True,
        )
        for cat, counter in sorted_categories[:2]:
            cat_top_genes = [g for g, _ in counter.most_common(2)]
            genes_or = " OR ".join(f'"{g}"[Title/Abstract]' for g in cat_top_genes)
            clean_cat = _clean_term(cat)

            intents.append(SearchIntent(
                category="pathway_mechanism",
                description=f"{clean_cat} mechanism in {disease} ({', '.join(cat_top_genes)})",
                tavily_query=f"{clean_cat} molecular mechanism in {disease}",
                pubmed_query=(
                    f'"{clean_cat}"[Title/Abstract] AND ({genes_or})'
                    f' AND "{disease}"[Title/Abstract]'
                ),
                priority=1,
                source_terms=[t for t in all_terms if _classify_term(t) == cat][:3],
            ))

        # 3b. gene_interaction — largest cluster, top 3 genes
        if sorted_categories:
            largest_cat, largest_counter = sorted_categories[0]
            interaction_genes = [g for g, _ in largest_counter.most_common(3)]
            if len(interaction_genes) >= 2:
                genes_and = " AND ".join(
                    f'"{g}"[Title/Abstract]' for g in interaction_genes
                )
                intents.append(SearchIntent(
                    category="gene_interaction",
                    description=f"Interaction of {', '.join(interaction_genes)} in {disease}",
                    tavily_query=f"{' '.join(interaction_genes)} interaction {disease}",
                    pubmed_query=genes_and,
                    priority=1,
                    source_terms=[largest_cat],
                ))

        # 3c. gene_disease — most frequent gene + disease
        if top_genes:
            top_gene = top_genes[0]
            mesh = _DISEASE_MESH.get(disease.lower())
            if mesh:
                pm_query = f'"{top_gene}"[Title/Abstract] AND "{mesh}"[MeSH]'
            else:
                pm_query = (
                    f'"{top_gene}"[Title/Abstract] AND "{disease}"[Title/Abstract]'
                )
            intents.append(SearchIntent(
                category="gene_disease",
                description=f"{top_gene} role in {disease}",
                tavily_query=f"{top_gene} {disease} mechanism pathogenesis",
                pubmed_query=pm_query,
                priority=2,
                source_terms=[],
            ))

        # 3d. therapeutic — only if enrichment has therapeutic signal
        if _has_therapeutic_signal(all_terms) and sorted_categories:
            top_pathway = _clean_term(sorted_categories[0][0])
            intents.append(SearchIntent(
                category="therapeutic",
                description=f"Therapeutic targeting of {top_pathway} in {disease}",
                tavily_query=f"{top_pathway} therapeutic target drug {disease}",
                pubmed_query=(
                    f'"{top_pathway}"[Title/Abstract] AND "therapeutics"[MeSH]'
                    f' AND "{disease}"[Title/Abstract]'
                ),
                priority=3,
                source_terms=[],
            ))

        # Step 4: Cap & sort
        intents.sort(key=lambda x: x.priority)
        intents = intents[:self.MAX_TAVILY]

        summary = (
            f"Generated {len(intents)} search intents for {disease} "
            f"covering {len(gene_clusters)} pathway categories "
            f"and {len(top_genes)} key genes."
        )

        plan = QueryPlan(
            intents=intents,
            top_genes=top_genes,
            gene_clusters=gene_clusters,
            summary=summary,
        )

        logger.info(f"QueryPlanner: {summary}")
        for i, intent in enumerate(intents):
            logger.debug(
                f"  Intent {i+1} [{intent.category}, p{intent.priority}]: "
                f"tavily='{intent.tavily_query[:60]}' | "
                f"pubmed='{intent.pubmed_query[:60]}'"
            )

        return plan

    def refine_with_llm(
        self,
        plan: QueryPlan,
        enrichment_terms: List[str],
        disease: str,
        *,
        api_key: str,
        model: str = "gpt-4o",
    ) -> QueryPlan:
        """Optional LLM refinement of the rule-based plan.

        Uses a single LLM call with structured output to improve query quality.
        """
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=model,
            temperature=0,
            api_key=api_key,
        ).with_structured_output(QueryPlan)

        prompt = (
            "You are a biomedical search strategist. Refine the following search plan "
            "to maximize retrieval of relevant literature.\n\n"
            f"Disease context: {disease}\n"
            f"Enrichment terms: {', '.join(enrichment_terms[:20])}\n"
            f"Top genes: {', '.join(plan.top_genes)}\n\n"
            "Current plan:\n"
        )
        for intent in plan.intents:
            prompt += (
                f"- [{intent.category}, priority {intent.priority}] "
                f"{intent.description}\n"
                f"  Tavily: {intent.tavily_query}\n"
                f"  PubMed: {intent.pubmed_query}\n"
            )
        prompt += (
            "\nRefine the queries to be more precise and clinically relevant. "
            "You may rewrite queries, add hypothesis-driven intents, or remove "
            "low-value ones. Keep max 5 intents total. Return a complete QueryPlan."
        )

        try:
            logger.info("QueryPlanner: refining plan with LLM...")
            refined: QueryPlan = llm.invoke(prompt)
            # Preserve top_genes and gene_clusters from rule-based plan
            refined.top_genes = plan.top_genes
            refined.gene_clusters = plan.gene_clusters
            logger.info(f"QueryPlanner: LLM refined to {len(refined.intents)} intents.")
            return refined
        except Exception as e:
            logger.warning(f"LLM refinement failed, using rule-based plan: {e}")
            return plan
