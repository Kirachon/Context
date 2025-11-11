"""
Context Ranker

Multi-factor ranking system that boosts search results based on user context,
including current file, recent files, frequent files, and team patterns.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os

from .models import SearchContext, EnhancedSearchResult, BoostFactors, ParsedQuery

logger = logging.getLogger(__name__)


class ContextRanker:
    """
    Re-ranks search results based on context.

    Applies multi-factor boosting:
    - Current file/project boost (2.0x)
    - Recent files boost (1.5x)
    - Frequent files boost (1.3x)
    - Team patterns boost (1.2x)
    - Relationship boost (1.5x)
    - Recency boost (0.5x)
    - Exact match boost (0.8x)
    """

    # Boost multipliers
    CURRENT_FILE_MULTIPLIER = 2.0
    RECENT_FILES_MULTIPLIER = 1.5
    FREQUENT_FILES_MULTIPLIER = 1.3
    TEAM_PATTERNS_MULTIPLIER = 1.2
    RELATIONSHIP_MULTIPLIER = 1.5
    RECENCY_MULTIPLIER = 0.5
    EXACT_MATCH_MULTIPLIER = 0.8

    def __init__(self, enable_explanations: bool = True):
        """
        Initialize context ranker.

        Args:
            enable_explanations: Whether to generate ranking explanations
        """
        self.enable_explanations = enable_explanations

    def rank(
        self,
        results: List[Dict],
        context: SearchContext,
        query: Optional[ParsedQuery] = None,
        project_relationships: Optional[Dict[str, List[str]]] = None
    ) -> List[EnhancedSearchResult]:
        """
        Apply context-based boosting and re-rank results.

        Args:
            results: List of search results (dicts with file_path, score, etc.)
            context: User search context
            query: Parsed query (optional, for exact match detection)
            project_relationships: Project dependency graph (optional)

        Returns:
            List of EnhancedSearchResult with final scores and boost breakdown
        """
        enhanced_results = []

        for result in results:
            # Calculate all boost factors
            boosts = self._calculate_boosts(
                result,
                context,
                query,
                project_relationships
            )

            # Calculate final score
            base_score = result.get("similarity_score", 0.0)
            final_score = base_score + boosts.total_boost()

            # Calculate context relevance
            context_relevance = self._calculate_context_relevance(result, context)

            # Create enhanced result
            enhanced = EnhancedSearchResult(
                file_path=result["file_path"],
                file_name=result.get("file_name", os.path.basename(result["file_path"])),
                file_type=result.get("file_type", "unknown"),
                base_score=base_score,
                final_score=final_score,
                boost_breakdown=boosts,
                context_relevance=context_relevance,
                query_understanding=query,
                snippet=result.get("snippet"),
                line_numbers=result.get("line_numbers"),
                metadata=result.get("metadata", {})
            )

            enhanced_results.append(enhanced)

        # Sort by final score (highest first)
        enhanced_results.sort(key=lambda r: r.final_score, reverse=True)

        return enhanced_results

    def _calculate_boosts(
        self,
        result: Dict,
        context: SearchContext,
        query: Optional[ParsedQuery],
        project_relationships: Optional[Dict[str, List[str]]]
    ) -> BoostFactors:
        """Calculate all boost factors for a result"""
        file_path = result["file_path"]

        boosts = BoostFactors(
            current_file_boost=self._current_file_boost(file_path, context),
            recent_files_boost=self._recent_files_boost(file_path, context),
            frequent_files_boost=self._frequent_files_boost(file_path, context),
            team_patterns_boost=self._team_patterns_boost(file_path, context),
            relationship_boost=self._relationship_boost(
                file_path, context, project_relationships
            ),
            recency_boost=self._recency_boost(result),
            exact_match_boost=self._exact_match_boost(result, query)
        )

        return boosts

    def _current_file_boost(self, file_path: str, context: SearchContext) -> float:
        """
        Boost files from current project/file.

        Returns boost value (0-1) to be multiplied by CURRENT_FILE_MULTIPLIER.
        """
        boost = 0.0

        # Same file
        if context.current_file and file_path == context.current_file:
            boost = 1.0
            logger.debug(f"Current file boost: {file_path} (same file)")
            return boost

        # Same project
        if context.current_project:
            file_project = self._extract_project(file_path)
            if file_project and file_project == context.current_project:
                boost = 0.8
                logger.debug(f"Current project boost: {file_path} (project: {file_project})")
                return boost

        # Same directory
        if context.current_file:
            current_dir = os.path.dirname(context.current_file)
            file_dir = os.path.dirname(file_path)
            if current_dir == file_dir:
                boost = 0.6
                logger.debug(f"Same directory boost: {file_path}")
                return boost

        return boost

    def _recent_files_boost(self, file_path: str, context: SearchContext) -> float:
        """
        Boost files accessed recently.

        Returns boost value (0-1) to be multiplied by RECENT_FILES_MULTIPLIER.
        """
        if file_path in context.recent_files:
            # Position-based boost (more recent = higher boost)
            position = context.recent_files.index(file_path)
            boost = 1.0 - (position / len(context.recent_files)) * 0.5
            logger.debug(f"Recent files boost: {file_path} (position: {position})")
            return boost

        return 0.0

    def _frequent_files_boost(self, file_path: str, context: SearchContext) -> float:
        """
        Boost frequently accessed files.

        Returns boost value (0-1) to be multiplied by FREQUENT_FILES_MULTIPLIER.
        """
        if file_path in context.frequent_files:
            # Position-based boost (more frequent = higher boost)
            position = context.frequent_files.index(file_path)
            boost = 1.0 - (position / len(context.frequent_files)) * 0.5
            logger.debug(f"Frequent files boost: {file_path} (position: {position})")
            return boost

        return 0.0

    def _team_patterns_boost(self, file_path: str, context: SearchContext) -> float:
        """
        Boost files frequently accessed by team.

        Returns boost value (0-1) to be multiplied by TEAM_PATTERNS_MULTIPLIER.
        """
        boost = context.team_patterns.get(file_path, 0.0)
        if boost > 0:
            logger.debug(f"Team patterns boost: {file_path} (score: {boost:.3f})")
        return boost

    def _relationship_boost(
        self,
        file_path: str,
        context: SearchContext,
        project_relationships: Optional[Dict[str, List[str]]]
    ) -> float:
        """
        Boost files from related projects.

        Returns boost value (0-1) to be multiplied by RELATIONSHIP_MULTIPLIER.
        """
        if not project_relationships or not context.current_project:
            return 0.0

        file_project = self._extract_project(file_path)
        if not file_project:
            return 0.0

        # Check if file's project is related to current project
        related_projects = project_relationships.get(context.current_project, [])
        if file_project in related_projects:
            # Boost based on relationship type (could be enhanced)
            boost = 0.7
            logger.debug(
                f"Relationship boost: {file_path} "
                f"(project: {file_project} related to {context.current_project})"
            )
            return boost

        return 0.0

    def _recency_boost(self, result: Dict) -> float:
        """
        Boost recently modified files.

        Returns boost value (0-1) to be multiplied by RECENCY_MULTIPLIER.
        """
        # Check if result has modification time
        modified_at = result.get("metadata", {}).get("modified_at")
        if not modified_at:
            return 0.0

        # Calculate age in days
        if isinstance(modified_at, str):
            try:
                modified_at = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
            except ValueError:
                return 0.0

        age_days = (datetime.utcnow() - modified_at).days

        # Boost recent files
        if age_days < 1:
            boost = 1.0
        elif age_days < 7:
            boost = 0.8
        elif age_days < 30:
            boost = 0.5
        else:
            boost = 0.0

        if boost > 0:
            logger.debug(f"Recency boost: {result['file_path']} (age: {age_days} days)")

        return boost

    def _exact_match_boost(self, result: Dict, query: Optional[ParsedQuery]) -> float:
        """
        Boost files with exact keyword matches.

        Returns boost value (0-1) to be multiplied by EXACT_MATCH_MULTIPLIER.
        """
        if not query or not query.keywords:
            return 0.0

        file_path = result["file_path"]
        file_name = os.path.basename(file_path).lower()

        # Count keyword matches in file name
        matches = sum(1 for keyword in query.keywords if keyword.lower() in file_name)

        if matches > 0:
            boost = min(matches / len(query.keywords), 1.0)
            logger.debug(f"Exact match boost: {file_path} ({matches} keyword matches)")
            return boost

        return 0.0

    def _calculate_context_relevance(
        self,
        result: Dict,
        context: SearchContext
    ) -> float:
        """
        Calculate overall context relevance score (0-1).

        This is a normalized measure of how relevant the result is to the user's context.
        """
        file_path = result["file_path"]

        relevance = 0.0
        factors = 0

        # Current file/project
        if context.current_file:
            if file_path == context.current_file:
                relevance += 1.0
            elif self._same_project(file_path, context.current_file):
                relevance += 0.7
            elif self._same_directory(file_path, context.current_file):
                relevance += 0.5
            factors += 1

        # Recent files
        if context.recent_files:
            if file_path in context.recent_files:
                position = context.recent_files.index(file_path)
                relevance += 1.0 - (position / len(context.recent_files))
            factors += 1

        # Frequent files
        if context.frequent_files:
            if file_path in context.frequent_files:
                position = context.frequent_files.index(file_path)
                relevance += 1.0 - (position / len(context.frequent_files))
            factors += 1

        # Team patterns
        if context.team_patterns:
            relevance += context.team_patterns.get(file_path, 0.0)
            factors += 1

        # Average across factors
        if factors > 0:
            return relevance / factors

        return 0.0

    def _extract_project(self, file_path: str) -> Optional[str]:
        """Extract project name from file path"""
        parts = file_path.split(os.sep)

        # Look for common project indicators
        project_markers = ['src', 'lib', 'app', 'backend', 'frontend', 'packages']

        for i, part in enumerate(parts):
            if part in project_markers and i > 0:
                return parts[i - 1]

        # Fallback
        if len(parts) >= 3:
            return parts[-3]

        return None

    def _same_project(self, file1: str, file2: str) -> bool:
        """Check if two files are in the same project"""
        project1 = self._extract_project(file1)
        project2 = self._extract_project(file2)
        return project1 is not None and project1 == project2

    def _same_directory(self, file1: str, file2: str) -> bool:
        """Check if two files are in the same directory"""
        return os.path.dirname(file1) == os.path.dirname(file2)

    def explain_ranking(self, result: EnhancedSearchResult) -> str:
        """
        Generate human-readable explanation of ranking.

        Args:
            result: Enhanced search result

        Returns:
            Explanation string
        """
        if not self.enable_explanations:
            return ""

        return result.explain_ranking()

    def get_top_boost_factors(self, result: EnhancedSearchResult) -> List[tuple]:
        """
        Get top contributing boost factors.

        Args:
            result: Enhanced search result

        Returns:
            List of (factor_name, contribution) tuples, sorted by contribution
        """
        boost_dict = result.boost_breakdown.to_dict()
        factors = [
            (name, value * self._get_multiplier(name))
            for name, value in boost_dict.items()
            if name != "total" and value > 0
        ]
        factors.sort(key=lambda x: x[1], reverse=True)
        return factors

    def _get_multiplier(self, factor_name: str) -> float:
        """Get multiplier for a boost factor"""
        multipliers = {
            "current_file": self.CURRENT_FILE_MULTIPLIER,
            "recent_files": self.RECENT_FILES_MULTIPLIER,
            "frequent_files": self.FREQUENT_FILES_MULTIPLIER,
            "team_patterns": self.TEAM_PATTERNS_MULTIPLIER,
            "relationship": self.RELATIONSHIP_MULTIPLIER,
            "recency": self.RECENCY_MULTIPLIER,
            "exact_match": self.EXACT_MATCH_MULTIPLIER,
        }
        return multipliers.get(factor_name, 1.0)
