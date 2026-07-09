"""
Portfolio Analyzer Agent.
Aggregates multiple weekly project reports to generate portfolio-level trends and insights in structured JSON.
Supports API-based LLM trend analysis and deterministic rule-based analysis.
"""

import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from utils.logger import get_logger
from utils.file_utils import load_json
from utils.parser_utils import parse_llm_json
from config.prompts import PromptLoader

logger = get_logger(__name__)

# Pydantic Schemas for Portfolio Trend Reports
class RepeatedMilestoneDelay(BaseModel):
    milestone_name: str = Field(..., description="Name of the delayed milestone")
    affected_projects: List[str] = Field(default_factory=list, description="Projects impacted by this delay")
    details: str = Field(..., description="Details regarding the repeated delay status")

class BudgetBurnTrends(BaseModel):
    total_portfolio_budget: float = Field(0.0, description="Sum of budgets across all projects")
    total_portfolio_spent: float = Field(0.0, description="Sum of actual spent across all projects")
    burn_rate_trajectory: str = Field("STABLE", description="Burn trajectory: STABLE | ACCELERATING | DECELERATING")
    insights: str = Field(..., description="Insights detailing the financial status of the portfolio")

class CommonBlocker(BaseModel):
    blocker_type: str = Field(..., description="Common blocker theme or area")
    affected_projects: List[str] = Field(default_factory=list, description="Projects blocked by this issue")
    details: str = Field(..., description="Details of the blocker impact")

class ProjectRiskProfile(BaseModel):
    project_name: str = Field(..., description="Name of the project")
    rag_status: str = Field(..., description="RAG status: RED | YELLOW | GREEN")
    reasons: str = Field(..., description="Reasons for project status flagging")

class ImprovingProject(BaseModel):
    project_name: str = Field(..., description="Name of the project")
    improvement_details: str = Field(..., description="Details showing metric score improvement trends")

class SentimentTrends(BaseModel):
    overall_sentiment: str = Field("NEUTRAL", description="Overall sentiment: POSITIVE | NEUTRAL | NEGATIVE")
    trajectory: str = Field("STABLE", description="Sentiment trajectory: IMPROVING | STABLE | DECLINING")
    details: str = Field(..., description="Synthesis of comments and feedback")

class PortfolioTrendReport(BaseModel):
    repeated_milestone_delays: List[RepeatedMilestoneDelay] = Field(default_factory=list)
    budget_burn_trends: BudgetBurnTrends = Field(default_factory=lambda: BudgetBurnTrends(insights="N/A"))
    common_blockers: List[CommonBlocker] = Field(default_factory=list)
    projects_at_risk: List[ProjectRiskProfile] = Field(default_factory=list)
    improving_projects: List[ImprovingProject] = Field(default_factory=list)
    sentiment_trends: SentimentTrends = Field(default_factory=lambda: SentimentTrends(details="N/A"))
    executive_insights: List[str] = Field(default_factory=list)

