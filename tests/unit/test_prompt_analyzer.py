"""
Unit tests for Prompt Analyzer (Story 3-2)
"""
import pytest
from src.ai_processing.prompt_analyzer import PromptAnalyzer


def test_prompt_analyzer_basic():
    analyzer = PromptAnalyzer()
    result = analyzer.analyze("Find usages of function foo in repo")
    assert "intent" in result
    assert "confidence" in result

