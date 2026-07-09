"""
Configuration module for managing and loading LLM prompt templates.
Loads markdown/text prompt templates dynamically from the templates directory.
"""

import os
from typing import Dict
from utils.logger import get_logger

logger = get_logger(__name__)

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
    "prompts"
)

# Hardcoded default fallback templates if files are missing
FALLBACK_PROMPTS: Dict[str, str] = {
    "extraction": (
        "You are an information extraction agent. Extract structured milestones, "
        "tasks, risks, and financial metrics from the following text:\n\n{context}"
    ),
    "reasoning": (
        "You are a Project Management Office (PMO) director. Analyze the project "
        "health based on these details:\n\n{extracted_data}\n\nProvide risk "
        "assessments and recommendations."
    ),
    "trend_analysis": (
        "Analyze trends by comparing current project data with past status records:\n\n"
        "Current:\n{current_data}\n\nHistorical:\n{historical_data}"
    ),
    "rag_evaluation": (
        "Compare the generated report with the source documents and evaluate faithfulness.\n\n"
        "Source context:\n{source_context}\n\nReport content:\n{report_content}"
    )
}

class PromptLoader:
    """Utility class to load and cache prompts from the filesystem."""
    _cache: Dict[str, str] = {}

    @classmethod
    def get_prompt(cls, prompt_name: str) -> str:
        """
        Retrieves a prompt template by name. Reads from filesystem if available,
        otherwise returns a fallback template.
        
        Args:
            prompt_name: The base name of the template file (e.g. 'extraction', 'reasoning').
            
        Returns:
            The prompt template string.
        """
        # Strip extension if passed
        base_name = os.path.splitext(prompt_name)[0]
        
        if base_name in cls._cache:
            return cls._cache[base_name]

        # Try multiple extensions (e.g., .md, .txt)
        file_content = None
        for ext in (".md", ".txt"):
            filepath = os.path.join(TEMPLATES_DIR, f"{base_name}{ext}")
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        file_content = f.read()
                        logger.info(f"Loaded prompt template '{base_name}' from {filepath}")
                        break
                except Exception as e:
                    logger.error(f"Error reading prompt template file {filepath}: {e}")

        if file_content is not None:
            cls._cache[base_name] = file_content
            return file_content

        # Return fallback
        fallback = FALLBACK_PROMPTS.get(base_name, "Use this text: {context}")
        logger.warning(f"Prompt template '{base_name}' not found in filesystem. Using fallback.")
        cls._cache[base_name] = fallback
        return fallback

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the prompt cache."""
        cls._cache.clear()
        logger.debug("Prompt cache cleared.")
