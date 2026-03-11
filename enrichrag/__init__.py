"""EnrichRAG - Enrichment analysis for RAG systems."""

__version__ = "0.2.0"

from enrichrag.core.enricher import GeneEnricher
from enrichrag.prompts.generator import PromptGenerator

__all__ = ["GeneEnricher", "PromptGenerator"]