class PortfolioAnalyzer:
    """Agent that analyzes enterprise-wide project reports to extract portfolio trends."""
    
    def __init__(self, history_dir: str = "data/processed", model_name: str = "gemini-2.5-flash"):
        self.history_dir = os.path.abspath(history_dir)
        self.model_name = model_name
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        
        if self.gemini_key or self.openai_key:
            logger.info("PortfolioAnalyzer initialized with API credentials.")
        else:
            logger.warning("No API keys found for PortfolioAnalyzer. Running in offline rule-based mode.")

    def load_weekly_reports(self, timeframe_days: int = 30) -> List[Dict[str, Any]]:
        """
        Loads all project JSON report files from the processed directory
        that fall within the given timeframe in days.
        """
        logger.info(f"Scanning directory {self.history_dir} for weekly reports in the last {timeframe_days} days.")
        reports = []
        if not os.path.exists(self.history_dir):
            logger.warning("History directory does not exist.")
            return []

        limit_date = datetime.now() - timedelta(days=timeframe_days)

        for filename in os.listdir(self.history_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.history_dir, filename)
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime >= limit_date:
                        data = load_json(filepath)
                        reports.append(data)
                except Exception as e:
                    logger.error(f"Failed to read report {filepath}: {e}")

        logger.info(f"Loaded {len(reports)} reports for portfolio analysis.")
        return reports

    def analyze_portfolio(self, reports: Optional[List[Dict[str, Any]]] = None) -> PortfolioTrendReport:
        """
        Runs portfolio-level trend extraction over multiple weekly reports.
        
        Args:
            reports: Optional list of report dicts. Loads from history if None.
            
        Returns:
            Validated PortfolioTrendReport object.
        """
        if reports is None:
            reports = self.load_weekly_reports()

        if not reports:
            logger.warning("No reports provided for portfolio analysis. Returning empty trend report.")
            return PortfolioTrendReport()

        if self.gemini_key:
            return self._analyze_via_gemini(reports)
        elif self.openai_key:
            return self._analyze_via_openai(reports)
        else:
            return self._rule_based_analyze(reports)

    def _analyze_via_gemini(self, reports: List[Dict[str, Any]]) -> PortfolioTrendReport:
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=self.gemini_key)
            
            prompt_template = PromptLoader.get_prompt("portfolio_analysis")
            prompt = prompt_template.format(weekly_reports=json.dumps(reports, indent=2))
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            parsed_dict = parse_llm_json(response.text)
            return PortfolioTrendReport(**parsed_dict)
        except Exception as e:
            logger.error(f"Failed portfolio analysis via Gemini API: {e}. Falling back to rule-based analysis.")
            return self._rule_based_analyze(reports)

    def _analyze_via_openai(self, reports: List[Dict[str, Any]]) -> PortfolioTrendReport:
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(api_key=self.openai_key)
            
            prompt_template = PromptLoader.get_prompt("portfolio_analysis")
            prompt = prompt_template.format(weekly_reports=json.dumps(reports, indent=2))
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            parsed_dict = parse_llm_json(response.choices[0].message.content)
            return PortfolioTrendReport(**parsed_dict)
        except Exception as e:
            logger.error(f"Failed portfolio analysis via OpenAI API: {e}. Falling back to rule-based analysis.")
            return self._rule_based_analyze(reports)

    def _rule_based_analyze(self, reports: List[Dict[str, Any]]) -> PortfolioTrendReport:
        """Deterministically aggregates report files to construct a portfolio report."""
        logger.info("Executing rule-based portfolio trend analyzer.")

        # Group reports by project to get the latest state for each
        latest_project_reports: Dict[str, Dict[str, Any]] = {}
        project_report_histories: Dict[str, List[Dict[str, Any]]] = {}

        for r in reports:
            name = r.get("project_name") or r.get("raw_extracted_data", {}).get("project_name") or "Unnamed"
            project_report_histories.setdefault(name, []).append(r)
            
            # Keep latest based on date
            current_latest = latest_project_reports.get(name)
            date_str = r.get("report_date") or ""
            if not current_latest or date_str > current_latest.get("report_date", ""):
                latest_project_reports[name] = r

        # 1. Milestone delays
        delays_map: Dict[str, List[str]] = {}
        for project, rep in latest_project_reports.items():
            ext = rep.get("raw_extracted_data", {})
            delayed_ms = ext.get("delayed_milestones") or []
            # Check milestones lists
            for m in ext.get("milestones") or []:
                if isinstance(m, dict) and m.get("status") == "Delayed":
                    delayed_ms.append(m)
            
            for m in delayed_ms:
                m_name = m.get("name") if isinstance(m, dict) else str(m)
                if m_name:
                    delays_map.setdefault(m_name, []).append(project)

        repeated_delays = []
        for m_name, projects in delays_map.items():
            if len(projects) >= 1:
                repeated_delays.append(RepeatedMilestoneDelay(
                    milestone_name=m_name,
                    affected_projects=list(set(projects)),
                    details=f"Milestone '{m_name}' flagged as Delayed in project updates."
                ))

        # 2. Budget burn trends
        total_budget = 0.0
        total_spent = 0.0
        for project, rep in latest_project_reports.items():
            ext = rep.get("raw_extracted_data", {})
            total_budget += float(ext.get("budget") or 0.0)
            total_spent += float(ext.get("budget_spent") or 0.0)

        burn_trajectory = "STABLE"
        if total_budget > 0:
            burn_ratio = total_spent / total_budget
            if burn_ratio > 0.75:
                burn_trajectory = "ACCELERATING"
            elif burn_ratio < 0.25:
                burn_trajectory = "DECELERATING"

        budget_trends = BudgetBurnTrends(
            total_portfolio_budget=total_budget,
            total_portfolio_spent=total_spent,
            burn_rate_trajectory=burn_trajectory,
            insights=f"Portfolio spent stands at {total_spent / total_budget * 100:.1f}% of total budget allocation." if total_budget > 0 else "No budget info available."
        )

        # 3. Common blockers
        blockers_map: Dict[str, List[str]] = {}
        for project, rep in latest_project_reports.items():
            ext = rep.get("raw_extracted_data", {})
            blockers = ext.get("blockers") or []
            for b in blockers:
                # Group by simple key matches
                b_str = str(b).lower()
                theme = "Other Blockers"
                if "credential" in b_str or "access" in b_str or "permission" in b_str:
                    theme = "Access & Credentials Blocker"
                elif "hardware" in b_str or "server" in b_str or "delivery" in b_str:
                    theme = "Hardware & Infrastructure Delivery Blocker"
                elif "vendor" in b_str or "third-party" in b_str or "contract" in b_str:
                    theme = "Third-party & Vendor Dependencies"
                
                blockers_map.setdefault(theme, []).append(project)

        common_blockers = []
        for theme, projects in blockers_map.items():
            common_blockers.append(CommonBlocker(
                blocker_type=theme,
                affected_projects=list(set(projects)),
                details=f"Blockers categorized under '{theme}' affecting active progress."
            ))

        # 4. Projects at risk
        projects_at_risk = []
        for project, rep in latest_project_reports.items():
            status = rep.get("overall_status") or "GREEN"
            if status in ("RED", "YELLOW"):
                score = rep.get("overall_score") or 100.0
                projects_at_risk.append(ProjectRiskProfile(
                    project_name=project,
                    rag_status=status,
                    reasons=f"Weighted health score flagged at {score}/100. Category score values: {rep.get('scores') or {}}."
                ))

        # 5. Improving projects
        improving_projects = []
        for project, history in project_report_histories.items():
            if len(history) >= 2:
                # Sort by date
                history.sort(key=lambda x: x.get("report_date", ""))
                oldest = history[0]
                latest = history[-1]
                
                old_score = oldest.get("overall_score", 0.0)
                new_score = latest.get("overall_score", 0.0)
                
                if new_score > old_score:
                    improving_projects.append(ImprovingProject(
                        project_name=project,
                        improvement_details=f"Health score increased from {old_score} to {new_score} over reporting periods."
                    ))

        # 6. Sentiment trends
        sentiment_scores = []
        for project, rep in latest_project_reports.items():
            cat_scores = rep.get("scores") or {}
            sentiment_scores.append(float(cat_scores.get("sentiment", 80.0)))

        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 80.0
        sentiment_status = "POSITIVE" if avg_sentiment >= 80 else "NEUTRAL" if avg_sentiment >= 50 else "NEGATIVE"
        
        sentiment = SentimentTrends(
            overall_sentiment=sentiment_status,
            trajectory="STABLE",
            details=f"Average stakeholder sentiment score is calculated at {avg_sentiment:.1f}/100."
        )

        # 7. Executive insights
        insights = [
            f"Portfolio comprises {len(latest_project_reports)} unique projects under monitoring.",
            f"Currently, {len(projects_at_risk)} projects are marked with YELLOW or RED status risk profiles.",
            f"Common blocker categories identified include: {', '.join([b.blocker_type for b in common_blockers[:3]])}."
        ]

        return PortfolioTrendReport(
            repeated_milestone_delays=repeated_delays,
            budget_burn_trends=budget_trends,
            common_blockers=common_blockers,
            projects_at_risk=projects_at_risk,
            improving_projects=improving_projects,
            sentiment_trends=sentiment,
            executive_insights=insights
        )
