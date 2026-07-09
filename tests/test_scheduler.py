"""
Unit tests for the Aegis Automated Execution Scheduler.
"""

import pytest
import os
import logging
from scheduler import setup_logging, run_pipeline_once

def test_setup_logging(tmp_path):
    """Verifies that the scheduler logger is constructed with handlers."""
    log_file = tmp_path / "logs" / "scheduler.log"
    logger = setup_logging(str(log_file), "INFO")
    
    assert logger is not None
    assert logger.name == "aegis_scheduler"
    assert len(logger.handlers) >= 1
    assert os.path.exists(str(log_file.parent))

def test_scheduler_run_once_empty(tmp_path):
    """Verifies that running the pipeline on an empty folder exits gracefully."""
    log_file = tmp_path / "logs" / "scheduler.log"
    logger = setup_logging(str(log_file), "INFO")
    
    mock_input_dir = tmp_path / "input"
    os.makedirs(mock_input_dir, exist_ok=True)
    
    config = {
        "input_directory": str(mock_input_dir),
        "model_name": "gemini-2.5-flash"
    }
    
    # Run sweep once (should find 0 files and exit cleanly)
    run_pipeline_once(config, logger)
    
    # Read log file to verify it logged successfully
    with open(str(log_file), "r") as f:
        log_content = f.read()
        
    assert "Initializing Aegis pipeline execution sweep." in log_content
    assert "No incoming project plan files detected" in log_content

def test_scheduler_run_once_with_file(tmp_path):
    """Verifies that running the pipeline on a mock status file processes it cleanly."""
    log_file = tmp_path / "logs" / "scheduler.log"
    logger = setup_logging(str(log_file), "INFO")
    
    mock_input_dir = tmp_path / "input"
    os.makedirs(mock_input_dir, exist_ok=True)
    
    # Write a mock file
    mock_file = mock_input_dir / "apollo.txt"
    mock_file.write_text("Project: Apollo\nStart Date: 2026-06-01\nEnd Date: 2026-10-01\nProgress: 40%\n")
    
    config = {
        "input_directory": str(mock_input_dir),
        "model_name": "gemini-2.5-flash"
    }
    
    # Execute the scheduler run-once function
    run_pipeline_once(config, logger)
    
    with open(str(log_file), "r") as f:
        log_content = f.read()
        
    assert "Detected 1 files to audit" in log_content
    assert "Successfully processed project: Apollo" in log_content
