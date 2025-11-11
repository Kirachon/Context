"""
Context Ranking Engine - Epic 3 (Part 1)

Ranks context chunks by relevance using 10-factor scoring formula.

10 Factors:
1. relevance_score: Semantic similarity (HIGHEST - weight 3.0)
2. recency_score: How recent (HIGH - weight 2.0)
3. proximity_score: Distance from current file (HIGH - weight 2.0)
4. dependency_score: Direct dependency? (MEDIUM-HIGH - weight 1.5)
5. usage_frequency: How often used (MEDIUM - weight 1.0)
6. error_correlation: Related to errors? (HIGH - weight 2.0)
7. team_signal: Expert's code? (MEDIUM - weight 1.0)
8. historical_success: Solved similar issues? (MEDIUM-HIGH - weight 1.5)
9. architectural_importance: Core component? (MEDIUM - weight 1.0)
10. user_preference: User referenced? (LOW - weight 0.5)
"""

import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

# Lazy load embedding model
_embedding_model = None


def get_embedding_model():
    """Lazy load sentence transformer model"""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            # If not installed, use dummy model
            _embedding_model = None
    return _embedding_model


@dataclass
class ScoredChunk:
    """Context chunk with relevance score"""
    chunk: any  # ContextItem
    score: float  # Total weighted score
    factors: Dict[str, float] = field(default_factory=dict)  # Individual factor scores


@dataclass
class RankedContext:
    """Context chunks ranked by relevance"""
    chunks: List[ScoredChunk] = field(default_factory=list)


