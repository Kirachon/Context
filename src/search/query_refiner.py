"""
Query Refinement utilities.

Provides small, deterministic refinement suggestions and ambiguity
resolution without external dependencies. Designed to be safe and
backward-compatible.
"""
from __future__ import annotations

from typing import List, Optional

from src.search.query_intent import QueryIntentClassifier, QueryIntentResult, QueryIntent
from src.search.query_enhancement import QueryEnhancer


class QueryRefiner:
    """Lightweight query refinement helper.

    - Uses existing QueryIntentClassifier and QueryEnhancer
    - Avoids heavy NLP deps; suggestions are rule-based and deterministic
    """

    def __init__(self):
        self._classifier = QueryIntentClassifier()
        self._enhancer = QueryEnhancer()

    def suggest_refinements(
        self,
        query: str,
        intent_result: Optional[QueryIntentResult] = None,
        session_context: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[str]:
        """Return up to top_k refined query variants.

        Strategy:
        - Add intent-specific hints (file type, directories, error terms)
        - Add minimal context snippets (last turn) when provided
        - Keep suggestions short and readable
        """
        intent_result = intent_result or self._classifier.classify(query)
        suggestions: List[str] = []

        ctx_suffix = ""
        if session_context:
            last = str(session_context[-1])[:60]
            ctx_suffix = f" (context: '{last}…')"

        base = query.strip()

        if intent_result.intent.name == "SEARCH":
            suggestions.append(f"{base} in src/ or tests/{ctx_suffix}")
            suggestions.append(f"{base} file:*.py or file:*.ts{ctx_suffix}")
            suggestions.append(f"{base} exact match only{ctx_suffix}")
        elif intent_result.intent.name == "DEBUG":
            suggestions.append(f"{base} include:traceback OR error OR exception{ctx_suffix}")
            suggestions.append(f"{base} recently changed files{ctx_suffix}")
        elif intent_result.intent.name == "UNDERSTAND":
            suggestions.append(f"{base} include:architecture OR design OR flow{ctx_suffix}")
            suggestions.append(f"{base} include:dependencies{ctx_suffix}")
        elif intent_result.intent.name == "OPTIMIZE":
            suggestions.append(f"{base} bottleneck:cpu OR memory{ctx_suffix}")
            suggestions.append(f"{base} include:profiling data{ctx_suffix}")
        elif intent_result.intent.name == "REFACTOR":
            suggestions.append(f"{base} prefer:readability OR maintainability{ctx_suffix}")
            suggestions.append(f"{base} suggest:pattern alternatives{ctx_suffix}")
        else:
            # Safe defaults
            suggestions.append(f"{base} narrow by path or file type{ctx_suffix}")

        # Always include an entity/pattern-aware enhanced variant as the last option
        enhanced = self._enhancer.enhance(
            base,
            intent_result,
            session_context=session_context,
            suggest_refinements=True,
        )
        suggestions.append(enhanced.enhanced_query)

        return suggestions[: max(1, min(top_k, 10))]

    def detect_ambiguities(
        self, query: str, intent_result: Optional[QueryIntentResult] = None
    ) -> List[str]:
        """Return clarifying questions indicating potential ambiguity."""
        intent_result = intent_result or self._classifier.classify(query)
        return self._enhancer.get_follow_up_questions(intent_result)

