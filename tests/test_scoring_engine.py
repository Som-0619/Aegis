"""
Unit tests specifically for the deterministic Project Health Scoring Engine.
"""

import pytest
from datetime import datetime, timedelta
from agents.reasoning_agent import ReasoningAgent
from agents.information_extractor import ExtractedProjectInfo, ExtractedMilestone, ExtractedRisk
from utils.date_utils import format_date

def test_scoring_on_track_green():
    """Tests that a project with everything on track scores 100 and yields a GREEN status."""
    agent = ReasoningAgent()
    
    # 2 weeks ago start, 2 weeks from now end
    start_date = format_date(datetime.now() - timedelta(days=14))
    end_date = format_date(datetime.now() + timedelta(days=14))
    
    mock_data = ExtractedProjectInfo(
        project_name="Green Horizon",
        planned_start_date=start_date,
        planned_end_date=end_date,
        current_progress="50%",  # 50% elapsed, 50% progress -> no lag
        budget=100000.0,
        budget_spent=90000.0,  # under budget
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
    
    results = agent.calculate_health_scores(mock_data)
    
    assert results["rag_status"] == "GREEN"
    assert results["scores"]["schedule"] == 100.0
    assert results["scores"]["budget"] == 100.0
    assert results["scores"]["milestones"] == 100.0
    assert results["scores"]["risks"] == 100.0
    assert results["scores"]["resources"] == 100.0
    assert results["scores"]["sentiment"] == 90.0  # base 80 + 10 boost for "happy"
    assert results["overall_score"] >= 80.0

def test_scoring_delayed_red():
    """Tests that a heavily delayed and blocked project yields a RED status."""
    agent = ReasoningAgent()
    
    # 4 weeks ago start, 2 weeks ago end (should be 100% done)
    start_date = format_date(datetime.now() - timedelta(days=28))
    end_date = format_date(datetime.now() - timedelta(days=14))
    
    mock_data = ExtractedProjectInfo(
        project_name="Red Alert",
        planned_start_date=start_date,
        planned_end_date=end_date,
        current_progress="10%",  # 100% elapsed but only 10% progress -> major lag
        budget=100000.0,
        budget_spent=150000.0,  # 50% overrun
        milestones=[
            ExtractedMilestone(name="M1", status="Delayed"),
            ExtractedMilestone(name="M2", status="Delayed")
        ],
        delayed_milestones=[
            ExtractedMilestone(name="M1", status="Delayed"),
            ExtractedMilestone(name="M2", status="Delayed")
        ],
        open_risks=[
            ExtractedRisk(description="Critical risk", severity="Critical"),
            ExtractedRisk(description="High risk", severity="High")
        ],
        blockers=["Hardware issue", "Blocked by vendor"],
        stakeholder_comments=["We are very concerned and unhappy about this poor performance."],
        resource_availability="We have a tight resource deficit."
    )
    
    results = agent.calculate_health_scores(mock_data)
    
    assert results["rag_status"] == "RED"
    assert results["scores"]["schedule"] < 50.0
    assert results["scores"]["budget"] < 50.0
    assert results["scores"]["milestones"] == 0.0  # 100% delayed
    assert results["scores"]["risks"] == 15.0  # 100 - (2*25 blocker + 20 critical + 15 high) = 15
    assert results["scores"]["resources"] == 50.0  # base 100 - 50 deficit penalty
    assert results["scores"]["sentiment"] < 50.0  # heavily penalized for concerned, unhappy, poor

def test_scoring_empty_defaults():
    """Tests that an empty project model resolves to default safe scores instead of crashing."""
    agent = ReasoningAgent()
    mock_data = ExtractedProjectInfo()
    
    results = agent.calculate_health_scores(mock_data)
    
    assert results["rag_status"] == "GREEN"
    assert results["overall_score"] == 98.0  # base sentiment is 80 (weighted at 10%), rest are 100
    assert results["scores"]["schedule"] == 100.0
    assert results["scores"]["budget"] == 100.0
    assert results["scores"]["milestones"] == 100.0
    assert results["scores"]["risks"] == 100.0
    assert results["scores"]["resources"] == 100.0
    assert results["scores"]["sentiment"] == 80.0
