import os
import pandas as pd
from typing import Dict, List
from langchain_core.prompts import load_prompt

class PromptGenerator:
    """
    負責載入外部 Prompt 模板並填充生物資訊數據。
    """
    def __init__(self, template_path: str):
        # LangChain 支援從 yaml, json 或 txt 載入
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"找不到 Prompt 模板檔案：{template_path}")
        self.prompt_template = load_prompt(template_path)

    def build_enrichment_prompt(self, 
                                gene_list: List[str], 
                                filtered_results: Dict[str, pd.DataFrame], 
                                disease: str = "癌症") -> str:
        """
        將 GeneEnricher 的結果轉化為最終的 Prompt 字串。
        """
        # 準備數據
        genes_str = ", ".join(gene_list)
        
        # 提取表格並轉為 Markdown 格式（這是 LLM 最容易理解的格式）
        go_table = filtered_results.get("GO", pd.DataFrame()).to_markdown(index=False)
        kegg_table = filtered_results.get("KEGG", pd.DataFrame()).to_markdown(index=False)

        # 使用 LangChain 填充變數
        final_prompt = self.prompt_template.format(
            context=f"疾病背景：{disease}",
            genes=genes_str,
            go_table=go_table if go_table else "無顯著富集結果",
            kegg_table=kegg_table if kegg_table else "無顯著富集結果"
        )
        
        return final_prompt