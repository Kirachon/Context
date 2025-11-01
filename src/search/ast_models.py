"""
AST Search Models

Enhanced search models for AST metadata and code structure search.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class SymbolType(str, Enum):
    """Types of code symbols."""
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    INTERFACE = "interface"
    VARIABLE = "variable"
    CONSTANT = "constant"
    CONSTRUCTOR = "constructor"
    PROPERTY = "property"
    TYPE_ALIAS = "type_alias"
    ENUM = "enum"
    STRUCT = "struct"
    TRAIT = "trait"


class SearchScope(str, Enum):
    """Search scope for AST elements."""
    ALL = "all"
    SYMBOLS = "symbols"
    CLASSES = "classes"
    IMPORTS = "imports"
    RELATIONSHIPS = "relationships"


class ASTSearchRequest(BaseModel):
    """Enhanced search request for AST metadata."""
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    
    # Standard filters
    file_types: Optional[List[str]] = Field(default=None, description="Filter by file extensions")
    directories: Optional[List[str]] = Field(default=None, description="Filter by directory paths")
    exclude_patterns: Optional[List[str]] = Field(default=None, description="Exclude patterns")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    
    # AST-specific filters
    symbol_types: Optional[List[SymbolType]] = Field(default=None, description="Filter by symbol types")
    languages: Optional[List[str]] = Field(default=None, description="Filter by programming languages")
    search_scope: SearchScope = Field(default=SearchScope.ALL, description="Search scope")
    
    # Advanced filters
    has_parameters: Optional[bool] = Field(default=None, description="Filter functions with/without parameters")
    has_return_type: Optional[bool] = Field(default=None, description="Filter functions with/without return types")
    is_async: Optional[bool] = Field(default=None, description="Filter async functions")
    is_static: Optional[bool] = Field(default=None, description="Filter static methods")
    is_abstract: Optional[bool] = Field(default=None, description="Filter abstract classes/methods")
    visibility: Optional[str] = Field(default=None, description="Filter by visibility (public, private, protected)")
    
    # Relationship filters
    has_inheritance: Optional[bool] = Field(default=None, description="Filter classes with inheritance")
    implements_interface: Optional[bool] = Field(default=None, description="Filter classes implementing interfaces")


class ASTSearchResult(BaseModel):
    """Enhanced search result with AST metadata."""
    # Basic file information
    file_path: str = Field(..., description="Path to the file")
    file_name: str = Field(..., description="Name of the file")
    language: str = Field(..., description="Programming language")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    
    # Symbol information
    symbol_name: Optional[str] = Field(default=None, description="Symbol name")
    symbol_type: Optional[SymbolType] = Field(default=None, description="Symbol type")
    line_start: Optional[int] = Field(default=None, description="Start line number")
    line_end: Optional[int] = Field(default=None, description="End line number")
    
    # Code context
    snippet: Optional[str] = Field(default=None, description="Code snippet")
    signature: Optional[str] = Field(default=None, description="Function/method signature")
    docstring: Optional[str] = Field(default=None, description="Documentation string")
    
    # Symbol details
    parameters: Optional[List[Dict[str, Any]]] = Field(default=None, description="Function parameters")
    return_type: Optional[str] = Field(default=None, description="Return type")
    decorators: Optional[List[str]] = Field(default=None, description="Decorators/annotations")
    
    # Class-specific information
    base_classes: Optional[List[str]] = Field(default=None, description="Base classes")
    interfaces: Optional[List[str]] = Field(default=None, description="Implemented interfaces")
    
    # Modifiers
    visibility: Optional[str] = Field(default=None, description="Visibility modifier")
    is_static: Optional[bool] = Field(default=None, description="Is static")
    is_abstract: Optional[bool] = Field(default=None, description="Is abstract")
    is_async: Optional[bool] = Field(default=None, description="Is async")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ASTSearchResponse(BaseModel):
    """Enhanced search response with AST metadata."""
    query: str = Field(..., description="Original search query")
    results: List[ASTSearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., ge=0, description="Total number of results found")
    search_time_ms: float = Field(..., ge=0, description="Search execution time")
    
    # Result breakdown
    symbols_found: int = Field(default=0, description="Number of symbols found")
    classes_found: int = Field(default=0, description="Number of classes found")
    imports_found: int = Field(default=0, description="Number of imports found")
    
    # Applied filters
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    languages_searched: List[str] = Field(default_factory=list, description="Languages searched")
    
    timestamp: str = Field(..., description="Search timestamp")


class SymbolEmbeddingPayload(BaseModel):
    """Payload structure for symbol embeddings in Qdrant."""
    # Core identification
    file_path: str
    symbol_name: str
    symbol_type: str
    language: str
    
    # Location information
    line_start: int
    line_end: int
    
    # Symbol details
    signature: Optional[str] = None
    docstring: Optional[str] = None
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = Field(default_factory=list)
    
    # Class-specific
    parent_class: Optional[str] = None
    base_classes: List[str] = Field(default_factory=list)
    interfaces: List[str] = Field(default_factory=list)
    
    # Modifiers
    visibility: Optional[str] = None
    is_static: bool = False
    is_abstract: bool = False
    is_async: bool = False
    
    # Indexing metadata
    indexed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    file_hash: Optional[str] = None
    
    # Search optimization
    search_text: str = Field(..., description="Optimized text for embedding generation")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Qdrant storage."""
        return self.model_dump()


class ClassEmbeddingPayload(BaseModel):
    """Payload structure for class embeddings in Qdrant."""
    # Core identification
    file_path: str
    class_name: str
    language: str
    
    # Location information
    line_start: int
    line_end: int
    
    # Class details
    docstring: Optional[str] = None
    base_classes: List[str] = Field(default_factory=list)
    interfaces: List[str] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    fields: List[str] = Field(default_factory=list)
    decorators: List[str] = Field(default_factory=list)
    generic_params: List[str] = Field(default_factory=list)
    
    # Modifiers
    visibility: Optional[str] = None
    is_abstract: bool = False
    is_interface: bool = False
    is_static: bool = False
    
    # Indexing metadata
    indexed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    file_hash: Optional[str] = None
    
    # Search optimization
    search_text: str = Field(..., description="Optimized text for embedding generation")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Qdrant storage."""
        return self.model_dump()


class ImportEmbeddingPayload(BaseModel):
    """Payload structure for import embeddings in Qdrant."""
    # Core identification
    file_path: str
    module: str
    language: str
    
    # Import details
    import_type: str  # import, from, include, use
    alias: Optional[str] = None
    items: List[str] = Field(default_factory=list)
    is_wildcard: bool = False
    line: Optional[int] = None
    
    # Indexing metadata
    indexed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    file_hash: Optional[str] = None
    
    # Search optimization
    search_text: str = Field(..., description="Optimized text for embedding generation")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Qdrant storage."""
        return self.model_dump()
