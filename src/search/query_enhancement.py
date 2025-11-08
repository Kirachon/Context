"""
Query Enhancement Engine (Story 2.6)

Enhances user queries with relevant context from codebase analysis,
recent changes, and detected patterns.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from src.search.query_intent import QueryIntentResult, QueryIntent


@dataclass
class EnhancedQuery:
    """Enhanced query with additional context"""

    original_query: str
    enhanced_query: str
    context_additions: List[str]  # what was added
    confidence: float


class QueryEnhancer:
    """Enhances queries with relevant context"""

    def __init__(self, dependency_analyzer=None, pattern_detector=None):
        """
        Initialize query enhancer

        Args:
            dependency_analyzer: DependencyAnalyzer instance (optional)
            pattern_detector: Pattern detector instance (optional)
        """
        self.dependency_analyzer = dependency_analyzer
        self.pattern_detector = pattern_detector
        self.recent_changes: List[str] = []
        self.common_patterns: Dict[str, List[str]] = {}

    def enhance(
        self,
        query: str,
        intent_result: QueryIntentResult,
        recent_files: Optional[List[str]] = None,
        project_patterns: Optional[Dict[str, Any]] = None,
        session_context: Optional[List[str]] = None,  # NEW optional additive context
        suggest_refinements: bool = False,  # NEW flag (non-breaking)
    ) -> EnhancedQuery:
        """
        Enhance query with relevant context

        Args:
            query: Original query
            intent_result: Intent classification result
            recent_files: Recently modified files (optional)
            project_patterns: Detected project patterns (optional)
            session_context: Optional list of prior messages or queries to include (additive)
            suggest_refinements: When True, annotate enhanced query to indicate refinement flow

        Returns:
            EnhancedQuery with enhanced query and context additions
        """
        context_additions = []
        enhanced_parts = [query]

        # Add entity context
        if intent_result.entities:
            entity_context = self._get_entity_context(intent_result.entities)
            if entity_context:
                enhanced_parts.append(f"(related to: {entity_context})")
                context_additions.append(f"entity_context: {entity_context}")

        # Add recent changes context
        if recent_files:
            recent_context = self._get_recent_context(recent_files, intent_result)
            if recent_context:
                enhanced_parts.append(f"(recent changes: {recent_context})")
                context_additions.append(f"recent_context: {recent_context}")

        # Add pattern context
        if project_patterns:
            pattern_context = self._get_pattern_context(project_patterns, intent_result)
            if pattern_context:
                enhanced_parts.append(f"(patterns: {pattern_context})")
                context_additions.append(f"pattern_context: {pattern_context}")

        # Add conversation/session context (last turn only to keep it concise)
        if session_context:
            last_turn = str(session_context[-1])[:120]
            enhanced_parts.append(f"(context: prev='{last_turn}…')")
            context_additions.append("session_context:last_turn")

        # Add intent-specific context
        intent_context = self._get_intent_context(intent_result.intent)
        if intent_context:
            enhanced_parts.append(f"({intent_context})")
            context_additions.append(f"intent_context: {intent_context}")

        # Optional marker to signal refinement flow (no semantic change)
        if suggest_refinements:
            context_additions.append("refinement_flow:enabled")

        enhanced_query = " ".join(enhanced_parts)
        confidence = min(1.0, 0.7 + len(context_additions) * 0.05)

        return EnhancedQuery(
            original_query=query,
            enhanced_query=enhanced_query,
            context_additions=context_additions,
            confidence=confidence,
        )

    def _get_entity_context(self, entities: List[str]) -> str:
        """Get context about extracted entities"""
        if not entities:
            return ""
        return ", ".join(entities[:3])

    def _get_recent_context(
        self, recent_files: List[str], intent_result: QueryIntentResult
    ) -> str:
        """Get context from recently modified files"""
        if not recent_files:
            return ""

        # Filter recent files by scope
        if intent_result.scope.level == "file" and intent_result.scope.target:
            relevant = [f for f in recent_files if intent_result.scope.target in f]
        else:
            relevant = recent_files[:3]

        return ", ".join(relevant) if relevant else ""

    def _get_pattern_context(
        self, patterns: Dict[str, Any], intent_result: QueryIntentResult
    ) -> str:
        """Get context from detected patterns"""
        if not patterns:
            return ""

        # Extract relevant pattern names
        pattern_names = list(patterns.keys())[:2]
        return ", ".join(pattern_names) if pattern_names else ""

    def _get_intent_context(self, intent: QueryIntent) -> str:
        """Get context based on query intent"""
        intent_hints = {
            QueryIntent.SEARCH: "focus on relevance and coverage",
            QueryIntent.UNDERSTAND: "include structure and relationships",
            QueryIntent.REFACTOR: "consider code quality metrics",
            QueryIntent.DEBUG: "include error patterns and stack traces",
            QueryIntent.OPTIMIZE: "include performance metrics",
            QueryIntent.IMPLEMENT: "include similar implementations",
            QueryIntent.DOCUMENT: "include docstring examples",
        }
        return intent_hints.get(intent, "")

    def add_recent_change(self, file_path: str):
        """Track recently modified file"""
        self.recent_changes.insert(0, file_path)
        self.recent_changes = self.recent_changes[:20]  # Keep last 20

    def add_pattern(self, pattern_name: str, examples: List[str]):
        """Track detected pattern"""
        self.common_patterns[pattern_name] = examples

    def get_follow_up_questions(self, intent_result: QueryIntentResult) -> List[str]:
        """Generate follow-up questions to refine search"""
        questions = []

        if intent_result.intent == QueryIntent.SEARCH:
            questions.append("Would you like to filter by file type or directory?")
            questions.append("Should I include similar patterns or exact matches only?")
        elif intent_result.intent == QueryIntent.UNDERSTAND:
            questions.append(
                "Would you like to see the full implementation or just the interface?"
            )
            questions.append("Should I include related dependencies?")
        elif intent_result.intent == QueryIntent.REFACTOR:
            questions.append(
                "What's your priority: readability, performance, or maintainability?"
            )
            questions.append("Should I suggest alternative patterns?")
        elif intent_result.intent == QueryIntent.DEBUG:
            questions.append("Do you have error messages or stack traces?")
            questions.append("Should I look for similar issues in the codebase?")
        elif intent_result.intent == QueryIntent.OPTIMIZE:
            questions.append("What's the current performance bottleneck?")
            questions.append("Are you optimizing for speed, memory, or both?")

        return questions[:2]  # Return top 2 questions
