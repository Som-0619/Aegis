"""
Unit tests for the InformationExtractor agent.
"""

import pytest
from agents.information_extractor import InformationExtractor, ExtractedProjectInfo

def test_information_extractor_instantiation():
    """Verifies that InformationExtractor can be instantiated successfully."""
    extractor = InformationExtractor()
    assert extractor is not None

def test_rule_based_extract_full_data():
    """Verifies parsing of a fully populated project update document."""
    extractor = InformationExtractor()
    raw_document = """
    Project: Project Alpha
    Start Date: 2026-06-01
    End Date: 2026-09-01
    Progress: 45%
    Budget: 150000.00
    Spent: 45000.00
    Resource Availability: adequate staffing levels.

    ### Milestones
    * Phase 1 Kickoff | 2026-06-05 | Completed
    * Design Review | 2026-07-15 | Delayed

    ### Risks
    * Vendor delays | High | Open | mitigat-plan: contact secondary vendor

    ### Blockers
    * Hardware delivery delayed at custom checks

    ### Stakeholder Comments
    * We are satisfied with the current progression.
    * John is concerned about the hardware shipment blocker.

    ### Dependencies
    * Cloud infrastructure setup
    """
    
    info = extractor.extract(raw_document)
    
    assert isinstance(info, ExtractedProjectInfo)
    assert info.project_name == "Project Alpha"
    assert info.planned_start_date == "2026-06-01"
    assert info.planned_end_date == "2026-09-01"
    assert info.current_progress == "45%"
    assert info.budget == 150000.0
    assert info.budget_spent == 45000.0
    assert info.resource_availability == "adequate staffing levels."
    
    # Verify lists
    assert len(info.milestones) == 2
    assert info.milestones[0].status == "Completed"
    assert info.milestones[1].status == "Delayed"
    assert len(info.delayed_milestones) == 1
    assert info.delayed_milestones[0].name == "Design Review"
    
    assert len(info.open_risks) == 1
    assert info.open_risks[0].severity == "High"
    
    assert len(info.blockers) == 1
    assert "Hardware delivery delayed" in info.blockers[0]
    
    assert len(info.stakeholder_comments) == 2
    assert "satisfied" in info.stakeholder_comments[0]
    assert "concerned" in info.stakeholder_comments[1]
    
    assert len(info.dependencies) == 1
    assert info.dependencies[0] == "Cloud infrastructure setup"

def test_rule_based_extract_missing_data():
    """Verifies that missing values are correctly returned as None (null in JSON)."""
    extractor = InformationExtractor()
    raw_document = """
    Project: Project Beta
    Progress: 10%
    """
    
    info = extractor.extract(raw_document)
    
    assert info.project_name == "Project Beta"
    assert info.current_progress == "10%"
    assert info.planned_start_date is None
    assert info.planned_end_date is None
    assert info.budget is None
    assert info.budget_spent is None
    assert info.milestones is None
    assert info.open_risks is None
    assert info.blockers is None
    assert info.stakeholder_comments is None
    assert info.dependencies is None
    assert info.resource_availability is None
