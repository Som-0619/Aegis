"""
File operation utilities for reading/writing YAML, JSON, text, and markdown files safely.
"""

import os
import json
import yaml
from typing import Any, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

def read_text_file(filepath: str) -> str:
    """Reads and returns the contents of a text file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read text file {filepath}: {e}")
        raise

def write_text_file(filepath: str, content: str) -> None:
    """Writes content to a text file, creating parent directories if they don't exist."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Successfully wrote text file to {filepath}")
    except Exception as e:
        logger.error(f"Failed to write text file {filepath}: {e}")
        raise

def load_yaml(filepath: str) -> Dict[str, Any]:
    """Loads and parses a YAML file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data or {}
    except Exception as e:
        logger.error(f"Failed to load YAML file {filepath}: {e}")
        raise

def save_yaml(filepath: str, data: Dict[str, Any]) -> None:
    """Saves a dictionary as a YAML file."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Successfully saved YAML to {filepath}")
    except Exception as e:
        logger.error(f"Failed to save YAML file {filepath}: {e}")
        raise

def load_json(filepath: str) -> Any:
    """Loads and parses a JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON file {filepath}: {e}")
        raise

def save_json(filepath: str, data: Any, indent: int = 4) -> None:
    """Saves data to a JSON file."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        logger.info(f"Successfully saved JSON to {filepath}")
    except Exception as e:
        logger.error(f"Failed to save JSON file {filepath}: {e}")
        raise
