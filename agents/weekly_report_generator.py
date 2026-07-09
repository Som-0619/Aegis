"""
Weekly Report Generator Orchestrator.
Coordinates reader, extractor, analyzer, reasoning agent, ppt generator, and evaluator to produce health reports.
Aligns with Phase 2 ExtractedProjectInfo, Phase 3 Scoring metrics, and Phase 4 Explanation narratives.
Exports JSON, Markdown, and formatted PDF-ready text.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from agents.document_reader import DocumentReader
from agents.information_extractor import InformationExtractor, ExtractedProjectInfo
from agents.trend_analyzer import TrendAnalyzer
from agents.reasoning_agent import ReasoningAgent
from agents.ppt_generator import PPTGenerator
from agents.rag_evaluator import RAGEvaluator
from utils.logger import get_logger
from utils.file_utils import read_text_file, write_text_file, save_json
from utils.date_utils import get_current_week_ending

logger = get_logger(__name__)

class WeeklyReportGenerator:
    """Orchestrates the entire AI reporting agent pipeline."""
    
    def __init__(self, output_dir: str = "outputs/weekly_reports", model_name: str = "gemini-2.5-flash"):
        self.output_dir = os.path.abspath(output_dir)
        self.reader = DocumentReader()
        self.extractor = InformationExtractor(model_name=model_name)
        self.analyzer = TrendAnalyzer()
        self.reasoner = ReasoningAgent(model_name=model_name)
        self.ppt_generator = PPTGenerator()
        self.evaluator = RAGEvaluator(model_name=model_name)
        logger.info("WeeklyReportGenerator orchestrator initialized.")

    def run_pipeline(self, input_filepath: str) -> Dict[str, Any]:
        """
        Executes the full pipeline:
        1. Read document text.
        2. Extract structured project info.
        3. Load history & analyze trends.
        4. Calculate health scores and generate PMO reasoning.
        5. Compile final markdown report.
        6. Run RAG faithfulness audit.
        7. Save outputs (markdown report, JSON data, slide presentations, PDF-ready text).
        
        Args:
            input_filepath: Path to the raw project update file.
            
        Returns:
            Dictionary containing output files path and QA results.
        """
        logger.info(f"Starting pipeline execution for file: {input_filepath}")
        
        # 1. Read file
        raw_text = self.reader.read_file(input_filepath)
        
        # 2. Extract structured data
        project_data: ExtractedProjectInfo = self.extractor.extract(raw_text)
        project_name_slug = (project_data.project_name or "unknown_project").lower().replace(" ", "_")
        report_date = get_current_week_ending()
        
        # Calculate confidence score and identify missing fields
        confidence_score, missing_data_text = self._calculate_confidence(project_data)
        
        # 3. Analyze trends
        historical_records = self.analyzer.load_historical_data(project_data.project_name or "unknown")
        trends_summary = self.analyzer.analyze_trends(project_data, historical_records)
        
        # 4. Calculate health scores and PMO reasoning
        scores = self.reasoner.calculate_health_scores(project_data)
        reasoning_outputs = self.reasoner.generate_reasoning_and_recommendations(
            project_data, scores, trends_summary
        )
        
        # 5. Build Markdown report compilation
        report_md = self._compile_markdown_report(
            project_data, scores, reasoning_outputs, trends_summary, 
            report_date, confidence_score, missing_data_text
        )
        
        # 6. Run QA Alignment audit
        qa_result = self.evaluator.evaluate_report(raw_text, report_md)
        
        # Append QA metadata details to markdown
        report_md = report_md.replace("{rag_faithfulness}", str(int(qa_result.faithfulness_score * 100)))
        report_md = report_md.replace("{rag_verdict}", qa_result.verdict)
        report_md = report_md.replace("{compiled_at}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Compile PDF-ready plain text
        pdf_ready_text = self._compile_pdf_ready_text(
            project_data, scores, reasoning_outputs, confidence_score, missing_data_text, report_date
        )
        
        # 7. Save outputs (JSON, Markdown, PDF-ready text, PPTX slides)
        saved_files = self._save_outputs(
            project_data, scores, report_md, pdf_ready_text, 
            project_name_slug, report_date, confidence_score, missing_data_text
        )
        
        # Return summary dictionary
        pipeline_result = {
            "project_name": project_data.project_name or "Unknown Project",
            "report_date": report_date,
            "overall_status": scores["rag_status"],
            "overall_score": scores["overall_score"],
            "confidence_score": confidence_score,
            "missing_data": missing_data_text,
            "scores": scores["scores"],
            "qa_verdict": qa_result.verdict,
            "qa_score": qa_result.faithfulness_score,
            "saved_files": saved_files
        }
        
        logger.info(f"Pipeline executed successfully. Results: {pipeline_result}")
        return pipeline_result

    def _calculate_confidence(self, data: ExtractedProjectInfo) -> tuple[float, str]:
        """Calculates confidence score (percentage of fields populated) and tracks missing fields."""
        field_configs = [
            ("Project Name", data.project_name),
            ("Planned Start Date", data.planned_start_date),
            ("Planned End Date", data.planned_end_date),
            ("Current Progress", data.current_progress),
            ("Budget", data.budget),
            ("Budget Spent", data.budget_spent),
            ("Milestones", data.milestones),
            ("Delayed Milestones", data.delayed_milestones),
            ("Open Risks", data.open_risks),
            ("Blockers", data.blockers),
            ("Stakeholder Comments", data.stakeholder_comments),
            ("Dependencies", data.dependencies),
            ("Resource Availability", data.resource_availability)
        ]
        
        present_count = sum(1 for name, val in field_configs if val is not None)
        confidence = round((present_count / len(field_configs)) * 100.0, 1)
        
        missing = [name for name, val in field_configs if val is None]
        missing_text = ", ".join(missing) if missing else "None. All parameters extracted successfully."
        
        logger.info(f"Confidence score calculated: {confidence}%. Missing fields: {len(missing)}")
        return confidence, missing_text

    def _compile_markdown_report(self, data: ExtractedProjectInfo, scores: Dict[str, Any], reasoning: Dict[str, str], trends: str, report_date: str, confidence: float, missing_data: str) -> str:
        """Assembles variables into the report template format."""
        template_path = os.path.join("templates", "report_template.md")
        if os.path.exists(template_path):
            template_content = read_text_file(template_path)
        else:
            logger.warning("Report template file not found, using raw markdown compiler fallback.")
            template_content = "# Project Health Report: {project_name}\nStatus: {overall_status}\nScore: {overall_score}"

        # Create markdown elements for milestones table
        milestones = data.milestones or []
        milestones_rows = []
        for m in milestones:
            milestones_rows.append(f"| {m.name or 'N/A'} | {m.due_date or 'N/A'} | {m.status or 'N/A'} | {m.completion_percentage or 0.0}% |")
        
        if not milestones_rows:
            milestones_table = "*No milestones found.*"
        else:
            milestones_table = "| Milestone Name | Due Date | Status | Progress |\n| :--- | :---: | :---: | :---: |\n" + "\n".join(milestones_rows)

        blockers = data.blockers or []
        blockers_text = ", ".join(blockers) if blockers else "None noted."
        
        deps = data.dependencies or []
        dependencies_text = ", ".join(deps) if deps else "None noted."
        
        resource_status_text = data.resource_availability or "Adequate staffing."

        categories = scores["scores"]
        rag_status = scores["rag_status"]
        
        def get_desc_status(val: float) -> str:
            if val >= 80: return "GREEN"
            if val >= 50: return "YELLOW"
            return "RED"

        compiled_md = template_content.format(
            project_name=data.project_name or "Unnamed Project",
            report_date=report_date,
            overall_status=rag_status,
            overall_score=scores["overall_score"],
            confidence_score=confidence,
            missing_data_text=missing_data,
            executive_summary=f"Project {data.project_name or 'Unnamed'} health is calculated as {rag_status} (score {scores['overall_score']}/100) with {confidence}% data confidence.",
            
            schedule_status=get_desc_status(categories["schedule"]),
            schedule_score=categories["schedule"],
            schedule_comments=f"Progress rate tracked at '{data.current_progress or 'N/A'}'. Start: {data.planned_start_date or 'N/A'}, End: {data.planned_end_date or 'N/A'}.",
            
            budget_status=get_desc_status(categories["budget"]),
            budget_score=categories["budget"],
            budget_comments=f"Planned: ${data.budget:,.2f}" if data.budget else "Planned: N/A" + f", Spent: ${data.budget_spent:,.2f}" if data.budget_spent else ", Spent: N/A",
            
            milestones_status=get_desc_status(categories["milestones"]),
            milestones_score=categories["milestones"],
            milestones_comments=f"{len(data.delayed_milestones or [])} milestones are delayed.",
            
            risks_status=get_desc_status(categories["risks"]),
            risks_score=categories["risks"],
            risks_comments=f"{len(data.open_risks or [])} active risks and {len(blockers)} blocker items.",
            
            sentiment_status=get_desc_status(categories["sentiment"]),
            sentiment_score=categories["sentiment"],
            sentiment_comments=f"Sentiment score derived from {len(data.stakeholder_comments or [])} stakeholder comments.",
            
            resources_status=get_desc_status(categories["resources"]),
            resources_score=categories["resources"],
            resources_comments=f"Resource availability status: '{data.resource_availability or 'N/A'}'.",
            
            milestones_table=milestones_table,
            blockers_text=blockers_text,
            dependencies_text=dependencies_text,
            resource_status_text=resource_status_text,
            trends_section=trends,
            pmo_reasoning=reasoning["pmo_reasoning"],
            recommendations=reasoning["recommendations"],
            
            rag_faithfulness="{rag_faithfulness}",
            rag_verdict="{rag_verdict}",
            compiled_at="{compiled_at}"
        )
        return compiled_md

    def _compile_pdf_ready_text(self, data: ExtractedProjectInfo, scores: Dict[str, Any], reasoning: Dict[str, str], confidence: float, missing_data: str, report_date: str) -> str:
        """Generates a structured, cleanly margins typewriter-like plain text layout for PDF export."""
        border = "=" * 80
        thin_border = "-" * 80
        
        def center(text: str) -> str:
            return text.center(80)

        lines = [
            border,
            center("🛡️ AEGIS EXECUTIVE WEEKLY REPORT"),
            center(f"Project Name: {data.project_name or 'Unnamed Project'}"),
            center(f"Date:         {report_date}"),
            border,
            "",
            f"  Project Name: {data.project_name or 'Unnamed Project'}",
            f"  Date:         {report_date}",
            f"  RAG Status:   {scores['rag_status']} (Weighted Score: {scores['overall_score']}/100)",
            f"  Confidence:   {confidence}%",
            f"  Missing Data: {missing_data}",
            "",
            thin_border,
            center("1. METRIC CATEGORY SCOREBOARD"),
            thin_border,
        ]
        
        cats = scores["scores"]
        for cat, val in cats.items():
            status = "GREEN" if val >= 80 else "YELLOW" if val >= 50 else "RED"
            lines.append(f"  * {cat.upper().ljust(15)}: {str(val).rjust(5)}/100  [{status}]")
            
        lines.extend([
            "",
            thin_border,
            center("2. SUMMARY"),
            thin_border,
            f"Project {data.project_name or 'Unnamed'} health is calculated as {scores['rag_status']} (score {scores['overall_score']}/100) with {confidence}% data confidence.",
            "",
            thin_border,
            center("3. REASONING"),
            thin_border,
            reasoning["pmo_reasoning"],
            "",
            thin_border,
            center("4. RECOMMENDATIONS"),
            thin_border,
            reasoning["recommendations"],
            "",
            thin_border,
            center("5. PROJECT DETAILS & METADATA"),
            thin_border,
            f"  * Planned Timeline   : Start: {data.planned_start_date or 'N/A'}  |  End: {data.planned_end_date or 'N/A'}",
            f"  * Current Progress   : {data.current_progress or 'N/A'}",
            f"  * Financial Status   : Budget: ${data.budget:,.2f}" if data.budget else "  * Financial Status   : Budget: N/A" + f"  |  Spent: ${data.budget_spent:,.2f}" if data.budget_spent else "  |  Spent: N/A",
            f"  * Dependencies       : {', '.join(data.dependencies) if data.dependencies else 'None noted.'}",
            f"  * Resource Status    : {data.resource_availability or 'N/A'}",
            "",
            border,
            center("CONFIDENTIAL - FOR PMO EXECUTIVE AUDIT ONLY"),
            border
        ])
        
        return "\n".join(lines)

    def _save_outputs(self, data: ExtractedProjectInfo, scores: Dict[str, Any], report_md: str, pdf_ready_text: str, project_slug: str, report_date: str, confidence: float, missing_data: str) -> Dict[str, str]:
        """Saves generated documents (JSON database, Markdown, plain text PDF-ready) to output folders."""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 1. Save Markdown report
        md_filename = f"{project_slug}_report_{report_date}.md"
        md_filepath = os.path.join(self.output_dir, md_filename)
        write_text_file(md_filepath, report_md)

        # 2. Save PDF-ready plain text
        txt_filename = f"{project_slug}_report_{report_date}_pdf_ready.txt"
        txt_filepath = os.path.join(self.output_dir, txt_filename)
        write_text_file(txt_filepath, pdf_ready_text)

        # 3. Save JSON file to weekly reports folder (for user download) and to processed history DB
        json_filename = f"{project_slug}_data_{report_date}.json"
        
        # Build consolidated output payload
        json_payload = {
            "project_name": data.project_name or "Unnamed Project",
            "report_date": report_date,
            "overall_status": scores["rag_status"],
            "overall_score": scores["overall_score"],
            "confidence_score": confidence,
            "missing_data": missing_data,
            "scores": scores["scores"],
            "raw_extracted_data": data.model_dump()
        }
        
        # Save to weekly reports folder
        json_filepath = os.path.join(self.output_dir, json_filename)
        save_json(json_filepath, json_payload)

        # Save to processed history DB
        processed_dir = os.path.join("data", "processed")
        processed_filepath = os.path.join(processed_dir, json_filename)
        save_json(processed_filepath, json_payload)
        
        # 4. Save Slide Presentation
        ppt_dir = os.path.join("outputs", "presentations")
        ppt_filename = f"{project_slug}_slides_{report_date}.pptx"
        ppt_filepath = os.path.join(ppt_dir, ppt_filename)
        self.ppt_generator.generate_presentation(
            json_payload,
            ppt_filepath
        )

        return {
            "markdown_report": md_filepath,
            "pdf_ready_text": txt_filepath,
            "processed_json": json_filepath,
            "pptx_slides": ppt_filepath
        }
