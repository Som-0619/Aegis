"""
Unit tests for the RAGEvaluator agent.
"""

import pytest
from agents.rag_evaluator import RAGEvaluator, EvaluationResult

def test_rag_evaluator_instantiation():
    """Verifies that RAGEvaluator can be instantiated successfully."""
    evaluator = RAGEvaluator()
    assert evaluator is not None

def test_rag_evaluator_mock_evaluation():
    """Verifies mock evaluation returns correct schema and passes verdict."""
    evaluator = RAGEvaluator()
    source_context = "Project Alpha is currently on budget."
    generated_report = "Project Alpha is on track and within budget boundaries."
    
    result = evaluator.evaluate_report(source_context, generated_report)
    assert isinstance(result, EvaluationResult)
    assert result.faithfulness_score >= 0.0
    assert result.faithfulness_score <= 1.0
    assert result.verdict in ("PASS", "FAIL")
