"""Canonical relation taxonomy for all knowledge graph sources.

Every edge in the KG gets a normalized `relation` (atomic verb) and a
`relation_group` (user-facing category for UI filtering).

Raw/original relation strings are preserved in metadata_json.
"""

from __future__ import annotations

# ── Canonical atomic relations and their groups ──

RELATION_GROUPS: dict[str, str] = {
    # Regulation
    "activate": "Regulation",
    "inhibit": "Regulation",
    "upregulate": "Regulation",
    "downregulate": "Regulation",
    # Interaction
    "interact": "Interaction",
    "catalyze": "Interaction",
    "phosphorylation": "Interaction",
    "binding": "Interaction",
    # Association
    "associate": "Association",
    "predicted": "Association",
    "compound": "Association",
    # Expression
    "expression_up": "Expression",
    "expression_down": "Expression",
    # Clinical
    "treat": "Clinical",
    "cause": "Clinical",
    "biomarker": "Clinical",
    # Correlation
    "positive_correlate": "Correlation",
    "negative_correlate": "Correlation",
}


def get_group(relation: str) -> str:
    """Return the UI group for a canonical relation."""
    return RELATION_GROUPS.get(relation, "Association")


# ── Reactome: multi-label annotation → single canonical relation ──

# Priority order: first match wins when scanning semicolon-separated tags
_REACTOME_VERB_MAP: list[tuple[str, str]] = [
    ("inhibit", "inhibit"),
    ("inhibited by", "inhibit"),
    ("activate", "activate"),
    ("activated by", "activate"),
    ("catalyze", "catalyze"),
    ("catalyzed by", "catalyze"),
    ("expression regulates", "expression_up"),
    ("expression regulated by", "expression_down"),
    ("predicted", "predicted"),
    # context tags (complex, input, reaction) → ignored, fallback to interact
]


def normalize_reactome(raw: str) -> str:
    """Normalize a Reactome multi-label annotation to a canonical relation."""
    if not raw:
        return "interact"
    tags = [t.strip().lower() for t in raw.split(";")]
    for tag in tags:
        for pattern, canonical in _REACTOME_VERB_MAP:
            if tag == pattern:
                return canonical
    return "interact"


# ── KEGG: subtype name → canonical relation ──

_KEGG_MAP: dict[str, str] = {
    "activation": "activate",
    "inhibition": "inhibit",
    "expression": "expression_up",
    "repression": "expression_down",
    "phosphorylation": "phosphorylation",
    "dephosphorylation": "phosphorylation",
    "ubiquitination": "phosphorylation",  # PTM group
    "glycosylation": "phosphorylation",   # PTM group
    "binding/association": "binding",
    "association": "binding",
    "compound": "compound",
    "state change": "associate",
    "indirect effect": "associate",
    "missing interaction": "associate",
    "dissociation": "associate",
}


def normalize_kegg(raw: str) -> str:
    """Normalize a KEGG subtype name to a canonical relation."""
    return _KEGG_MAP.get(raw.strip().lower(), "associate")


# ── PubTator: relation type → canonical relation ──

_PUBTATOR_MAP: dict[str, str] = {
    "associate": "associate",
    "positive_correlate": "positive_correlate",
    "negative_correlate": "negative_correlate",
    "stimulate": "activate",
    "inhibit": "inhibit",
    "interact": "interact",
}


def normalize_pubtator(raw: str) -> str:
    """Normalize a PubTator relation type to a canonical relation."""
    return _PUBTATOR_MAP.get(raw.strip().lower(), "associate")


# ── Generic normalizer (for already-loaded DB or LLM extractor output) ──

_GENERIC_MAP: dict[str, str] = {
    # LLM extractor 9-enum
    "upregulate": "upregulate",
    "downregulate": "downregulate",
    "inhibit": "inhibit",
    "activate": "activate",
    "associate": "associate",
    "treat": "treat",
    "cause": "cause",
    "biomarker": "biomarker",
    "interact": "interact",
    # PubTator
    "positive_correlate": "positive_correlate",
    "negative_correlate": "negative_correlate",
    "stimulate": "activate",
    # KEGG
    "activation": "activate",
    "inhibition": "inhibit",
    "expression": "expression_up",
    "repression": "expression_down",
    "phosphorylation": "phosphorylation",
    "dephosphorylation": "phosphorylation",
    "ubiquitination": "phosphorylation",
    "glycosylation": "phosphorylation",
    "binding/association": "binding",
    "association": "binding",
    "compound": "compound",
    "state change": "associate",
    "indirect effect": "associate",
    "missing interaction": "associate",
    "dissociation": "associate",
    # Reactome atomic tags
    "activated by": "activate",
    "inhibited by": "inhibit",
    "catalyze": "catalyze",
    "catalyzed by": "catalyze",
    "expression regulates": "expression_up",
    "expression regulated by": "expression_down",
    "predicted": "predicted",
    "complex": "interact",
    "input": "interact",
    "reaction": "interact",
}


def normalize(raw: str, source_db: str = "") -> str:
    """Normalize any relation string to a canonical relation.

    Tries source-specific normalizer first, then falls back to generic map.
    """
    if not raw:
        return "associate"

    db = source_db.lower()
    if db == "reactome":
        return normalize_reactome(raw)
    if db == "kegg":
        return normalize_kegg(raw)
    if db == "pubtator":
        return normalize_pubtator(raw)

    # Generic: try direct lookup, then try as Reactome multi-label
    key = raw.strip().lower()
    if key in _GENERIC_MAP:
        return _GENERIC_MAP[key]
    if ";" in key:
        return normalize_reactome(raw)
    return "associate"
