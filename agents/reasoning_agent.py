"""
Reasoning Agent / Project Health Scoring Engine.
Performs deterministic, rule-based weighted health scoring of projects
based on extracted parameters and thresholds defined in config/scoring_config.yaml.
Integrates the AIExplanationAgent to generate executive narratives and recommendations.
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from agents.information_extractor import ExtractedProjectInfo
from utils.logger import get_logger
from utils.file_utils import load_yaml
from utils.date_utils import parse_date
from config.prompts import PromptLoader

logger = get_logger(__name__)

class AIExplanationAgent:
    """Agent that generates narrative project summaries and recommendations using LLMs or fallbacks."""
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        if self.gemini_key or self.openai_key:
            logger.info("AIExplanationAgent initialized with API credentials.")
        else:
            logger.warning("No API keys found for Explanation agent. Running in offline rule-based narrative mode.")

    def generate_explanation(self, data: ExtractedProjectInfo, scores: Dict[str, Any]) -> Dict[str, str]:
        """Generates executive summaries and recommendations based on score dynamics."""
        logger.info("Generating AI explanation narrative.")
        
        if self.gemini_key:
            return self._explain_via_gemini(data, scores)
        elif self.openai_key:
            return self._explain_via_openai(data, scores)
        else:
            return self._rule_based_explain(data, scores)

    def _explain_via_gemini(self, data: ExtractedProjectInfo, scores: Dict[str, Any]) -> Dict[str, str]:
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=self.gemini_key)
            
            prompt_template = PromptLoader.get_prompt("explanation")
            prompt = prompt_template.format(
                rag_status=scores["rag_status"],
                scores=json.dumps(scores["scores"], indent=2),
                project_info=data.model_dump_json(indent=2)
            )
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return self._parse_explanation_response(response.text)
        except Exception as e:
            logger.error(f"Failed AI explanation via Gemini API: {e}. Falling back to rule-based explanation.")
            return self._rule_based_explain(data, scores)

    def _explain_via_openai(self, data: ExtractedProjectInfo, scores: Dict[str, Any]) -> Dict[str, str]:
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(api_key=self.openai_key)
            
            prompt_template = PromptLoader.get_prompt("explanation")
            prompt = prompt_template.format(
                rag_status=scores["rag_status"],
                scores=json.dumps(scores["scores"], indent=2),
                project_info=data.model_dump_json(indent=2)
            )
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            return self._parse_explanation_response(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Failed AI explanation via OpenAI API: {e}. Falling back to rule-based explanation.")
            return self._rule_based_explain(data, scores)

    def _parse_explanation_response(self, text: str) -> Dict[str, str]:
        from utils.parser_utils import extract_markdown_section
        
        pmo_reasoning = extract_markdown_section(text, "PMO Executive Summary")
        recommendations = extract_markdown_section(text, "Actionable Recommendations")
        
        # Clean up section titles if captured inside the content
        pmo_reasoning = re.sub(r"^###?\s*PMO Executive Summary\s*", "", pmo_reasoning, flags=re.IGNORECASE).strip()
        recommendations = re.sub(r"^###?\s*Actionable Recommendations\s*", "", recommendations, flags=re.IGNORECASE).strip()
        
        if not pmo_reasoning:
            pmo_reasoning = text  # Fallback to entire text
            
        return {
            "pmo_reasoning": pmo_reasoning,
            "recommendations": recommendations or "1. Monitor project progress."
        }

    def _rule_based_explain(self, data: ExtractedProjectInfo, scores: Dict[str, Any]) -> Dict[str, str]:
        logger.info("Executing rule-based PMO explanation generator.")
        
        project = data.project_name or "the project"
        rag = scores["rag_status"]
        overall = scores["overall_score"]
        
        # Audit data completeness to report uncertainties
        uncertainties = []
        if not data.project_name:
            uncertainties.append("Project name is missing from source files.")
        if not data.planned_start_date or not data.planned_end_date:
            uncertainties.append("Planned start/end dates are not provided, limiting schedule precision.")
        if data.budget is None or data.budget_spent is None:
            uncertainties.append("Financial metrics (budget or spent amount) are missing, preventing cost tracking.")
        if data.milestones is None:
            uncertainties.append("Milestone registers are missing, preventing task delay tracking.")
        if data.open_risks is None:
            uncertainties.append("Risk registers are missing, limiting threat tracking.")
        if data.stakeholder_comments is None:
            uncertainties.append("Stakeholder comments are missing, preventing sentiment analysis.")
        if data.resource_availability is None:
            uncertainties.append("Resource allocation details are missing.")

        categories = scores["scores"]
        
        # Schedule review
        if categories["schedule"] == 100.0:
            sched_text = "schedule is currently on track"
        else:
            sched_text = f"schedule is experiencing pressure due to progress lag (score: {categories['schedule']}/100)"

        # Budget review
        if categories["budget"] == 100.0:
            budget_text = "budget remains within baseline parameters"
        else:
            budget_text = f"budget is experiencing overruns (score: {categories['budget']}/100)"

        # Milestones review
        if categories["milestones"] == 100.0:
            milestones_text = "key milestones are progressing as planned"
        else:
            milestones_text = f"key milestones are facing delays (score: {categories['milestones']}/100)"

        # Risks review
        if categories["risks"] == 100.0:
            risks_text = "no significant risks or blocker items have been logged"
        else:
            risks_text = f"multiple active risk items or blockers have been logged (score: {categories['risks']}/100)"

        # Sentiment review
        if categories["sentiment"] >= 80.0:
            sentiment_text = "stakeholder sentiment remains positive"
        else:
            sentiment_text = f"stakeholder comments indicate concerns (score: {categories['sentiment']}/100)"

        # Resource review
        if categories["resources"] == 100.0:
            resource_text = "resource availability is adequate"
        else:
            resource_text = "resource constraints have been flagged"

        summary = (
            f"The overall health status of **{project}** is evaluated as **{rag}** (weighted score: **{overall}/100**). "
            f"This rating is driven by the following parameters: the {sched_text}, the {budget_text}, and {milestones_text}. "
            f"Additionally, {risks_text}, {sentiment_text}, and {resource_text}.\n\n"
        )
        
        if uncertainties:
            summary += "**Data Integrity Warnings:**\n" + "\n".join([f"- *Uncertainty: {u}*" for u in uncertainties]) + "\n"

        # Actionable Recommendations
        recommendations = []
        if categories["schedule"] < 100.0:
            recommendations.append("Conduct a schedule recovery workshop to align actual progress with the planned timeline.")
        if categories["budget"] < 100.0:
            recommendations.append("Implement a cost control audit to review and mitigate actual budget overruns.")
        if categories["milestones"] < 100.0:
            recommendations.append("Assign dedicated task owners to recover delayed milestones.")
        if categories["risks"] < 100.0:
            recommendations.append("Prioritize blocker resolution and update mitigation paths for critical risks.")
        if categories["sentiment"] < 80.0:
            recommendations.append("Schedule a stakeholder meeting to address comments and rebuild confidence.")
        if categories["resources"] < 100.0:
            recommendations.append("Assess staffing deficit and reallocate resources from lower-priority tasks.")

        if not recommendations:
            recommendations.append("Continue current operations and maintain standard status checks.")

        rec_markdown = "\n".join([f"{i+1}. {rec}" for i, rec in enumerate(recommendations)])

        return {
            "pmo_reasoning": summary.strip(),
            "recommendations": rec_markdown.strip()
        }

class ReasoningAgent:
    """Project Health Scoring Engine."""
    
    def __init__(self, config_path: str = "config/scoring_config.yaml", model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.config_path = config_path
        self.config = self._load_config()
        logger.info(f"ReasoningAgent initialized with scoring configuration: {config_path}")

    def _load_config(self) -> Dict[str, Any]:
        """Loads health scoring weights and thresholds from the config file."""
        try:
            return load_yaml(self.config_path)
        except Exception as e:
            logger.warning(f"Failed to load config {self.config_path}: {e}. Using code-level fallbacks.")
            return {}

    def calculate_health_scores(self, data: ExtractedProjectInfo) -> Dict[str, Any]:
        """
        Calculates deterministic health scores for all categories and returns the overall RAG status.
        """
        logger.info(f"Executing deterministic health scoring for project: {data.project_name or 'Unnamed Project'}")

        # Load weights
        weights = self.config.get("metric_weights", {
            "schedule": 0.30,
            "budget": 0.20,
            "milestones": 0.20,
            "risks": 0.15,
            "sentiment": 0.10,
            "resources": 0.05
        })

        # Calculate scores
        schedule_score = self._score_schedule(data)
        budget_score = self._score_budget(data)
        milestones_score = self._score_milestones(data)
        risks_score = self._score_risks(data)
        sentiment_score = self._score_sentiment(data)
        resources_score = self._score_resources(data)

        # Calculate overall weighted score
        overall_score = (
            schedule_score * weights.get("schedule", 0.30) +
            budget_score * weights.get("budget", 0.20) +
            milestones_score * weights.get("milestones", 0.20) +
            risks_score * weights.get("risks", 0.15) +
            sentiment_score * weights.get("sentiment", 0.10) +
            resources_score * weights.get("resources", 0.05)
        )
        overall_score = round(overall_score, 1)

        # Determine RAG status
        thresholds = self.config.get("health_score_thresholds", {})
        green_min = thresholds.get("green", {}).get("min", 80)
        yellow_min = thresholds.get("yellow", {}).get("min", 50)

        if overall_score >= green_min:
            rag_status = "GREEN"
        elif overall_score >= yellow_min:
            rag_status = "YELLOW"
        else:
            rag_status = "RED"

        results = {
            "scores": {
                "schedule": round(schedule_score, 1),
                "budget": round(budget_score, 1),
                "milestones": round(milestones_score, 1),
                "risks": round(risks_score, 1),
                "sentiment": round(sentiment_score, 1),
                "resources": round(resources_score, 1)
            },
            "overall_score": overall_score,
            "rag_status": rag_status
        }
        
        logger.info(f"Health scoring complete. Overall Score: {overall_score}, RAG Status: {rag_status}")
        return results

    def _score_schedule(self, data: ExtractedProjectInfo) -> float:
        if not data.planned_start_date or not data.planned_end_date:
            return 100.0

        try:
            start = parse_date(data.planned_start_date)
            end = parse_date(data.planned_end_date)
            today = datetime.now()

            total_days = (end - start).days
            if total_days <= 0:
                return 100.0

            elapsed_days = (today - start).days
            elapsed_ratio = max(0.0, min(1.0, elapsed_days / total_days))
            expected_progress = elapsed_ratio * 100.0

            actual_progress = 0.0
            if data.current_progress:
                progress_str = str(data.current_progress).lower()
                if "complete" in progress_str:
                    actual_progress = 100.0
                else:
                    progress_match = re.search(r"(\d+)", progress_str)
                    if progress_match:
                        actual_progress = float(progress_match.group(1))
                    else:
                        actual_progress = 0.0

            lag = expected_progress - actual_progress
            if lag > 0:
                lag_multiplier = self.config.get("schedule", {}).get("progress_lag_multiplier", 1.5)
                penalty = lag * lag_multiplier
                return max(0.0, 100.0 - penalty)
            
            return 100.0
        except Exception as e:
            logger.error(f"Error calculating schedule score: {e}")
            return 100.0

    def _score_budget(self, data: ExtractedProjectInfo) -> float:
        if data.budget is None or data.budget_spent is None:
            return 100.0
        if data.budget <= 0:
            return 100.0

        if data.budget_spent > data.budget:
            overrun_ratio = (data.budget_spent - data.budget) / data.budget
            overrun_multiplier = self.config.get("budget", {}).get("overrun_multiplier", 200.0)
            penalty = overrun_ratio * overrun_multiplier
            return max(0.0, 100.0 - penalty)

        return 100.0

    def _score_milestones(self, data: ExtractedProjectInfo) -> float:
        milestones = data.milestones or []
        delayed = data.delayed_milestones or []

        delayed_count = len(delayed)
        for m in milestones:
            if m.status and m.status.lower() == "delayed" and m not in delayed:
                delayed_count += 1

        total_count = len(milestones)
        if total_count == 0:
            return 100.0

        delay_ratio = delayed_count / total_count
        delay_multiplier = self.config.get("milestones", {}).get("delay_multiplier", 100.0)
        penalty = delay_ratio * delay_multiplier
        return max(0.0, 100.0 - penalty)

    def _score_risks(self, data: ExtractedProjectInfo) -> float:
        score = 100.0
        penalties = self.config.get("risks", {}).get("penalties", {
            "blocker": 25, "risk_critical": 20, "risk_high": 15, "risk_medium": 10, "risk_low": 5
        })

        blockers = data.blockers or []
        score -= len(blockers) * penalties.get("blocker", 25)

        open_risks = data.open_risks or []
        for risk in open_risks:
            sev = (risk.severity or "medium").lower()
            if sev == "critical":
                score -= penalties.get("risk_critical", 20)
            elif sev == "high":
                score -= penalties.get("risk_high", 15)
            elif sev == "low":
                score -= penalties.get("risk_low", 5)
            else:
                score -= penalties.get("risk_medium", 10)

        return max(0.0, score)

    def _score_sentiment(self, data: ExtractedProjectInfo) -> float:
        sentiment_cfg = self.config.get("sentiment", {})
        base_score = sentiment_cfg.get("base_score", 80)
        positive_boost = sentiment_cfg.get("positive_boost", 10)
        negative_penalty = sentiment_cfg.get("negative_penalty", 20)
        pos_keywords = sentiment_cfg.get("positive_keywords", ["happy", "pleased", "satisfied", "excellent", "great", "good"])
        neg_keywords = sentiment_cfg.get("negative_keywords", ["concerned", "worried", "unhappy", "delay", "risk", "block"])

        comments = data.stakeholder_comments or []
        if not comments:
            return float(base_score)

        score = float(base_score)
        combined_comments = " ".join(comments).lower()

        for word in pos_keywords:
            matches = len(re.findall(rf"\b{re.escape(word.lower())}\b", combined_comments))
            score += matches * positive_boost

        for word in neg_keywords:
            matches = len(re.findall(rf"\b{re.escape(word.lower())}\b", combined_comments))
            score -= matches * negative_penalty

        return max(0.0, min(100.0, score))

    def _score_resources(self, data: ExtractedProjectInfo) -> float:
        res_cfg = self.config.get("resources", {})
        base_score = res_cfg.get("base_score", 100)
        deficit_penalty = res_cfg.get("deficit_penalty", 50)
        deficit_keywords = res_cfg.get("deficit_keywords", ["low", "limited", "deficit", "shortage", "missing", "tight"])

        availability = data.resource_availability
        if not availability:
            return float(base_score)

        availability_lower = str(availability).lower()
        
        for keyword in deficit_keywords:
            if re.search(rf"\b{re.escape(keyword.lower())}\b", availability_lower):
                return max(0.0, float(base_score - deficit_penalty))

        return float(base_score)

    def generate_reasoning_and_recommendations(self, data: ExtractedProjectInfo, scores: Dict[str, Any], trends_summary: str) -> Dict[str, str]:
        """
        Generates PMO executive summaries and actionable recommendations.
        Delegates narrative generation to the AIExplanationAgent.
        """
        explanation_agent = AIExplanationAgent(model_name=self.model_name)
        return explanation_agent.generate_explanation(data, scores)
