import json
import argparse
import os
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from enrichrag.core.enricher import GeneEnricher
from enrichrag.prompts.generator import PromptGenerator

# 載入 .env 文件
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="EnrichRAG Pipeline: Input genes, output JSON analysis.")
    parser.add_argument("--genes", nargs="+", help="List of gene symbols (e.g. TP53 BRCA1)", required=True)
    parser.add_argument("--disease", help="Disease context for the prompt", default="癌症")
    parser.add_argument("--output", help="Path to save the output JSON", default="result.json")
    
    args = parser.parse_args()
    
    # 檢查 API key
    if os.getenv("OPENAI_API_KEY"):
        print("✅ OpenAI API Key 已從 .env 載入")
    else:
        print("❌ 找不到 OPENAI_API_KEY，請在專案根目錄建立 .env 文件")
    
    print(f"正在分析基因: {args.genes}")
    
    # 1. 執行富集分析
    enricher = GeneEnricher(gene_list=args.genes)
    enricher.run_enrichment()
    enricher.filter(pval_threshold=0.05)
    
    # 2. 準備 Prompt Generator 與 LLM Chain
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "enrichrag/prompts/templates/enrichment_analysis.yaml")
    
    insight = ""
    try:
        # 初始化 Generator
        generator = PromptGenerator(template_path=template_path)
        
        # 初始化模型與 Parser
        llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
        parser = StrOutputParser()
        
        # 建立 LCEL 鏈
        chain = generator.prompt_template | llm | parser
        
        # 準備輸入數據
        go_table = enricher.filtered_results.get("GO", pd.DataFrame()).to_markdown(index=False)
        kegg_table = enricher.filtered_results.get("KEGG", pd.DataFrame()).to_markdown(index=False)
        
        inputs = {
            "context": f"疾病背景：{args.disease}",
            "genes": ", ".join(args.genes),
            "go_table": go_table if go_table else "無顯著富集結果",
            "kegg_table": kegg_table if kegg_table else "無顯著富集結果"
        }
        
        print("正在生成分析報告...")
        insight = chain.invoke(inputs)
        
        print("\n--- 生成結果 ---\n")
        print(insight)
        print("\n----------------\n")
        
    except Exception as e:
        print(f"LLM 生成失敗: {e}")
        insight = f"Error generating insight: {e}"

    # 3. 整合結果並輸出 JSON
    output_data = {
        "input_genes": args.genes,
        "disease_context": args.disease,
        "enrichment_results": {
            label: df.to_dict(orient="records") 
            for label, df in enricher.filtered_results.items()
        },
        "llm_insight": insight
    }
    
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"分析完成！結果已儲存至: {args.output}")

if __name__ == "__main__":
    main()