class ContextRanker:
    """
    Rank context chunks by relevance using 10-factor scoring

    Uses weighted sum of 10 factors to compute relevance score:
    - Semantic similarity is weighted highest (3.0)
    - Recency and proximity are also important (2.0 each)
    - Other factors provide additional signal (0.5-1.5)
    """

    DEFAULT_WEIGHTS = {
        'relevance_score': 3.0,           # Semantic similarity (HIGHEST)
        'recency_score': 2.0,             # How recent
        'proximity_score': 2.0,           # Distance from current file
        'dependency_score': 1.5,          # Direct dependency?
        'usage_frequency': 1.0,           # How often used
        'error_correlation': 2.0,         # Related to errors?
        'team_signal': 1.0,               # Expert's code?
        'historical_success': 1.5,        # Solved similar issues?
        'architectural_importance': 1.0,  # Core component?
        'user_preference': 0.5,           # User referenced?
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize context ranker

        Args:
            weights: Optional custom weights for scoring factors
        """
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.embedding_model = get_embedding_model()

    async def rank(self, raw_context, prompt_intent, user_context) -> RankedContext:
        """
        Rank all context chunks by relevance

        Args:
            raw_context: RawContext with all gathered chunks
            prompt_intent: Analyzed prompt intent
            user_context: Current user context

        Returns:
            RankedContext with chunks sorted by score
        """
        # Compute embedding for prompt once
        prompt_embedding = None
        if self.embedding_model:
            try:
                prompt_embedding = self.embedding_model.encode(
                    prompt_intent.original_prompt
                )
            except Exception:
                pass

        scored_chunks = []

        # Score each context item
        for chunk in raw_context.chunks:
            for item in chunk.items:
                # Compute all 10 factors
                factors = {
                    'relevance_score': self._semantic_similarity(
                        prompt_embedding,
                        item
                    ),
                    'recency_score': self._recency_score(item),
                    'proximity_score': self._proximity_score(item, user_context),
                    'dependency_score': self._dependency_score(item, user_context),
                    'usage_frequency': self._usage_frequency(item),
                    'error_correlation': self._error_correlation(item, prompt_intent),
                    'team_signal': self._team_signal(item, user_context),
                    'historical_success': self._historical_success(item),
                    'architectural_importance': self._architectural_importance(item),
                    'user_preference': self._user_preference(item, prompt_intent),
                }

                # Compute weighted score
                total_score = sum(
                    factors[name] * weight
                    for name, weight in self.weights.items()
                )

                # Add base priority from gatherer
                total_score += item.priority

                scored_chunks.append(ScoredChunk(
                    chunk=item,
                    score=total_score,
                    factors=factors
                ))

        # Sort by score (descending)
        scored_chunks.sort(key=lambda x: x.score, reverse=True)

        return RankedContext(chunks=scored_chunks)

    def _semantic_similarity(self, prompt_embedding, item) -> float:
        """
        Compute cosine similarity between prompt and context

        Returns: 0.0 - 1.0
        """
        if prompt_embedding is None or self.embedding_model is None:
            # Fallback: simple keyword matching
            return self._keyword_similarity(item)

        try:
            # Get content text
            content = str(item.content)[:1000]  # Limit to first 1000 chars

            # Compute embedding
            item_embedding = self.embedding_model.encode(content)

            # Cosine similarity
            similarity = np.dot(prompt_embedding, item_embedding) / (
                np.linalg.norm(prompt_embedding) * np.linalg.norm(item_embedding)
            )

            return max(0.0, min(1.0, float(similarity)))

        except Exception:
            return self._keyword_similarity(item)

    def _keyword_similarity(self, item) -> float:
        """Fallback keyword-based similarity"""
        # Simple fallback: return 0.5 for any content
        return 0.5

    def _recency_score(self, item) -> float:
        """
        Score based on how recent this context is

        Returns: 0.0 - 1.0
        """
        if not hasattr(item, 'timestamp') or item.timestamp is None:
            return 0.5  # Unknown age

        try:
            age_hours = (datetime.now() - item.timestamp).total_seconds() / 3600

            # Exponential decay: recent = 1.0, 1 week old = ~0.1
            score = math.exp(-age_hours / 168)  # 168 hours = 1 week
            return max(0.0, min(1.0, score))

        except Exception:
            return 0.5

    def _proximity_score(self, item, user_context) -> float:
        """
        Score based on distance from current file

        Returns: 0.0 - 1.0
        """
        if not user_context.current_file:
            return 0.5

        item_path = item.metadata.get('path', '')
        if not item_path:
            return 0.5

        try:
            # Same file = 1.0
            if item_path == user_context.current_file:
                return 1.0

            # Same directory = 0.8
            if os.path.dirname(item_path) == os.path.dirname(user_context.current_file):
                return 0.8

            # Same top-level directory (module) = 0.6
            item_parts = item_path.split('/')
            current_parts = user_context.current_file.split('/')
            if item_parts[0] == current_parts[0]:
                return 0.6

            # Different module = 0.3
            return 0.3

        except Exception:
            return 0.5

    def _dependency_score(self, item, user_context) -> float:
        """
        Score based on dependency relationship

        Returns: 0.0 - 1.0
        """
        if item.type in ['dependency', 'reverse_dependency']:
            return 1.0
        elif item.type == 'test':
            return 0.9
        elif item.type == 'file' and user_context.current_file:
            # Check if it's a dependency
            # (simplified check - actual implementation would parse imports)
            return 0.5
        else:
            return 0.3

    def _usage_frequency(self, item) -> float:
        """
        Score based on how often this code is used

        Returns: 0.0 - 1.0
        """
        # Stub: Would need to track usage patterns
        # For now, use simple heuristics
        if item.type in ['config', 'schema']:
            return 0.8  # Config files are important
        elif item.type == 'test':
            return 0.6
        else:
            return 0.5

    def _error_correlation(self, item, prompt_intent) -> float:
        """
        Score based on correlation with error messages

        Returns: 0.0 - 1.0
        """
        # Check if prompt contains errors
        try:
            from src.prompt.analyzer import EntityType
            has_errors = any(
                e.type == EntityType.ERROR
                for e in prompt_intent.entities
            )
        except ImportError:
            has_errors = any(
                e.type == "ERROR"
                for e in prompt_intent.entities
            )

        if not has_errors:
            return 0.5

        # Check if this item mentions similar errors
        content = str(item.content).lower()
        if any(
            error_type in content
            for error_type in ['error', 'exception', 'traceback', 'failed']
        ):
            return 0.9
        else:
            return 0.3

    def _team_signal(self, item, user_context) -> float:
        """
        Score based on team expertise

        Returns: 0.0 - 1.0
        """
        # Check if item has expert information
        if item.type == 'experts':
            return 0.9
        elif item.type == 'codeowners':
            return 0.8
        elif item.source == 'team':
            return 0.7
        else:
            return 0.5

    def _historical_success(self, item) -> float:
        """
        Score based on historical success solving similar issues

        Returns: 0.0 - 1.0
        """
        # Stub: Would need to track solution success rates
        # For now, favor commit history and blame
        if item.type in ['recent_commit', 'git_blame']:
            return 0.7
        else:
            return 0.5

    def _architectural_importance(self, item) -> float:
        """
        Score based on architectural importance

        Returns: 0.0 - 1.0
        """
        # Config files and schemas are architecturally important
        if item.type in ['config', 'schema']:
            return 0.9
        elif item.source == 'architecture':
            return 0.8
        elif item.type == 'dependency':
            return 0.7
        else:
            return 0.5

    def _user_preference(self, item, prompt_intent) -> float:
        """
        Score based on user explicitly referencing this

        Returns: 0.0 - 1.0
        """
        # Check if item path/name is mentioned in prompt
        item_name = item.metadata.get('path', '')
        if item_name and item_name.lower() in prompt_intent.original_prompt.lower():
            return 1.0
        else:
            return 0.5
