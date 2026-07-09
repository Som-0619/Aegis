"""
Unit tests for the complete WeeklyReportGenerator pipeline orchestrator.
"""

import pytest
import os
from agents.weekly_report_generator import WeeklyReportGenerator
from utils.file_utils import load_json, read_text_file

def test_weekly_report_generator_instantiation():
    """Verifies that the orchestrator can be instantiated successfully."""
    generator = WeeklyReportGenerator()
    assert generator is not None

def test_pipeline_execution_txt_input(tmp_path):
    """
    Simulates a full pipeline run with a mock text input document.
    Verifies that all three core outputs (JSON, Markdown, PDF-ready Txt) are generated.
    """
    # Create output directory
    output_dir = tmp_path / "outputs"
    generator = WeeklyReportGenerator(output_dir=str(output_dir))
    
    # 1. Create a mock project raw text update
    input_file = tmp_path / "weekly_update.txt"
    input_content = """
    Project: Operation Shield
    Start Date: 2026-05-01
    End Date: 2026-10-01
    Progress: 35%
    Budget: 250000.00
    Spent: 120000.00
    Resource Availability: limited staffing in the core QA team.

    ### Milestones
    * Phase 1 Definition | 2026-06-01 | Completed
    * Core API Architecture | 2026-07-05 | Delayed

    ### Risks
    * Database replication lag | High | Open | mitigat-plan: configure write-through cache

    ### Blockers
    * Staging environment credentials not issued

    ### Stakeholder Comments
    * We are satisfied with the speed of backend developers.
    * Client is concerned with QA delay warnings.

    ### Dependencies
    * Integration API specifications from third-party vendor
    """
    
    input_file.write_text(input_content)
    
    # 2. Run Pipeline
    result = generator.run_pipeline(str(input_file))
    
    # 3. Verify execution results
    assert result["project_name"] == "Operation Shield"
    assert result["overall_status"] in ("GREEN", "YELLOW", "RED")
    assert result["confidence_score"] == 100.0  # All 13 fields are represented in text!
    assert "None. All parameters extracted" in result["missing_data"]
    assert "scores" in result
    assert "schedule" in result["scores"]
    
    # 4. Verify saved deliverables
    saved = result["saved_files"]
    assert os.path.exists(saved["markdown_report"])
    assert os.path.exists(saved["pdf_ready_text"])
    assert os.path.exists(saved["processed_json"])
    assert os.path.exists(saved["pptx_slides"])
    
    # Verify JSON content
    json_data = load_json(saved["processed_json"])
    assert json_data["project_name"] == "Operation Shield"
    assert "confidence_score" in json_data
    assert "scores" in json_data
    assert "schedule" in json_data["scores"]
    assert "raw_extracted_data" in json_data
    
    # Verify PDF-ready text content
    pdf_text = read_text_file(saved["pdf_ready_text"])
    assert "🛡️ AEGIS EXECUTIVE WEEKLY REPORT" in pdf_text
    assert "RAG Status:" in pdf_text
    assert "Confidence:   100.0%" in pdf_text
    assert "RECOMMENDATIONS" in pdf_text
    assert "CONFIDENTIAL - FOR PMO EXECUTIVE AUDIT ONLY" in pdf_text
