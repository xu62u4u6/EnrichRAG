"""Query planner: transforms enrichment results into structured search intents."""

import json
import re
from collections import Counter, defaultdict
from typing import Dict, List, Literal, Optional

import pandas as pd
from pydantic import BaseModel, Field

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
    top_genes: List[str] = Field(default_factory=list)
    gene_clusters: Dict[str, List[str]] = Field(default_factory=dict)
    term_categories: Dict[str, str] = Field(default_factory=dict)
    summary: str = ""


# ── Term classification ──────────────────────────────────────────────────────

# Fallback keyword matching (used when no LLM available)
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


def _classify_terms_with_llm(
    terms: List[str], *, api_key: str, model: str = "gpt-4o"
) -> Dict[str, str]:
    """Classify enrichment terms into biological categories using one LLM call.

    Returns a dict mapping each term to its category name.
    """
    from langchain_openai import ChatOpenAI

    cleaned = [_clean_term(t) for t in terms]
    unique_terms = list(dict.fromkeys(cleaned))  # dedupe, preserve order

    prompt = (
        "You are a bioinformatics expert. Classify each biological term into a "
        "short, general biological category (2-4 words). Group similar processes together.\n\n"
        "Examples of good category names:\n"
        "- DNA damage response\n"
        "- cell cycle regulation\n"
        "- apoptosis and cell death\n"
        "- immune signaling\n"
        "- chromatin remodeling\n"
        "- transcriptional regulation\n"
        "- protein ubiquitination\n"
        "- metabolic regulation\n"
        "- autophagy\n\n"
        "Terms to classify:\n"
    )
    for i, t in enumerate(unique_terms[:40], 1):
        prompt += f"{i}. {t}\n"

    prompt += (
        "\nReturn ONLY a JSON object mapping each term to its category. "
        'Example: {"DNA repair": "DNA damage response", "apoptotic process": "apoptosis and cell death"}'
    )

    try:
        llm = ChatOpenAI(
            model=model, temperature=0, api_key=api_key, max_tokens=1000,
        )
        response = llm.invoke(prompt)
        text = response.content.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        mapping = json.loads(text)
        logger.info(f"LLM classified {len(mapping)} terms into {len(set(mapping.values()))} categories")
        # Map back to original term names
        result = {}
        for orig, clean in zip(terms, [_clean_term(t) for t in terms]):
            result[orig] = mapping.get(clean, clean)
        return result
    except Exception as e:
        logger.warning(f"LLM term classification failed, using keyword fallback: {e}")
        return {}

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
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ) -> QueryPlan:
        """Query planning from enrichment results.

        Uses LLM for term classification when api_key is provided,
        falls back to keyword matching otherwise.

        Returns a QueryPlan with up to 5 SearchIntents.
        """
        # Step 1: Collect all terms and genes
        gene_counter: Counter = Counter()
        all_terms: List[str] = []
        term_genes: Dict[str, List[str]] = {}  # term → genes list

        for df in enrichment_results.values():
            if df.empty or "genes" not in df.columns or "term" not in df.columns:
                continue
            for _, row in df.iterrows():
                term = str(row["term"])
                all_terms.append(term)
                row_genes = []
                genes_str = str(row.get("genes", ""))
                for g in genes_str.replace(",", ";").split(";"):
                    g = g.strip().upper()
                    if g:
                        gene_counter[g] += 1
                        row_genes.append(g)
                term_genes[term] = row_genes

        # Step 2: Classify terms (LLM or keyword fallback)
        llm_mapping: Dict[str, str] = {}
        if api_key and all_terms:
            llm_mapping = _classify_terms_with_llm(
                all_terms, api_key=api_key, model=model,
            )

        category_genes: Dict[str, Counter] = defaultdict(Counter)
        term_categories: Dict[str, str] = {}
        for term in all_terms:
            if llm_mapping and term in llm_mapping:
                category = llm_mapping[term]
            else:
                category = _classify_term(term)
            term_categories[term] = category
            for g in term_genes.get(term, []):
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
            term_categories=term_categories,
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
        ).with_structured_output(QueryPlan, method="function_calling")

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
