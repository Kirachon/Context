"""
Prompt Analysis & Intent Recognition (Story 3-2)

Analyzes natural language prompts to extract intent and context needs.
"""

import logging
from typing import Dict, Any

from src.search.query_intent import QueryIntentClassifier, QueryIntentResult

logger = logging.getLogger(__name__)


class PromptAnalyzer:
    """Thin wrapper reusing query intent classifier for generic prompts"""

    def __init__(self):
        self.classifier = QueryIntentClassifier()

    def analyze(self, prompt: str) -> Dict[str, Any]:
        """Analyze prompt and return structured intent & hints"""
        result: QueryIntentResult = self.classifier.classify(prompt)
        logger.debug(f"Prompt analyzed intent={result.intent} conf={result.confidence}")
        return {
            "intent": result.intent.value,
            "confidence": result.confidence,
            "scope": result.scope,
            "entities": result.entities,
            "keywords": result.keywords,
            "context_hints": result.context_hints,
        }


# Singleton
_prompt_analyzer: PromptAnalyzer = None


def get_prompt_analyzer() -> PromptAnalyzer:
    global _prompt_analyzer
    if _prompt_analyzer is None:
        _prompt_analyzer = PromptAnalyzer()
    return _prompt_analyzer

