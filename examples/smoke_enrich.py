from enrichrag.core.enricher import GeneEnricher
from enrichrag.prompts.generator import PromptGenerator

# --- 使用範例 ---
genes = ["TP53", "KRAS", "EGFR", "TP63", "MYC", "PTEN", "RAF", "AKT"]

enricher = GeneEnricher(genes).run_enrichment().filter(pval_threshold=0.01)
print(enricher.get_top_terms("GO", n=5))

generator = PromptGenerator(template_path="/home/blue/code/EnrichRAG/enrichrag/prompts/templates/enrichment_analysis.yaml")
# final_insight_prompt = generator.build_enrichment_prompt(
#     gene_list=enricher.gene_list,
#     filtered_results=enricher.filtered_results,
#     disease="癌症"
# )


# --- 修正後的整合使用範例 ---
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import os
import pandas as pd
from typing import Dict, List
from langchain_core.prompts import load_prompt
# 從 .env 文件載入環境變數
from dotenv import load_dotenv
import os

# 載入 .env 文件（會自動尋找專案根目錄的 .env）
load_dotenv()

# 檢查 API key 是否已設置
if os.getenv("OPENAI_API_KEY"):
    print("✅ OpenAI API Key 已從 .env 載入")
else:
    print("❌ 找不到 OPENAI_API_KEY，請在專案根目錄建立 .env 文件")
    print("   參考 .env.example 文件的格式")

    
class PromptGenerator:
    """
    負責載入外部 Prompt 模板並填充生物資訊數據。
    """
    def __init__(self, template_path: str):
        # LangChain 支援從 yaml, json 或 txt 載入
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"找不到 Prompt 模板檔案：{template_path}")
        self.prompt_template = load_prompt(template_path)


# 1. 初始化模型與 Parser
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
parser = StrOutputParser()

# 2. 初始化 Generator (維持你原本的類別)
generator = PromptGenerator(template_path="/home/blue/code/EnrichRAG/enrichrag/prompts/templates/enrichment_analysis.yaml")

# 3. 建立 LCEL 鏈：直接將類別中的 prompt_template 作為起點
# 數據流：Template -> LLM -> String
chain = generator.prompt_template | llm | parser

# 4. 執行分析：將「數據字典」直接丟入 invoke，讓鏈自己去填充變數
insight = chain.invoke({
    "context": "疾病背景：癌症",
    "genes": ", ".join(enricher.gene_list),
    "go_table": enricher.filtered_results.get("GO", pd.DataFrame()).to_markdown(index=False),
    "kegg_table": enricher.filtered_results.get("KEGG", pd.DataFrame()).to_markdown(index=False)
})

print(insight)