"""
Trend Analyzer Agent.
Analyzes differences and trends between the current reporting week and historical project data.
Supports API-based LLM trend analysis and deterministic score-based delta analysis.
"""

import os
import json
from typing import List, Dict, Any, Optional
from agents.information_extractor import ExtractedProjectInfo
from utils.logger import get_logger
from utils.file_utils import load_json
from config.prompts import PromptLoader

logger = get_logger(__name__)

class TrendAnalyzer:
    """Agent that compares current weekly metrics with historical records."""
    
    def __init__(self, history_dir: str = "data/processed", model_name: str = "gemini-2.5-flash"):
        self.history_dir = os.path.abspath(history_dir)
        self.model_name = model_name
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        
        if self.gemini_key or self.openai_key:
            logger.info("TrendAnalyzer initialized with API credentials.")
        else:
            logger.warning("No API keys found for TrendAnalyzer. Running in offline rule-based mode.")

    def load_historical_data(self, project_name: Optional[str]) -> List[Dict[str, Any]]:
        """
        Scans history directory for JSON records corresponding to the project name,
        and returns them sorted chronologically.
        """
        if not project_name:
            return []
            
        history = []
        if not os.path.exists(self.history_dir):
            logger.warning(f"History directory {self.history_dir} does not exist.")
            return []

        # Find all JSON files containing the project name
        for filename in os.listdir(self.history_dir):
            if filename.endswith(".json") and project_name.lower().replace(" ", "_") in filename.lower():
                filepath = os.path.join(self.history_dir, filename)
                try:
                    data = load_json(filepath)
                    history.append(data)
                except Exception as e:
                    logger.error(f"Error loading historical file {filepath}: {e}")

        # Sort by report_date
        history.sort(key=lambda x: x.get("report_date", ""))
        logger.info(f"Loaded {len(history)} historical reports for project {project_name}.")
        return history

    def analyze_trends(self, current_data: ExtractedProjectInfo, historical_records: List[Dict[str, Any]]) -> str:
        """
        Compares current project data against historical records to create a trend report.
        """
        logger.info(f"Analyzing trends for project: {current_data.project_name or 'Unnamed'}")
        
        if not historical_records:
            logger.info("No historical records found for comparison. Providing baseline report.")
            return "No historical trends available. This is the first recorded report."

        if self.gemini_key:
            return self._analyze_via_gemini(current_data, historical_records)
        elif self.openai_key:
            return self._analyze_via_openai(current_data, historical_records)
        else:
            return self._rule_based_analyze(current_data, historical_records)

    def _analyze_via_gemini(self, current_data: ExtractedProjectInfo, historical_records: List[Dict[str, Any]]) -> str:
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=self.gemini_key)
            
            prompt_template = PromptLoader.get_prompt("trend_analysis")
            prompt = prompt_template.format(
                current_data=current_data.model_dump_json(indent=2),
                historical_data=json.dumps(historical_records, indent=2)
            )
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed trend analysis via Gemini API: {e}. Falling back to rule-based analysis.")
            return self._rule_based_analyze(current_data, historical_records)

    def _analyze_via_openai(self, current_data: ExtractedProjectInfo, historical_records: List[Dict[str, Any]]) -> str:
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(api_key=self.openai_key)
            
            prompt_template = PromptLoader.get_prompt("trend_analysis")
            prompt = prompt_template.format(
                current_data=current_data.model_dump_json(indent=2),
                historical_data=json.dumps(historical_records, indent=2)
            )
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed trend analysis via OpenAI API: {e}. Falling back to rule-based analysis.")
            return self._rule_based_analyze(current_data, historical_records)

    def _rule_based_analyze(self, current_data: ExtractedProjectInfo, historical_records: List[Dict[str, Any]]) -> str:
        logger.info("Executing rule-based trend analyzer.")
        
        # Sort history to find the most recent previous record
        historical_records.sort(key=lambda x: x.get("report_date", ""))
        latest_prev = historical_records[-1]
        
        prev_score = float(latest_prev.get("overall_score", 0.0))
        prev_status = latest_prev.get("overall_status", "UNKNOWN")
        
        # Calculate current scores using the reasoning engine on current data
        from agents.reasoning_agent import ReasoningAgent
        reasoner = ReasoningAgent()
        current_scores = reasoner.calculate_health_scores(current_data)
        current_score = current_scores["overall_score"]
        current_status = current_scores["rag_status"]
        
        delta = current_score - prev_score
        
        if delta > 0:
            overall_traj = f"Project health score improved by {delta:.1f} points (from {prev_score:.1f} to {current_score:.1f}), improving status from {prev_status} to {current_status}."
        elif delta < 0:
            overall_traj = f"Project health score declined by {abs(delta):.1f} points (from {prev_score:.1f} to {current_score:.1f}), indicating a trajectory shift from {prev_status} to {current_status}."
        else:
            overall_traj = f"Project health score remains stable at {current_score:.1f}/100 with RAG status {current_status}."

        # Schedule check
        curr_sched = current_scores["scores"]["schedule"]
        prev_sched = latest_prev.get("scores", {}).get("schedule", 100.0)
        sched_delta = curr_sched - prev_sched
        if sched_delta > 0:
            sched_text = f"Schedule index improved by {sched_delta:.1f} points, reflecting accelerated work rate."
        elif sched_delta < 0:
            sched_text = f"Schedule index drifted down by {abs(sched_delta):.1f} points due to progress lags."
        else:
            sched_text = "Schedule velocity remains stable compared to previous updates."

        # Financial check
        curr_budget = current_scores["scores"]["budget"]
        prev_budget = latest_prev.get("scores", {}).get("budget", 100.0)
        budget_delta = curr_budget - prev_budget
        if budget_delta > 0:
            budget_text = "Financial burn has stabilized and remains within baseline parameters."
        elif budget_delta < 0:
            budget_text = f"Financial overrun metrics increased by {abs(budget_delta):.1f} points, indicating rising burn rates."
        else:
            budget_text = "Budget spent trajectory is stable."

        # Operational Risks check
        curr_risks = current_scores["scores"]["risks"]
        prev_risks = latest_prev.get("scores", {}).get("risks", 100.0)
        risks_delta = curr_risks - prev_risks
        if risks_delta > 0:
            risks_text = "Active blockers or critical risk threats have been mitigated."
        elif risks_delta < 0:
            risks_text = f"Risk deductions increased by {abs(risks_delta):.1f} points due to new blockers or critical risk entries."
        else:
            risks_text = "Risk profile is unchanged from the prior period."

        markdown_report = (
            f"- **Overall Trajectory**: {overall_traj}\n"
            f"- **Schedule Velocity**: {sched_text}\n"
            f"- **Financial Burn Rate**: {budget_text}\n"
            f"- **Operational Risks**: {risks_text}"
        )
        return markdown_report
