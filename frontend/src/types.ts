export interface User {
  id: number;
  email: string;
  display_name: string;
}

export interface HistoryItem {
  id: number;
  disease_context: string;
  gene_count: number;
  input_genes: string[];
  created_at: string;
}

export interface ValidationRow {
  input_gene: string;
  normalized_gene?: string;
  normalized_symbol?: string;
  status: string;
  source?: string;
  gene_id?: string;
  official_name?: string;
  description?: string;
}

export interface ValidationResponse {
  normalized_genes: string[];
  accepted: ValidationRow[];
  remapped: ValidationRow[];
  rejected: ValidationRow[];
  rows: ValidationRow[];
  summary: Record<string, number>;
}

export interface GeneProfile {
  canonical_symbol: string;
  gene_id?: string;
  official_symbol?: string;
  official_full_name?: string;
  synonyms?: string;
  description?: string;
  type_of_gene?: string;
  chromosome?: string;
  map_location?: string;
  dbxrefs?: string;
  modification_date?: string;
  tax_id?: number;
}

export interface SourceItem {
  title?: string;
  url?: string;
  snippet?: string;
  source?: string;
  year?: string | number;
  journal?: string;
  pmid?: string | number;
  authors?: string[];
  pub_date?: string;
  abstract?: string;
  content?: string;
}

export interface GraphNode {
  id?: string;
  label?: string;
  name?: string;
  type?: string;
  kind?: string;
  score?: number;
}

export interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  relation?: string;
  relation_group?: string;
  type?: string;
  source_db?: string;
  evidence?: string;
  pmid?: string;
}

export interface PipelineResult {
  id?: number;
  input_genes?: string[];
  genes?: string[];
  disease_context?: string;
  enrichment_results?: Record<string, unknown[]>;
  llm_insight?: string;
  sources?: {
    web?: SourceItem[];
    pubmed?: SourceItem[];
  };
  web_sources?: SourceItem[];
  gene_relations?: Record<string, unknown>[];
  graph?: {
    nodes?: GraphNode[];
    edges?: GraphEdge[];
  };
  query_plan?: Record<string, unknown>;
  gene_validation?: ValidationResponse | null;
  timestamp?: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}
