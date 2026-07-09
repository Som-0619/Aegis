"""
Information Extractor Agent.
Extracts structured project metadata, milestones, risks, blockers, financials,
sentiment, and resource status from raw text.
Supports API-based LLM extraction and rule-based regex parsing fallback.
"""

import os
import re
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from utils.logger import get_logger
from utils.parser_utils import parse_llm_json
from config.prompts import PromptLoader

logger = get_logger(__name__)

# Pydantic Schemas for Phase 2 Structured Project Information
class ExtractedMilestone(BaseModel):
    name: Optional[str] = Field(None, description="Name of the milestone")
    due_date: Optional[str] = Field(None, description="Due date (YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="Status (Not Started, In Progress, Completed, Delayed)")
    completion_percentage: Optional[float] = Field(None, description="Completion percentage (0 to 100)")

class ExtractedRisk(BaseModel):
    description: Optional[str] = Field(None, description="Detailed description of the risk")
    severity: Optional[str] = Field(None, description="Severity level (Low, Medium, High, Critical)")
    status: Optional[str] = Field(None, description="Status of the risk (Open, Mitigated)")
    mitigation_plan: Optional[str] = Field(None, description="Plan to resolve or mitigate the risk")

class ExtractedProjectInfo(BaseModel):
    project_name: Optional[str] = Field(None, description="Name of the project")
    planned_start_date: Optional[str] = Field(None, description="Planned start date (YYYY-MM-DD)")
    planned_end_date: Optional[str] = Field(None, description="Planned end date (YYYY-MM-DD)")
    current_progress: Optional[str] = Field(None, description="Current progress (e.g. '45%')")
    budget: Optional[float] = Field(None, description="Total planned baseline budget")
    budget_spent: Optional[float] = Field(None, description="Actual amount spent to date")
    milestones: Optional[List[ExtractedMilestone]] = Field(None, description="List of all milestones")
    delayed_milestones: Optional[List[ExtractedMilestone]] = Field(None, description="List of delayed milestones only")
    open_risks: Optional[List[ExtractedRisk]] = Field(None, description="List of active open risks")
    blockers: Optional[List[str]] = Field(None, description="List of active blockers or issues")
    stakeholder_comments: Optional[List[str]] = Field(None, description="List of stakeholder feedback or comments")
    dependencies: Optional[List[str]] = Field(None, description="List of project dependencies")
    resource_availability: Optional[str] = Field(None, description="Summary status of resource availability")

class InformationExtractor:
    """Agent that calls LLMs to extract project parameters or falls back to rule-based parsing."""
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        
        if self.gemini_key:
            logger.info("GEMINI_API_KEY found. Initializing legacy Google Generative AI client.")
        elif self.openai_key:
            logger.info("OPENAI_API_KEY found. Initializing OpenAI client.")
        else:
            logger.warning("No API keys found for LLM extraction. Running in offline rule-based regex fallback mode.")

    def extract(self, raw_text: str) -> ExtractedProjectInfo:
        """
        Parses raw text and returns a populated ExtractedProjectInfo object.
        
        Args:
            raw_text: Unstructured text content.
            
        Returns:
            ExtractedProjectInfo Pydantic object.
        """
        logger.info("Starting information extraction pipeline.")
        
        if not raw_text or not raw_text.strip():
            logger.warning("Input raw text is empty. Returning default empty schema.")
            return ExtractedProjectInfo()
            
        # If API keys are available, run LLM extraction
        if self.gemini_key:
            return self._extract_via_gemini(raw_text)
        elif self.openai_key:
            return self._extract_via_openai(raw_text)
        else:
            # Offline fallback
            return self._rule_based_extract(raw_text)

    def _extract_via_gemini(self, raw_text: str) -> ExtractedProjectInfo:
        """Extracts information using Google's generative AI client."""
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=self.gemini_key)
            
            prompt_template = PromptLoader.get_prompt("extraction")
            prompt = prompt_template.format(context=raw_text)
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            
            parsed_dict = parse_llm_json(response.text)
            return ExtractedProjectInfo(**parsed_dict)
        except Exception as e:
            logger.error(f"Failed extraction via Gemini API: {e}. Falling back to rule-based extraction.")
            return self._rule_based_extract(raw_text)

    def _extract_via_openai(self, raw_text: str) -> ExtractedProjectInfo:
        """Extracts information using OpenAI's client."""
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(api_key=self.openai_key)
            
            prompt_template = PromptLoader.get_prompt("extraction")
            prompt = prompt_template.format(context=raw_text)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            parsed_dict = parse_llm_json(response.choices[0].message.content)
            return ExtractedProjectInfo(**parsed_dict)
        except Exception as e:
            logger.error(f"Failed extraction via OpenAI API: {e}. Falling back to rule-based extraction.")
            return self._rule_based_extract(raw_text)

    def _rule_based_extract(self, text: str) -> ExtractedProjectInfo:
        """
        Parses text deterministically using regular expressions.
        Extracts names, dates, budgets, progress, and parses lists of milestones, risks, and comments.
        """
        logger.info("Executing rule-based regex fallback parser.")
        
        info = {}

        # 1. Project Name
        project_match = re.search(r"(?:Project Name|Project)\s*:\s*([^\n\r]+)", text, re.IGNORECASE)
        if project_match:
            info["project_name"] = project_match.group(1).strip()
        else:
            name_scan = re.search(r"\bProject\s+([A-Za-z0-9_-]+)\b", text)
            info["project_name"] = name_scan.group(1).strip() if name_scan else None

        # 2. Dates (YYYY-MM-DD)
        start_match = re.search(r"(?:Planned Start Date|Start Date|Start)\s*:\s*([\d-]+)", text, re.IGNORECASE)
        info["planned_start_date"] = start_match.group(1).strip() if start_match else None
        
        end_match = re.search(r"(?:Planned End Date|End Date|End)\s*:\s*([\d-]+)", text, re.IGNORECASE)
        info["planned_end_date"] = end_match.group(1).strip() if end_match else None

        # If labels not matched, look for any YYYY-MM-DD patterns
        dates_found = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
        if not info["planned_start_date"] and len(dates_found) >= 1:
            info["planned_start_date"] = dates_found[0]
        if not info["planned_end_date"] and len(dates_found) >= 2:
            info["planned_end_date"] = dates_found[1]

        # 3. Current Progress (e.g. 45% or In Progress)
        progress_match = re.search(r"(?:Current Progress|Progress|Completion)\s*:\s*([^\n\r]+)", text, re.IGNORECASE)
        info["current_progress"] = progress_match.group(1).strip() if progress_match else None

        # Synthesize timeline start/end dates if progress values are present but dates are missing
        planned_prog_match = re.search(r"(?:Planned Progress|Expected Progress|Schedule Delay)(?:[^:\n]*):\s*(\d+)%", text, re.IGNORECASE)
        curr_prog_match = re.search(r"Current Progress(?:[^:\n]*):\s*(\d+)%", text, re.IGNORECASE)
        
        if planned_prog_match and curr_prog_match and not info["planned_start_date"] and not info["planned_end_date"]:
            try:
                e_val = float(planned_prog_match.group(1))
                c_val = float(curr_prog_match.group(1))
                # If "Schedule Delay: 85%", expected progress is current_progress + delay
                if "delay" in planned_prog_match.group(0).lower():
                    e_val = c_val + e_val
                
                if e_val > 0:
                    from datetime import datetime, timedelta
                    ref_date = datetime(2026, 7, 8)
                    start_date = datetime(2026, 1, 1)
                    elapsed_days = (ref_date - start_date).days
                    total_days = int(elapsed_days / (e_val / 100.0))
                    end_date = start_date + timedelta(days=total_days)
                    
                    info["planned_start_date"] = start_date.strftime("%Y-%m-%d")
                    info["planned_end_date"] = end_date.strftime("%Y-%m-%d")
                    logger.info(f"Synthesized dates for schedule lag scoring: {info['planned_start_date']} to {info['planned_end_date']}")
            except Exception as ex:
                logger.error(f"Error synthesizing timeline dates: {ex}")

        # 4. Budget
        budget_match = re.search(r"Budget(?:[^:\n]*):\s*\$?([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
        if budget_match:
            info["budget"] = float(budget_match.group(1).replace(",", ""))
        else:
            info["budget"] = None

        # 5. Budget Spent
        spent_match = re.search(r"(?:Spent|Actual Spend|Actual Cost|Spent Budget)(?:[^:\n]*):\s*\$?([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
        if spent_match:
            info["budget_spent"] = float(spent_match.group(1).replace(",", ""))
        else:
            info["budget_spent"] = None

        def get_section_lines(section_name: str, exclude_tables: bool = True) -> List[str]:
            pattern = rf"(?:^|\n)\s*#*\s*{re.escape(section_name)}[^\n]*\n([\s\S]*?)(?=\n\s*#*\s*\w|\n*$)"
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                return []
            lines = [l.strip(" \t*-•") for l in match.group(1).split("\n") if l.strip()]
            if exclude_tables:
                lines = [l for l in lines if l.count('|') < 2 and not l.strip().startswith('|')]
            return lines

        # 6. Milestones & Delayed Milestones
        milestones = []
        delayed_milestones = []
        milestone_lines = get_section_lines("Milestones", exclude_tables=False)
        
        # Scan lines containing "milestone"
        if not milestone_lines:
            for line in text.split("\n"):
                if "milestone" in line.lower() and (":" in line or "|" in line):
                    milestone_lines.append(line.strip(" *-•"))

        # If a list is present, parse it
        for m_line in milestone_lines:
            parts = [p.strip() for p in re.split(r"[|:]", m_line)]
            if len(parts) >= 1:
                name = parts[0]
                date = None
                status = "Not Started"
                pct = 0.0
                
                date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", m_line)
                if date_match:
                    date = date_match.group(0)
                
                m_line_lower = m_line.lower()
                if "completed" in m_line_lower:
                    status = "Completed"
                    pct = 100.0
                elif "delayed" in m_line_lower or "late" in m_line_lower:
                    status = "Delayed"
                    pct = 50.0
                elif "in progress" in m_line_lower:
                    status = "In Progress"
                    pct = 50.0
                
                pct_match = re.search(r"(\d+)%", m_line)
                if pct_match:
                    pct = float(pct_match.group(1))

                ms_obj = ExtractedMilestone(
                    name=name,
                    due_date=date,
                    status=status,
                    completion_percentage=pct
                )
                milestones.append(ms_obj)
                if status == "Delayed":
                    delayed_milestones.append(ms_obj)

        # Fallback: Parse milestone count from key-values
        completed_match = re.search(r"(?:Completed Milestones|Completed)(?:[^:\n]*):\s*(\d+)", text, re.IGNORECASE)
        delayed_match = re.search(r"(?:Delayed Milestones|Delayed|Missed Milestones|Missed)(?:[^:\n]*):\s*(\d+)", text, re.IGNORECASE)
        
        if (completed_match or delayed_match) and not milestones:
            comp_val = int(completed_match.group(1)) if completed_match else 0
            del_val = int(delayed_match.group(1)) if delayed_match else 0
            
            for i in range(comp_val):
                milestones.append(ExtractedMilestone(name=f"Milestone Comp {i+1}", status="Completed", completion_percentage=100.0))
            for i in range(del_val):
                ms = ExtractedMilestone(name=f"Milestone Del {i+1}", status="Delayed", completion_percentage=50.0)
                milestones.append(ms)
                delayed_milestones.append(ms)

        info["milestones"] = milestones if milestones else None
        info["delayed_milestones"] = delayed_milestones if delayed_milestones else None

        # 7. Open Risks
        risks = []
        risk_lines = get_section_lines("Risks", exclude_tables=False)
        if not risk_lines:
            for line in text.split("\n"):
                if "risk" in line.lower() and (":" in line or "-" in line) and "mitigation" in line.lower():
                    risk_lines.append(line.strip(" *-•"))

        for r_line in risk_lines:
            desc = r_line
            sev = "Medium"
            status = "Open"
            mit = "N/A"
            
            r_line_lower = r_line.lower()
            if "critical" in r_line_lower:
                sev = "Critical"
            elif "high" in r_line_lower:
                sev = "High"
            elif "low" in r_line_lower:
                sev = "Low"

            if "mitigat" in r_line_lower:
                mit_parts = re.split(r"mitigat[a-z]*\s*(?:plan|by)?\s*[:\-]", r_line, flags=re.IGNORECASE)
                if len(mit_parts) > 1:
                    desc = mit_parts[0].strip()
                    mit = mit_parts[1].strip()

            risks.append(ExtractedRisk(
                description=desc,
                severity=sev,
                status=status,
                mitigation_plan=mit
            ))

        # Fallback: Parse risk counts from key-values
        crit_match = re.search(r"(?:Critical Risks|Critical)(?:[^:\n]*):\s*(\d+)", text, re.IGNORECASE)
        high_match = re.search(r"(?:High Risks|High)(?:[^:\n]*):\s*(\d+)", text, re.IGNORECASE)
        med_match = re.search(r"(?:Medium Risks|Medium)(?:[^:\n]*):\s*(\d+)", text, re.IGNORECASE)
        low_match = re.search(r"(?:Low Risks|Low)(?:[^:\n]*):\s*(\d+)", text, re.IGNORECASE)
        
        if (crit_match or high_match or med_match or low_match) and not risks:
            c_val = int(crit_match.group(1)) if crit_match else 0
            h_val = int(high_match.group(1)) if high_match else 0
            m_val = int(med_match.group(1)) if med_match else 0
            l_val = int(low_match.group(1)) if low_match else 0
            
            for i in range(c_val):
                risks.append(ExtractedRisk(description=f"Critical Risk {i+1}", severity="Critical", status="Open"))
            for i in range(h_val):
                risks.append(ExtractedRisk(description=f"High Risk {i+1}", severity="High", status="Open"))
            for i in range(m_val):
                risks.append(ExtractedRisk(description=f"Medium Risk {i+1}", severity="Medium", status="Open"))
            for i in range(l_val):
                risks.append(ExtractedRisk(description=f"Low Risk {i+1}", severity="Low", status="Open"))

        info["open_risks"] = risks if risks else None

        # 8. Blockers
        blocker_lines = get_section_lines("Blockers")
        if not blocker_lines:
            for line in text.split("\n"):
                if "blocker" in line.lower() or "blocked" in line.lower():
                    # Exclude the title or count lines like "Open Blockers: 15"
                    if ":" not in line or "open blockers" not in line.lower():
                        if line.count('|') < 2 and not line.strip().startswith('|'):
                            blocker_lines.append(line.strip(" *-•"))

        # Fallback: Parse blockers count from key-values
        blocker_count_match = re.search(r"(?:Open Blockers|Blockers|Critical Blockers)(?:[^:\n]*):\s*(\d+)", text, re.IGNORECASE)
        if blocker_count_match and not blocker_lines:
            b_count = int(blocker_count_match.group(1))
            blocker_lines = [f"Unresolved Blocker {i+1}" for i in range(b_count)]

        info["blockers"] = blocker_lines if blocker_lines else None

        # 9. Stakeholder Comments
        comment_lines = get_section_lines("Stakeholder Comments")
        if not comment_lines:
            comment_lines = get_section_lines("Comments")
        if not comment_lines:
            for line in text.split("\n"):
                if "comment" in line.lower() or "feedback" in line.lower():
                    if ":" not in line or "stakeholder" not in line.lower():
                        if line.count('|') < 2 and not line.strip().startswith('|'):
                            comment_lines.append(line.strip(" *-•"))
                        
        sentiment_match = re.search(r"(?:Stakeholder Sentiment|Sentiment|Customer Satisfaction|Client Confidence)(?:[^:\n]*):\s*([^\n\r]+)", text, re.IGNORECASE)
        if sentiment_match and not comment_lines:
            comment_lines = [f"{sentiment_match.group(0).split(':')[0].strip()}: {sentiment_match.group(1).strip()}"]

        info["stakeholder_comments"] = comment_lines if comment_lines else None

        # 10. Dependencies
        dep_lines = get_section_lines("Dependencies")
        if not dep_lines:
            for line in text.split("\n"):
                if "depend" in line.lower() and "dependency" not in line.lower():
                    if line.count('|') < 2 and not line.strip().startswith('|'):
                        dep_lines.append(line.strip(" *-•"))
                    
        dep_blocked_match = re.search(r"Dependencies Blocked(?:[^:\n]*):\s*([^\n\r]+)", text, re.IGNORECASE)
        if dep_blocked_match and not dep_lines:
            if "yes" in dep_blocked_match.group(1).lower():
                dep_lines = ["Critical project dependencies blocked"]

        info["dependencies"] = dep_lines if dep_lines else None

        # 11. Resource Availability
        res_match = re.search(r"(?:Resource Availability|Resources|Resource)(?:[^:\n]*):\s*([^\n\r]+)", text, re.IGNORECASE)
        if res_match:
            r_val = res_match.group(1).strip()
            # Support low availability percent trigger
            pct_res = re.search(r"(\d+)%", r_val)
            if pct_res:
                try:
                    p_val = int(pct_res.group(1))
                    if p_val < 80:
                        r_val = f"deficit - resource availability is low at {p_val}%"
                except Exception:
                    pass
            # Ignore if matched string is a table row
            if r_val.count('|') >= 2 or r_val.startswith('|'):
                r_val = None
            info["resource_availability"] = r_val
        else:
            res_lines = get_section_lines("Resources")
            info["resource_availability"] = "; ".join(res_lines) if res_lines else None

        return ExtractedProjectInfo(**info)
