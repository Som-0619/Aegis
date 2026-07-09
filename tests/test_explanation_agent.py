"""
Unit tests specifically for the AIExplanationAgent.
"""

import pytest
from agents.reasoning_agent import AIExplanationAgent
from agents.information_extractor import ExtractedProjectInfo, ExtractedMilestone, ExtractedRisk

def test_explanation_agent_instantiation():
    """Verifies that AIExplanationAgent can be instantiated successfully."""
    agent = AIExplanationAgent()
    assert agent is not None

def test_explanation_generation_on_track():
    """Verifies rule-based explanation on on-track project details."""
    agent = AIExplanationAgent()
    mock_data = ExtractedProjectInfo(
        project_name="Green Horizon",
        planned_start_date="2026-06-01",
        planned_end_date="2026-08-01",
        current_progress="50%",
        budget=100000.0,
        budget_spent=90000.0,
        milestones=[
            ExtractedMilestone(name="M1", status="Completed"),
            ExtractedMilestone(name="M2", status="In Progress")
        ],
        delayed_milestones=[],
        open_risks=[],
        blockers=[],
        stakeholder_comments=["The client is happy with the results."],
        resource_availability="Adequate resources available."
    )
    
    scores = {
        "scores": {
            "schedule": 100.0,
            "budget": 100.0,
            "milestones": 100.0,
            "risks": 100.0,
            "sentiment": 90.0,
            "resources": 100.0
        },
        "overall_score": 99.0,
        "rag_status": "GREEN"
    }
    
    outputs = agent.generate_explanation(mock_data, scores)
    
    assert "pmo_reasoning" in outputs
    assert "recommendations" in outputs
    
    narrative = outputs["pmo_reasoning"]
    # Check that it covers all 5 mandated keywords/areas
    assert "schedule" in narrative.lower()
    assert "budget" in narrative.lower()
    assert "milestones" in narrative.lower()
    assert "risk" in narrative.lower()
    assert "sentiment" in narrative.lower() or "stakeholder" in narrative.lower()
    
    # Since all fields are present, there should be no uncertainty notices
    assert "Uncertainty" not in narrative

def test_explanation_generation_missing_data_warnings():
    """Verifies that missing parameters yield explicit data integrity warnings."""
    agent = AIExplanationAgent()
    
    # Missing dates, budget, milestones, risks, and resource fields
    mock_data = ExtractedProjectInfo(
        project_name="Uncertain Project",
        current_progress="50%"
    )
    
    scores = {
        "scores": {
            "schedule": 100.0,
            "budget": 100.0,
            "milestones": 100.0,
            "risks": 100.0,
            "sentiment": 80.0,
            "resources": 100.0
        },
        "overall_score": 98.0,
        "rag_status": "GREEN"
    }
    
    outputs = agent.generate_explanation(mock_data, scores)
    
    narrative = outputs["pmo_reasoning"]
    
    # Check that it alerts the user to missing parameters
    assert "Uncertainty:" in narrative
    assert "Planned start/end dates" in narrative or "dates" in narrative
    assert "Financial metrics" in narrative or "budget" in narrative
    assert "Milestone" in narrative
    assert "Risk" in narrative
