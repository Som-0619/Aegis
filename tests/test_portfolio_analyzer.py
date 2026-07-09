"""
Unit tests for the PortfolioAnalyzer agent.
"""

import pytest
from agents.portfolio_analyzer import PortfolioAnalyzer, PortfolioTrendReport

def test_portfolio_analyzer_instantiation():
    """Verifies that PortfolioAnalyzer can be instantiated successfully."""
    analyzer = PortfolioAnalyzer()
    assert analyzer is not None

def test_portfolio_analysis_logic():
    """
    Tests portfolio aggregation and trend analysis on a mock dataset of
    multiple weekly reports across different projects.
    """
    analyzer = PortfolioAnalyzer()
    
    # Generate mock weekly reports for two projects
    mock_reports = [
        # Project A reports (latest and older)
        {
            "project_name": "Project Alpha",
            "report_date": "2026-07-03",
            "overall_status": "GREEN",
            "overall_score": 85.0,
            "scores": {"schedule": 90.0, "budget": 100.0, "milestones": 80.0, "risks": 100.0, "sentiment": 80.0, "resources": 100.0},
            "raw_extracted_data": {
                "project_name": "Project Alpha",
                "budget": 100000.0,
                "budget_spent": 50000.0,
                "milestones": [
                    {"name": "Database Schema Setup", "status": "Completed"},
                    {"name": "UI Wireframing", "status": "Delayed"}
                ],
                "blockers": ["Staging environment credential missing"],
                "stakeholder_comments": ["We are happy with the progress."]
            }
        },
        # Project B reports (YELLOW)
        {
            "project_name": "Project Beta",
            "report_date": "2026-07-03",
            "overall_status": "YELLOW",
            "overall_score": 70.0,
            "scores": {"schedule": 70.0, "budget": 60.0, "milestones": 50.0, "risks": 80.0, "sentiment": 60.0, "resources": 100.0},
            "raw_extracted_data": {
                "project_name": "Project Beta",
                "budget": 200000.0,
                "budget_spent": 220000.0,  # overrun
                "milestones": [
                    {"name": "Core Backend API", "status": "Delayed"},
                    {"name": "UI Integration", "status": "Delayed"}
                ],
                "blockers": ["Hardware shipment delayed at customs", "Credential key lost"],
                "stakeholder_comments": ["Concerned about vendor responsiveness."]
            }
        }
    ]

    # Run trend analysis
    report = analyzer.analyze_portfolio(mock_reports)
    
    assert isinstance(report, PortfolioTrendReport)
    
    # 1. Budget burn totals
    assert report.budget_burn_trends.total_portfolio_budget == 300000.0
    assert report.budget_burn_trends.total_portfolio_spent == 270000.0
    assert "90.0%" in report.budget_burn_trends.insights  # 270k / 300k = 90%
    assert report.budget_burn_trends.burn_rate_trajectory == "ACCELERATING" # > 75% spent
    
    # 2. Repeated delays
    assert len(report.repeated_milestone_delays) == 3  # UI Wireframing, Core Backend API, UI Integration
    assert any(x.milestone_name == "UI Wireframing" for x in report.repeated_milestone_delays)
    
    # 3. Blockers clustering
    assert len(report.common_blockers) == 2  # Access/Credentials, Hardware/Delivery
    assert any(x.blocker_type == "Access & Credentials Blocker" for x in report.common_blockers)
    # Check that Project Alpha and Project Beta are both in Access blocker (since both had "credential" blockers)
    access_blocker = next(x for x in report.common_blockers if x.blocker_type == "Access & Credentials Blocker")
    assert "Project Alpha" in access_blocker.affected_projects
    assert "Project Beta" in access_blocker.affected_projects

    # 4. At Risk projects
    assert len(report.projects_at_risk) == 1
    assert report.projects_at_risk[0].project_name == "Project Beta"
    assert report.projects_at_risk[0].rag_status == "YELLOW"
    
    # 5. Executive Insights
    assert len(report.executive_insights) >= 2
    assert "2 unique projects" in report.executive_insights[0]
