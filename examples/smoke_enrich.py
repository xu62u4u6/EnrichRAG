from enrichrag.core.enricher import GeneEnricher
from enrichrag.prompts.generator import PromptGenerator

# --- 使用範例 ---
genes = ["TP53", "KRAS", "EGFR", "TP63", "MYC", "PTEN", "RAF", "AKT"]

enricher = GeneEnricher(genes).run_enrichment().filter(pval_threshold=0.01)
print(enricher.get_top_terms("GO", n=5))

generator = PromptGenerator(template_path="/home/blue/code/EnrichRAG/enrichrag/prompts/templates/enrichment_analysis.yaml")
final_insight_prompt = generator.build_enrichment_prompt(
    gene_list=enricher.gene_list,
    filtered_results=enricher.filtered_results,
    disease="癌症"
)

print(final_insight_prompt)