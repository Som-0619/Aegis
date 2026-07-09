"""
Aegis Automated Execution Scheduler Service.
Provides automated triggers (Daily, Weekly, or Run-Once) to process incoming weekly project plans
located in the data/input directory using the WeeklyReportGenerator pipeline orchestrator.
"""

import os
import sys
import argparse
import logging
from typing import Dict, Any
from datetime import datetime

from agents.weekly_report_generator import WeeklyReportGenerator
from utils.file_utils import load_yaml

def setup_logging(log_file: str, log_level: str) -> logging.Logger:
    """Configures detailed execution logs to both file and stdout streams."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger = logging.getLogger("aegis_scheduler")
    logger.setLevel(log_level.upper())
    
    # Clear existing handlers to prevent duplicates or stale targets in tests
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File Handler
    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # Stream Handler
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    
    return logger

def run_pipeline_once(config: Dict[str, Any], logger: logging.Logger):
    """
    Scans the input folder, executes the audit pipeline for each detected project plan,
    and updates the historical databases.
    """
    logger.info("--------------------------------------------------------------------------------")
    logger.info("Initializing Aegis pipeline execution sweep.")
    input_dir = config.get("input_directory", "data/input")
    model_name = config.get("model_name", "gemini-2.5-flash")
    
    if not os.path.exists(input_dir):
        logger.error(f"Configured input directory '{input_dir}' does not exist. Exiting sweep.")
        return
        
    # Scan all files in input directory (ignoring hidden files)
    files = [f for f in os.listdir(input_dir) if not f.startswith(".")]
    if not files:
        logger.info("No incoming project plan files detected in the input directory. Sweep complete.")
        return
        
    logger.info(f"Detected {len(files)} files to audit: {files}")
    
    # Instantiating generator orchestrator
    try:
        generator = WeeklyReportGenerator(model_name=model_name)
    except Exception as e:
        logger.critical(f"Failed to initialize WeeklyReportGenerator orchestrator: {e}", exc_info=True)
        return

    success_count = 0
    fail_count = 0
    
    for filename in files:
        filepath = os.path.join(input_dir, filename)
        logger.info(f"Starting automated pipeline run for file: {filename}")
        
        try:
            result = generator.run_pipeline(filepath)
            logger.info(
                f"Successfully processed project: {result['project_name']} | "
                f"Status: {result['overall_status']} (Score: {result['overall_score']}/100) | "
                f"Confidence: {result['confidence_score']}%"
            )
            success_count += 1
        except Exception as e:
            # Gracefully log and continue with remaining files
            logger.error(f"Error auditing project plan '{filename}': {e}", exc_info=True)
            fail_count += 1
            
    logger.info(f"Sweep completed. Successfully compiled: {success_count}, Failed: {fail_count}")
    logger.info("--------------------------------------------------------------------------------")

def start_scheduler(mode: str, config: Dict[str, Any], logger: logging.Logger):
    """Initializes and runs the blocking scheduler for Daily or Weekly triggers."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore
    except ImportError:
        logger.critical("APScheduler package is not installed. Run: pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler()
    sched_cfg = config.get("schedule", {})
    
    if mode == "daily":
        daily_time = sched_cfg.get("daily_time", "08:00")
        try:
            hour, minute = map(int, daily_time.split(":"))
        except ValueError:
            logger.error(f"Invalid daily_time format: '{daily_time}'. Defaulting to 08:00.")
            hour, minute = 8, 0
            
        logger.info(f"Scheduling daily project sweep trigger at {hour:02d}:{minute:02d} every day.")
        scheduler.add_job(
            run_pipeline_once,
            'cron',
            hour=hour,
            minute=minute,
            args=[config, logger]
        )
        
    elif mode == "weekly":
        weekly_day = sched_cfg.get("weekly_day", "friday").lower()
        weekly_time = sched_cfg.get("weekly_time", "17:00")
        try:
            hour, minute = map(int, weekly_time.split(":"))
        except ValueError:
            logger.error(f"Invalid weekly_time format: '{weekly_time}'. Defaulting to 17:00.")
            hour, minute = 17, 0
            
        # Map string weekday to cron trigger weekdays
        day_map = {
            "monday": "mon", "tuesday": "tue", "wednesday": "wed",
            "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun"
        }
        cron_day = day_map.get(weekly_day, "fri")
        
        logger.info(f"Scheduling weekly project sweep trigger on {weekly_day} (cron: {cron_day}) at {hour:02d}:{minute:02d}.")
        scheduler.add_job(
            run_pipeline_once,
            'cron',
            day_of_week=cron_day,
            hour=hour,
            minute=minute,
            args=[config, logger]
        )
        
    logger.info("Aegis automated scheduler service is initializing. Press Ctrl+C to terminate.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Aegis scheduler service stopped manually.")

def main():
    parser = argparse.ArgumentParser(description="Aegis Project Health Scheduler Service CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-once", action="store_true", help="Process input folder immediately and exit.")
    group.add_argument("--weekly", action="store_true", help="Start service with a weekly cron trigger.")
    group.add_argument("--daily", action="store_true", help="Start service with a daily cron trigger.")
    parser.add_argument("--config", type=str, default="config/scheduler_config.yaml", help="Path to scheduler configuration yaml.")
    
    args = parser.parse_args()

    # Load configuration
    config_path = os.path.abspath(args.config)
    try:
        config = load_yaml(config_path)
    except Exception as e:
        print(f"Error loading configuration file '{config_path}': {e}. Using defaults.")
        config = {}

    # Setup Logging
    log_cfg = config.get("logging", {})
    log_file = log_cfg.get("log_file", "logs/scheduler.log")
    log_level = log_cfg.get("log_level", "INFO")
    logger = setup_logging(log_file, log_level)

    if args.run_once:
        logger.info("Running Aegis pipeline execution in immediate RUN-ONCE mode.")
        run_pipeline_once(config, logger)
    elif args.weekly:
        logger.info("Running Aegis pipeline execution in scheduled WEEKLY service mode.")
        start_scheduler("weekly", config, logger)
    elif args.daily:
        logger.info("Running Aegis pipeline execution in scheduled DAILY service mode.")
        start_scheduler("daily", config, logger)

if __name__ == "__main__":
    main()
