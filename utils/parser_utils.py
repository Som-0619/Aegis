"""
Utility functions for parsing structured data (JSON, markdown sections) from raw LLM text outputs.
"""

import re
import json
from typing import Any, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

def extract_json_block(text: str) -> Optional[str]:
    """
    Extracts a JSON block enclosed in markdown code fences ```json ... ``` or ``` ... ```.
    """
    # Try to find ```json ... ```
    json_block_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if json_block_match:
        return json_block_match.group(1).strip()
        
    # Try generic ``` ... ```
    generic_block_match = re.search(r"```\s*([\s\S]*?)\s*```", text)
    if generic_block_match:
        return generic_block_match.group(1).strip()
        
    # Check if the entire string might just be JSON
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
        
    return None

def parse_llm_json(text: str) -> Dict[str, Any]:
    """
    Extracts and parses a JSON dictionary from an LLM response.
    Returns an empty dict if parsing fails.
    """
    json_str = extract_json_block(text)
    if not json_str:
        # Try to find the first '{' and last '}'
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1:
            json_str = text[first_brace:last_brace+1]
            
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON string: {json_str}. Error: {e}")
            
    logger.warning("Could not find or parse any JSON from the LLM output.")
    return {}

def extract_markdown_section(text: str, section_title: str) -> str:
    """
    Extracts the content under a specific markdown heading (e.g. "## 5. PMO Risk Assessments & Reasoning").
    """
    # Regex to find the heading and read until the next heading of equal or higher level
    pattern = rf"(?:^|\n)(#+\s*{re.escape(section_title)}.*?)(?=\n#+ |\n*$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""
