"""
Pipeline evaluation tests — run full pipeline for curated gene sets,
then use LLM to verify the report satisfies expected biological claims.

Each test case defines:
  - A gene set + disease context
  - A list of claims (biological assertions the report should support)
  - A minimum hit rate (fraction of claims the report must satisfy)

Run:  uv run pytest tests/test_pipeline_eval.py -v
      uv run pytest tests/test_pipeline_eval.py -v -k "dna_repair"
"""

from dataclasses import dataclass, field

import pytest
from langchain_openai import ChatOpenAI

from enrichrag.core.pipeline import run_pipeline
from enrichrag.settings import settings


# ── Test case definition ───────────────────────────────────────────────


@dataclass
class PipelineEvalCase:
    """Defines a pipeline evaluation scenario."""

    name: str
    genes: list[str]
    disease: str
    # Biological claims the report should satisfy
    claims: list[str]
    # Minimum fraction of claims that must be hit (0.0–1.0)
    min_hit_rate: float = 0.7
    pval_threshold: float = 0.05


# ── Test cases ─────────────────────────────────────────────────────────

CASES = [
    PipelineEvalCase(
        name="dna_repair",
        genes=[
            "BRCA1", "MLH1", "MSH2", "RAD51", "FANCD2",
            "ERCC1", "XPA", "LIG4",
        ],
        disease="cancer",
        claims=[
            "The report identifies multiple distinct DNA repair sub-pathways covered by this gene set",
            "MLH1 and MSH2 are correctly classified as mismatch repair (MMR) pathway components",
            "BRCA1, RAD51, and FANCD2 are linked to homologous recombination (HR) or Fanconi anemia (FA) pathway",
            "ERCC1 and XPA are identified as nucleotide excision repair (NER) factors",
            "LIG4 is associated with non-homologous end joining (NHEJ)",
            "The report discusses genomic instability or cancer predisposition as a consequence of defects in these genes",
        ],
    ),
    PipelineEvalCase(
        name="emt",
        genes=[
            "SNAI1", "TWIST1", "ZEB1", "VIM", "CDH2",
            "FN1", "TGFB1",
        ],
        disease="cancer",
        claims=[
            "TGFB1 is identified as an upstream inducer or cytokine that drives EMT",
            "SNAI1, TWIST1, and ZEB1 are classified as EMT transcription factors (EMT-TFs)",
            "VIM, CDH2 (N-cadherin), and FN1 (Fibronectin) are described as mesenchymal markers",
            "The report links EMT to tumor invasion, migration, or metastasis",
        ],
    ),
    PipelineEvalCase(
        name="glycolysis",
        genes=[
            "HK2", "PKM", "LDHA", "PGK1", "SLC2A1",
        ],
        disease="cancer",
        claims=[
            "The report mentions the Warburg effect or aerobic glycolysis",
            "SLC2A1 (GLUT1) is identified as a glucose transporter",
            "HK2 and/or PKM are described as rate-limiting glycolytic enzymes",
            "LDHA is linked to lactate production and/or tumor microenvironment acidification",
        ],
    ),
    PipelineEvalCase(
        name="autophagy",
        genes=[
            "ULK1", "BECN1", "ATG5", "ATG7", "LC3B",
            "SQSTM1",
        ],
        disease="cancer",
        claims=[
            "ULK1 is identified as part of the initiation/kinase complex of autophagy",
            "BECN1 (Beclin 1) is linked to the PI3K complex or nucleation step",
            "ATG5, ATG7, and LC3B are associated with the ubiquitin-like conjugation system or membrane elongation",
            "SQSTM1 (p62) is described as an autophagy receptor or cargo adaptor",
            "The report discusses autophagic flux or the possibility that co-expression of LC3B and SQSTM1 may indicate blocked degradation rather than active autophagy",
        ],
    ),
    PipelineEvalCase(
        name="angiogenesis",
        genes=[
            "VEGFA", "KDR", "FLT1", "ANGPT1", "ANGPT2",
            "TEK", "CDH5",
        ],
        disease="cancer",
        claims=[
            "The report identifies the VEGF-VEGFR signaling axis (VEGFA binding KDR/FLT1) for endothelial proliferation and migration",
            "The Angiopoietin-Tie2 axis (ANGPT1/ANGPT2 with TEK) is described for vessel remodeling or stabilization",
            "CDH5 (VE-cadherin) is mentioned in the context of endothelial cell adhesion or vascular integrity",
            "The report links these genes to tumor angiogenesis or anti-angiogenic therapy (e.g. Bevacizumab)",
        ],
    ),
]


# ── LLM claim evaluator ───────────────────────────────────────────────

EVAL_SYSTEM_PROMPT = """\
You are a biology expert evaluating an enrichment analysis report.
You will be given a CLAIM and a REPORT.
Respond with exactly "YES" if the report supports the claim, or "NO" if it does not.
Do not explain. Just answer YES or NO."""


def evaluate_claims(
    report: str,
    claims: list[str],
    model: str | None = None,
) -> list[bool]:
    """Use LLM to check each claim against the report.

    Returns a list of booleans, one per claim.
    """
    llm = ChatOpenAI(
        model=model or settings.llm_model_report,
        temperature=0,
        api_key=settings.openai_api_key,
    )

    results = []
    for claim in claims:
        response = llm.invoke([
            {"role": "system", "content": EVAL_SYSTEM_PROMPT},
            {"role": "user", "content": f"CLAIM: {claim}\n\nREPORT:\n{report}"},
        ])
        results.append(response.content.strip().upper().startswith("YES"))

    return results


# ── Tests ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])
def test_pipeline_report(case: PipelineEvalCase):
    """Run full pipeline and verify report satisfies biological claims."""
    if not case.claims:
        pytest.skip("No claims defined yet")

    result = run_pipeline(
        genes=case.genes,
        disease=case.disease,
        pval_threshold=case.pval_threshold,
    )

    report = result.get("llm_insight", "")
    assert report, "Pipeline produced empty report"

    hits = evaluate_claims(report, case.claims)
    hit_rate = sum(hits) / len(hits)

    # Build detailed failure message
    missed = [
        claim for claim, hit in zip(case.claims, hits) if not hit
    ]

    assert hit_rate >= case.min_hit_rate, (
        f"Hit rate {hit_rate:.0%} < {case.min_hit_rate:.0%}\n"
        f"Missed claims:\n" + "\n".join(f"  - {c}" for c in missed)
    )
