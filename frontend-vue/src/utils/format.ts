import type { PipelineResult } from '../types';

export function normalizeResultShape(result: PipelineResult | null): PipelineResult | null {
  if (!result) return null;
  return {
    ...result,
    input_genes: deriveInputGenes(result),
    disease_context: result.disease_context || 'Analysis',
    enrichment_results: result.enrichment_results || {},
    llm_insight: result.llm_insight || '',
    sources: {
      web: result.sources?.web || result.web_sources || [],
      pubmed: result.sources?.pubmed || [],
    },
    gene_relations: result.gene_relations || [],
    graph: {
      nodes: result.graph?.nodes || [],
      edges: result.graph?.edges || [],
    },
  };
}

export function deriveInputGenes(result: PipelineResult): string[] {
  if (Array.isArray(result.input_genes) && result.input_genes.length) return result.input_genes;
  if (Array.isArray(result.genes) && result.genes.length) return result.genes;
  if (Array.isArray(result.gene_validation?.normalized_genes) && result.gene_validation.normalized_genes.length) {
    return result.gene_validation.normalized_genes;
  }
  return [];
}

export function formatDate(value?: string | null) {
  if (!value) return 'No timestamp';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function titleCase(value: string) {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
