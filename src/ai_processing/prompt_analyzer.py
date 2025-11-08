"""
Prompt Analysis & Intent Recognition (Story 3-2)

Analyzes natural language prompts to extract intent and context needs.
"""

import logging
from typing import Dict, Any

from src.search.query_intent import QueryIntentClassifier, QueryIntentResult
from src.config.settings import settings
from src.ai_processing.nlp_analyzer import get_nlp_analyzer

logger = logging.getLogger(__name__)


class PromptAnalyzer:
    """Thin wrapper reusing query intent classifier for generic prompts"""

    def __init__(self):
        self.classifier = QueryIntentClassifier()

    def analyze(self, prompt: str, use_nlp: bool = False, session_id: str | None = None) -> Dict[str, Any]:
        """Analyze prompt and return structured intent & hints.

        Parameters:
            prompt: Text to analyze
            use_nlp: When True (or when settings.enable_nlp_analysis), include additive NLP analysis
                     under the 'nlp' key. Backward compatible; existing keys unchanged.
            session_id: Optional conversation session id to include recent history (additive)
        """
        result: QueryIntentResult = self.classifier.classify(prompt)
        logger.debug(f"Prompt analyzed intent={result.intent} conf={result.confidence}")
        out: Dict[str, Any] = {
            "intent": result.intent.value,
            "confidence": result.confidence,
            "scope": result.scope,
            "entities": result.entities,
            "keywords": result.keywords,
            "context_hints": result.context_hints,
        }

        # Optional additive NLP analysis (non-breaking)
        if use_nlp or settings.enable_nlp_analysis:
            try:
                nlp = get_nlp_analyzer().analyze_text(prompt)
                out["nlp"] = nlp
            except Exception as e:
                logger.info("NLP analysis skipped due to error: %s", e)

        # Optional conversation context (non-breaking)
        if session_id:
            try:
                from src.ai_processing.conversation_tracker import get_conversation_tracker

                tracker = get_conversation_tracker()
                out["conversation"] = tracker.history(session_id)
            except Exception:
                pass
        return out


# Singleton
_prompt_analyzer: PromptAnalyzer = None


def get_prompt_analyzer() -> PromptAnalyzer:
    global _prompt_analyzer
    if _prompt_analyzer is None:
        _prompt_analyzer = PromptAnalyzer()
    return _prompt_analyzer
