"""
Query Intent Classification (Story 2.6)

Classifies user queries to understand intent and extract relevant context.
Supports multiple intent types: search, refactor, understand, debug, optimize.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any
import re


class QueryIntent(str, Enum):
    """Types of query intents"""
    SEARCH = "search"           # Find code matching criteria
    UNDERSTAND = "understand"   # Learn about code structure/behavior
    REFACTOR = "refactor"       # Improve code quality
    DEBUG = "debug"             # Find bugs or issues
    OPTIMIZE = "optimize"       # Improve performance
    IMPLEMENT = "implement"     # Add new functionality
    DOCUMENT = "document"       # Generate documentation
    UNKNOWN = "unknown"


@dataclass
class QueryScope:
    """Scope of query (file, module, codebase)"""
    level: str  # "file", "module", "codebase"
    target: Optional[str] = None  # specific file/module name


@dataclass
class QueryIntentResult:
    """Result of intent classification"""
    intent: QueryIntent
    confidence: float  # 0.0-1.0
    scope: QueryScope
    entities: List[str]  # extracted entities (function names, class names, etc.)
    keywords: List[str]  # key terms from query
    context_hints: Dict[str, Any]  # additional context


class QueryIntentClassifier:
    """Classifies query intent using pattern matching and heuristics"""

    def __init__(self):
        """Initialize classifier with intent patterns"""
        self.intent_patterns = {
            QueryIntent.SEARCH: [
                r'\b(find|search|locate|where|show|list|get)\b',
                r'\b(all|any|matching|containing|with)\b',
            ],
            QueryIntent.DEBUG: [
                r'\b(bug|error|issue|problem|fix|crash|fail|break|null pointer|exception)\b',
                r'\b(debug|trace|why.*crash|why.*fail|why.*error)\b',
            ],
            QueryIntent.UNDERSTAND: [
                r'\b(explain|understand|how|what|describe|tell)\b',
                r'\b(works|does|is|structure|architecture|flow)\b',
            ],
            QueryIntent.REFACTOR: [
                r'\b(refactor|improve|clean|simplify|optimize|restructure)\b',
                r'\b(code|quality|readability|maintainability)\b',
            ],
            QueryIntent.OPTIMIZE: [
                r'\b(optimize|performance|speed|fast|slow|efficient)\b',
                r'\b(improve|reduce|minimize|maximize)\b',
            ],
            QueryIntent.IMPLEMENT: [
                r'\b(implement|add|create|build|write|make)\b',
                r'\b(new|feature|function|method|class)\b',
            ],
            QueryIntent.DOCUMENT: [
                r'\b(document|comment|explain|describe|docstring)\b',
                r'\b(documentation|readme|guide|tutorial)\b',
            ],
        }

    def classify(self, query: str) -> QueryIntentResult:
        """
        Classify query intent and extract context

        Args:
            query: User query string

        Returns:
            QueryIntentResult with intent, confidence, and extracted context
        """
        query_lower = query.lower()

        # Score each intent with weighted patterns
        intent_scores: Dict[QueryIntent, float] = {}
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            for i, pattern in enumerate(patterns):
                matches = len(re.findall(pattern, query_lower))
                # First pattern is more important (weight 0.6), second is 0.4
                weight = 0.6 if i == 0 else 0.4
                score += matches * weight
            intent_scores[intent] = min(score, 1.0)

        # Get top intent
        top_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[top_intent]

        # If no clear intent, mark as unknown
        if confidence < 0.3:
            top_intent = QueryIntent.UNKNOWN
            confidence = 0.0
        
        # Extract scope
        scope = self._extract_scope(query_lower)
        
        # Extract entities (function/class names)
        entities = self._extract_entities(query)
        
        # Extract keywords
        keywords = self._extract_keywords(query_lower)
        
        # Extract context hints
        context_hints = self._extract_context_hints(query_lower, top_intent)
        
        return QueryIntentResult(
            intent=top_intent,
            confidence=confidence,
            scope=scope,
            entities=entities,
            keywords=keywords,
            context_hints=context_hints
        )

    def _extract_scope(self, query: str) -> QueryScope:
        """Extract query scope (file, module, codebase)"""
        if re.search(r'\b(this file|current file|file)\b', query):
            return QueryScope(level="file")
        elif re.search(r'\b(module|package|namespace)\b', query):
            return QueryScope(level="module")
        else:
            return QueryScope(level="codebase")

    def _extract_entities(self, query: str) -> List[str]:
        """Extract code entities (function/class names) from query"""
        # Match CamelCase and snake_case identifiers
        entities = re.findall(r'\b([A-Z][a-zA-Z0-9]*|[a-z_][a-z0-9_]*)\b', query)
        # Filter out common words
        common_words = {'the', 'and', 'or', 'in', 'is', 'to', 'for', 'of', 'a', 'an'}
        return [e for e in entities if e.lower() not in common_words][:5]

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract key terms from query"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        words = query.split()
        return [w for w in words if w.lower() not in stop_words and len(w) > 2][:10]

    def _extract_context_hints(self, query: str, intent: QueryIntent) -> Dict[str, Any]:
        """Extract additional context hints based on intent"""
        hints = {}
        
        # Check for language hints
        languages = ['python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'rust']
        for lang in languages:
            if lang in query:
                hints['language'] = lang
                break
        
        # Check for time-based hints
        if re.search(r'\b(recent|latest|new|old|recent)\b', query):
            hints['time_based'] = True
        
        # Check for complexity hints
        if re.search(r'\b(complex|simple|easy|hard|difficult)\b', query):
            hints['complexity_aware'] = True
        
        # Check for performance hints
        if re.search(r'\b(fast|slow|efficient|performance|speed)\b', query):
            hints['performance_focused'] = True
        
        return hints

