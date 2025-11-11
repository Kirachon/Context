"""
Intelligent Search Models

Data models for natural language query parsing, context tracking, and enhanced search results.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class Intent(str, Enum):
    """Query intent types"""
    FIND = "find"
    LIST = "list"
    SHOW = "show"
    SEARCH = "search"
    EXPLAIN = "explain"
    COMPARE = "compare"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Entity types extracted from queries"""
    FILE_NAME = "file_name"
    FUNCTION_NAME = "function_name"
    CLASS_NAME = "class_name"
    MODULE_NAME = "module_name"
    CONCEPT = "concept"
    KEYWORD = "keyword"
    PATTERN = "pattern"


@dataclass
class Entity:
    """Extracted entity from query"""
    text: str
    type: EntityType
    confidence: float = 1.0
    start_pos: int = 0
    end_pos: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedQuery:
    """Parsed natural language query"""
    original: str
    entities: List[Entity]
    intent: Intent
    expanded_terms: List[str]
    confidence: float
    keywords: List[str] = field(default_factory=list)
    stop_words_removed: List[str] = field(default_factory=list)
    lemmatized_terms: List[str] = field(default_factory=list)
    parsed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "original": self.original,
            "entities": [
                {
                    "text": e.text,
                    "type": e.type.value,
                    "confidence": e.confidence
                }
                for e in self.entities
            ],
            "intent": self.intent.value,
            "expanded_terms": self.expanded_terms,
            "confidence": self.confidence,
            "keywords": self.keywords
        }


@dataclass
class ExpandedTerm:
    """Term expanded from original query"""
    original: str
    expanded: str
    relevance_score: float
    expansion_type: str  # synonym, related, acronym, etc.
    source: str = "word2vec"  # word2vec, codebert, manual, etc.


@dataclass
class SearchContext:
    """User context for ranking"""
    user_id: str
    current_file: Optional[str] = None
    current_project: Optional[str] = None
    recent_files: List[str] = field(default_factory=list)  # Last hour
    frequent_files: List[str] = field(default_factory=list)  # Top 20
    recent_queries: List[str] = field(default_factory=list)  # Last 10
    team_patterns: Dict[str, float] = field(default_factory=dict)  # File → access frequency
    session_start: datetime = field(default_factory=datetime.utcnow)

    def get_current_project_from_file(self) -> Optional[str]:
        """Extract project from current file path"""
        if self.current_file and "/" in self.current_file:
            # Try to extract project from path (e.g., /path/to/project/src/file.py)
            parts = self.current_file.split("/")
            if len(parts) >= 2:
                return parts[-3] if len(parts) >= 3 else parts[-2]
        return self.current_project


@dataclass
class BoostFactors:
    """Breakdown of boost factors applied to a result"""
    current_file_boost: float = 0.0
    recent_files_boost: float = 0.0
    frequent_files_boost: float = 0.0
    team_patterns_boost: float = 0.0
    relationship_boost: float = 0.0
    recency_boost: float = 0.0
    exact_match_boost: float = 0.0

    def total_boost(self) -> float:
        """Calculate total boost"""
        return (
            self.current_file_boost * 2.0 +
            self.recent_files_boost * 1.5 +
            self.frequent_files_boost * 1.3 +
            self.team_patterns_boost * 1.2 +
            self.relationship_boost * 1.5 +
            self.recency_boost * 0.5 +
            self.exact_match_boost * 0.8
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            "current_file": self.current_file_boost,
            "recent_files": self.recent_files_boost,
            "frequent_files": self.frequent_files_boost,
            "team_patterns": self.team_patterns_boost,
            "relationship": self.relationship_boost,
            "recency": self.recency_boost,
            "exact_match": self.exact_match_boost,
            "total": self.total_boost()
        }


@dataclass
class EnhancedSearchResult:
    """Search result with boost breakdown"""
    file_path: str
    file_name: str
    file_type: str
    base_score: float  # Original similarity score
    final_score: float  # After boosting
    boost_breakdown: BoostFactors
    context_relevance: float  # How relevant to current context
    query_understanding: Optional[ParsedQuery] = None
    snippet: Optional[str] = None
    line_numbers: Optional[List[int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "base_score": self.base_score,
            "final_score": self.final_score,
            "boost_breakdown": self.boost_breakdown.to_dict(),
            "context_relevance": self.context_relevance,
            "snippet": self.snippet,
            "line_numbers": self.line_numbers,
            "metadata": self.metadata
        }

    def explain_ranking(self) -> str:
        """Generate human-readable explanation of ranking"""
        parts = [f"Base score: {self.base_score:.3f}"]

        boost_dict = self.boost_breakdown.to_dict()
        for factor, value in boost_dict.items():
            if factor != "total" and value > 0:
                parts.append(f"  + {factor}: +{value:.3f}")

        parts.append(f"Final score: {self.final_score:.3f}")
        return "\n".join(parts)


@dataclass
class SearchTemplate:
    """Pre-built search template"""
    name: str
    description: str
    query_pattern: str
    intent: Intent
    default_filters: Dict[str, Any] = field(default_factory=dict)
    parameters: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    search_type: str = "semantic"  # semantic, ast, keyword, hybrid

    def apply(self, **params) -> str:
        """Apply parameters to template"""
        query = self.query_pattern
        for param, value in params.items():
            query = query.replace(f"{{{param}}}", str(value))
        return query


@dataclass
class QueryExpansion:
    """Result of query expansion"""
    original_query: str
    expanded_terms: List[ExpandedTerm]
    synonyms: Dict[str, List[str]] = field(default_factory=dict)
    acronym_expansions: Dict[str, str] = field(default_factory=dict)
    related_concepts: List[str] = field(default_factory=list)

    def get_all_terms(self) -> List[str]:
        """Get all expanded terms"""
        terms = [self.original_query]
        terms.extend([term.expanded for term in self.expanded_terms])
        for syn_list in self.synonyms.values():
            terms.extend(syn_list)
        terms.extend(self.acronym_expansions.values())
        terms.extend(self.related_concepts)
        return list(set(terms))  # Remove duplicates
