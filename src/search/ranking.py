"""
Search Ranking Service

Result ranking and scoring logic for search results.
"""

import logging
import math
from typing import List, Dict, Any
from datetime import datetime

from src.search.models import SearchResult

logger = logging.getLogger(__name__)


class RankingService:
    """
    Ranking Service
    
    Provides result ranking and confidence scoring for search results.
    """
    
    def __init__(self):
        """Initialize ranking service"""
        # Ranking weights
        self.similarity_weight = 0.7
        self.file_size_weight = 0.1
        self.file_type_weight = 0.1
        self.freshness_weight = 0.1
        
        # File type preferences (higher = better)
        self.file_type_scores = {
            'python': 1.0,
            'javascript': 0.9,
            'typescript': 0.9,
            'java': 0.8,
            'cpp': 0.7,
            'unknown': 0.5
        }
        
        logger.info("RankingService initialized")
    
    def rank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Rank search results by relevance
        
        Args:
            results: List of search results to rank
            
        Returns:
            Ranked list of search results
        """
        if not results:
            return results
        
        logger.debug(f"Ranking {len(results)} search results")
        
        # Calculate composite scores
        for result in results:
            result.confidence_score = self._calculate_composite_score(result)
        
        # Sort by confidence score (descending)
        ranked_results = sorted(results, key=lambda r: r.confidence_score, reverse=True)
        
        # Remove duplicates (same file path)
        deduplicated_results = self._deduplicate_results(ranked_results)
        
        logger.debug(f"Ranked and deduplicated: {len(deduplicated_results)} results")
        return deduplicated_results
    
    def _calculate_composite_score(self, result: SearchResult) -> float:
        """
        Calculate composite confidence score
        
        Args:
            result: Search result
            
        Returns:
            Composite confidence score (0-1)
        """
        # Similarity score (primary factor)
        similarity_component = result.similarity_score * self.similarity_weight
        
        # File size component (prefer medium-sized files)
        file_size_component = self._calculate_file_size_score(result.file_size) * self.file_size_weight
        
        # File type component (prefer certain languages)
        file_type_component = self._calculate_file_type_score(result.file_type) * self.file_type_weight
        
        # Freshness component (prefer recently indexed files)
        freshness_component = self._calculate_freshness_score(result.metadata) * self.freshness_weight
        
        # Combine components
        composite_score = (
            similarity_component +
            file_size_component +
            file_type_component +
            freshness_component
        )
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, composite_score))
    
    def _calculate_file_size_score(self, file_size: int) -> float:
        """
        Calculate file size score (prefer medium-sized files)
        
        Args:
            file_size: File size in bytes
            
        Returns:
            File size score (0-1)
        """
        if file_size <= 0:
            return 0.5
        
        # Optimal size range: 1KB - 50KB
        optimal_min = 1024  # 1KB
        optimal_max = 51200  # 50KB
        
        if optimal_min <= file_size <= optimal_max:
            return 1.0
        elif file_size < optimal_min:
            # Small files get lower score
            return 0.3 + 0.7 * (file_size / optimal_min)
        else:
            # Large files get decreasing score
            size_ratio = file_size / optimal_max
            return max(0.1, 1.0 / math.log(size_ratio + 1))
    
    def _calculate_file_type_score(self, file_type: str) -> float:
        """
        Calculate file type score based on preferences
        
        Args:
            file_type: File type/language
            
        Returns:
            File type score (0-1)
        """
        return self.file_type_scores.get(file_type.lower(), 0.5)
    
    def _calculate_freshness_score(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate freshness score based on indexing time
        
        Args:
            metadata: Result metadata
            
        Returns:
            Freshness score (0-1)
        """
        try:
            indexed_time_str = metadata.get("indexed_time")
            if not indexed_time_str:
                return 0.5  # Neutral score for unknown time
            
            # Parse indexed time
            indexed_time = datetime.fromisoformat(indexed_time_str.replace('Z', '+00:00'))
            current_time = datetime.utcnow().replace(tzinfo=indexed_time.tzinfo)
            
            # Calculate age in days
            age_days = (current_time - indexed_time).total_seconds() / (24 * 3600)
            
            # Fresher files get higher scores
            if age_days <= 1:
                return 1.0  # Very fresh
            elif age_days <= 7:
                return 0.9  # Fresh
            elif age_days <= 30:
                return 0.7  # Recent
            elif age_days <= 90:
                return 0.5  # Moderate
            else:
                return 0.3  # Old
                
        except Exception as e:
            logger.debug(f"Error calculating freshness score: {e}")
            return 0.5  # Neutral score on error
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Remove duplicate results (same file path)
        
        Args:
            results: List of search results
            
        Returns:
            Deduplicated results
        """
        seen_paths = set()
        deduplicated = []
        
        for result in results:
            if result.file_path not in seen_paths:
                seen_paths.add(result.file_path)
                deduplicated.append(result)
        
        return deduplicated
    
    def calculate_confidence_score(self, similarity_score: float, file_size: int) -> float:
        """
        Calculate confidence score for a single result
        
        Args:
            similarity_score: Vector similarity score
            file_size: File size in bytes
            
        Returns:
            Confidence score (0-1)
        """
        # Simple confidence calculation based on similarity and file size
        size_factor = self._calculate_file_size_score(file_size)
        confidence = similarity_score * 0.8 + size_factor * 0.2
        
        return max(0.0, min(1.0, confidence))
    
    def get_ranking_weights(self) -> Dict[str, float]:
        """
        Get current ranking weights
        
        Returns:
            Dictionary of ranking weights
        """
        return {
            "similarity_weight": self.similarity_weight,
            "file_size_weight": self.file_size_weight,
            "file_type_weight": self.file_type_weight,
            "freshness_weight": self.freshness_weight
        }
    
    def update_ranking_weights(self, weights: Dict[str, float]):
        """
        Update ranking weights
        
        Args:
            weights: New ranking weights
        """
        if "similarity_weight" in weights:
            self.similarity_weight = weights["similarity_weight"]
        if "file_size_weight" in weights:
            self.file_size_weight = weights["file_size_weight"]
        if "file_type_weight" in weights:
            self.file_type_weight = weights["file_type_weight"]
        if "freshness_weight" in weights:
            self.freshness_weight = weights["freshness_weight"]
        
        logger.info(f"Updated ranking weights: {self.get_ranking_weights()}")


# Global ranking service instance
ranking_service = RankingService()


def get_ranking_service() -> RankingService:
    """Get ranking service instance"""
    return ranking_service
