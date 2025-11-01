"""
Search Models

Pydantic models for search requests and responses.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    file_types: Optional[List[str]] = Field(default=None, description="Filter by file extensions (e.g., ['.py', '.js'])")
    directories: Optional[List[str]] = Field(default=None, description="Filter by directory paths")
    exclude_patterns: Optional[List[str]] = Field(default=None, description="Exclude patterns (e.g., ['test', '__pycache__'])")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    # Advanced filters (Story 2.4)
    authors: Optional[List[str]] = Field(default=None, description="Filter by authors (if metadata available)")
    modified_after: Optional[str] = Field(default=None, description="ISO 8601 modified time lower bound")
    modified_before: Optional[str] = Field(default=None, description="ISO 8601 modified time upper bound")


class SearchResult(BaseModel):
    """Individual search result"""
    file_path: str = Field(..., description="Path to the file")
    file_name: str = Field(..., description="Name of the file")
    file_type: str = Field(..., description="Programming language/file type")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    snippet: Optional[str] = Field(default=None, description="Code snippet preview")
    line_numbers: Optional[List[int]] = Field(default=None, description="Relevant line numbers")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchResponse(BaseModel):
    """Search response model"""
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., ge=0, description="Total number of results found")
    search_time_ms: float = Field(..., ge=0, description="Search execution time in milliseconds")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Filters that were applied")
    timestamp: str = Field(..., description="Search timestamp")


class SearchStats(BaseModel):
    """Search statistics model"""
    total_searches: int = Field(..., ge=0, description="Total number of searches performed")
    average_response_time_ms: float = Field(..., ge=0, description="Average response time")
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")
    popular_queries: List[str] = Field(..., description="Most popular search queries")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Search error rate")
    timestamp: str = Field(..., description="Statistics timestamp")


class SearchError(BaseModel):
    """Search error model"""
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    query: Optional[str] = Field(default=None, description="Query that caused the error")
    timestamp: str = Field(..., description="Error timestamp")
