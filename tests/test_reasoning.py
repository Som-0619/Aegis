"""
Unit tests for the ReasoningAgent/Scoring Engine.
"""

import pytest
from agents.reasoning_agent import ReasoningAgent
from agents.information_extractor import ExtractedProjectInfo, ExtractedMilestone, ExtractedRisk

def test_reasoning_agent_instantiation():
    """Verifies that ReasoningAgent can be instantiated successfully."""
    agent = ReasoningAgent()
    assert agent is not None

def test_health_scoring_calculations():
    """Verifies that overall health status calculations output correct range scores and RAG status."""
    agent = ReasoningAgent()
    
    # Setup test mock ExtractedProjectInfo
    mock_data = ExtractedProjectInfo(
        project_name="Test Project",
        planned_start_date="2026-06-01",
        planned_end_date="2026-08-01",
        current_progress="30%",
        budget=10000.0,
        budget_spent=12000.0,  # overrun
        milestones=[
            ExtractedMilestone(name="Milestone A", due_date="2026-07-01", status="Completed", completion_percentage=100.0),
            ExtractedMilestone(name="Milestone B", due_date="2026-07-15", status="Delayed", completion_percentage=50.0)
        ],
        delayed_milestones=[
            ExtractedMilestone(name="Milestone B", due_date="2026-07-15", status="Delayed", completion_percentage=50.0)
        ],
        open_risks=[
            ExtractedRisk(description="Resource risk", severity="High", status="Open")
        ],
        blockers=["API key missing"],
        stakeholder_comments=["I am worried about the delays."],
        resource_availability="We have a shortage of staff."
    )
    
    results = agent.calculate_health_scores(mock_data)
    
    assert "overall_score" in results
    assert "rag_status" in results
    assert results["rag_status"] in ("GREEN", "YELLOW", "RED")
    assert "scores" in results
    assert "schedule" in results["scores"]
    assert "budget" in results["scores"]
    assert "milestones" in results["scores"]
    assert "risks" in results["scores"]
    assert "sentiment" in results["scores"]
    assert "resources" in results["scores"]

    # Verify scores are capped between 0 and 100
    for score in results["scores"].values():
        assert 0.0 <= score <= 100.0
