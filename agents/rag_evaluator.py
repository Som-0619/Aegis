"""
RAG Evaluator Agent.
Audits the generated report against the source context to ensure faithfulness,
detect hallucinations, and compute alignment metrics.
Supports API-based LLM faithfulness evaluation and deterministic local text auditing.
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from utils.logger import get_logger
from utils.file_utils import load_yaml
from utils.parser_utils import parse_llm_json
from config.prompts import PromptLoader

logger = get_logger(__name__)

class EvaluationResult(BaseModel):
    faithfulness_score: float = Field(..., description="Proportion of claims supported by source documents (0.0 to 1.0)")
    context_precision: float = Field(..., description="Precision of context utilization (0.0 to 1.0)")
    hallucinations_found: List[str] = Field(default_factory=list, description="List of unsupported facts/claims detected")
    verdict: str = Field(..., description="Verdict: PASS or FAIL")

class RAGEvaluator:
    """Agent that performs validation of reports against original documents."""
    
    def __init__(self, config_path: str = "config/rag_rules.yaml", model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.config_path = config_path
        self.rules = self._load_rules()
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        logger.info(f"RAGEvaluator initialized with rules configuration: {config_path}")

    def _load_rules(self) -> Dict[str, Any]:
        """Loads RAG audit thresholds."""
        import os
        try:
            return load_yaml(self.config_path)
        except Exception as e:
            logger.warning(f"Could not load RAG rules from {self.config_path}: {e}. Using fallback thresholds.")
            return {}

    def evaluate_report(self, raw_source_context: str, generated_report: str) -> EvaluationResult:
        """
        Compares report content with original context using LLM or local fallback.
        """
        logger.info("Evaluating generated report faithfulness against source documents.")
        
        if self.gemini_key:
            return self._evaluate_via_gemini(raw_source_context, generated_report)
        elif self.openai_key:
            return self._evaluate_via_openai(raw_source_context, generated_report)
        else:
            return self._rule_based_evaluate(raw_source_context, generated_report)

    def _evaluate_via_gemini(self, raw_source_context: str, generated_report: str) -> EvaluationResult:
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=self.gemini_key)
            
            prompt_template = PromptLoader.get_prompt("rag_evaluation")
            prompt = prompt_template.format(
                source_context=raw_source_context,
                report_content=generated_report
            )
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            parsed_dict = parse_llm_json(response.text)
            
            return self._enforce_thresholds(parsed_dict)
        except Exception as e:
            logger.error(f"Failed RAG evaluation via Gemini API: {e}. Falling back to local text analysis.")
            return self._rule_based_evaluate(raw_source_context, generated_report)

    def _evaluate_via_openai(self, raw_source_context: str, generated_report: str) -> EvaluationResult:
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(api_key=self.openai_key)
            
            prompt_template = PromptLoader.get_prompt("rag_evaluation")
            prompt = prompt_template.format(
                source_context=raw_source_context,
                report_content=generated_report
            )
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            parsed_dict = parse_llm_json(response.choices[0].message.content)
            
            return self._enforce_thresholds(parsed_dict)
        except Exception as e:
            logger.error(f"Failed RAG evaluation via OpenAI API: {e}. Falling back to local text analysis.")
            return self._rule_based_evaluate(raw_source_context, generated_report)

    def _enforce_thresholds(self, parsed_dict: Dict[str, Any]) -> EvaluationResult:
        threshold = self.rules.get("evaluation_metrics", {}).get("faithfulness_threshold", 0.85)
        result = EvaluationResult(**parsed_dict)
        
        if result.faithfulness_score < threshold:
            result.verdict = "FAIL"
            logger.warning(f"Faithfulness score {result.faithfulness_score} is below threshold {threshold}. Verdict: FAIL.")
        else:
            result.verdict = "PASS"
            logger.info(f"Report passed QA checks with faithfulness {result.faithfulness_score}.")
        return result

    def _rule_based_evaluate(self, raw_source: str, report: str) -> EvaluationResult:
        logger.info("Executing rule-based RAG faithfulness evaluator.")
        
        raw_lower = raw_source.lower()
        
        # 1. Match all budget / spent cash amounts (e.g. $100,000.00, $50,000, 250000)
        currency_pattern = r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?"
        currencies = re.findall(currency_pattern, report)
        
        hallucinations = []
        
        for curr in set(currencies):
            clean_curr = curr.replace("$", "").replace(",", "")
            raw_curr_match = clean_curr.split(".")[0]  # e.g. "110000"
            
            if curr.lower() not in raw_lower and raw_curr_match not in raw_lower:
                hallucinations.append(f"Report mentions financial amount '{curr}' which is not supported by source text.")

        # 2. Match dates YYYY-MM-DD
        date_pattern = r"\b\d{4}-\d{2}-\d{2}\b"
        dates = re.findall(date_pattern, report)
        for d in set(dates):
            # Exclude current compilation timestamps from warning logs
            if d not in raw_source and d != datetime.now().strftime("%Y-%m-%d"):
                hallucinations.append(f"Report mentions date '{d}' which is not supported by source text.")

        # Calculate faithfulness score
        base_faith = 1.0
        if hallucinations:
            # Deduct 0.15 per distinct hallucination, min score 0.0
            base_faith = max(0.0, 1.0 - (len(hallucinations) * 0.15))
            
        threshold = self.rules.get("evaluation_metrics", {}).get("faithfulness_threshold", 0.85)
        verdict = "PASS" if base_faith >= threshold else "FAIL"
        
        result = EvaluationResult(
            faithfulness_score=round(base_faith, 2),
            context_precision=0.95,
            hallucinations_found=hallucinations,
            verdict=verdict
        )
        logger.info(f"RAG QA Complete. Faithfulness: {result.faithfulness_score}. Verdict: {result.verdict}")
        return result
