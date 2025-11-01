"""
Parsing Models

Data models for AST parsing results and code structure analysis.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"


@dataclass
class ASTNode:
    """Represents a node in the Abstract Syntax Tree."""
    type: str
    text: str
    start_byte: int
    end_byte: int
    start_point: tuple[int, int]  # (row, column)
    end_point: tuple[int, int]    # (row, column)
    children: List['ASTNode'] = field(default_factory=list)
    parent: Optional['ASTNode'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AST node to dictionary for serialization."""
        return {
            "type": self.type,
            "text": self.text,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "start_point": self.start_point,
            "end_point": self.end_point,
            "children": [child.to_dict() for child in self.children]
        }


@dataclass
class ParameterInfo:
    """Information about a function/method parameter."""
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    is_variadic: bool = False  # *args, **kwargs, ...rest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type_hint": self.type_hint,
            "default_value": self.default_value,
            "is_variadic": self.is_variadic
        }


@dataclass
class SymbolInfo:
    """Information about a code symbol (function, class, variable)."""
    name: str
    type: str  # function, class, variable, method, constructor, etc.
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    parameters: List[ParameterInfo] = field(default_factory=list)
    return_type: Optional[str] = None
    visibility: Optional[str] = None  # public, private, protected
    is_static: bool = False
    is_abstract: bool = False
    is_async: bool = False
    parent_class: Optional[str] = None  # For methods
    decorators: List[str] = field(default_factory=list)  # Python decorators, Java annotations
    generic_params: List[str] = field(default_factory=list)  # Generic type parameters

    def to_dict(self) -> Dict[str, Any]:
        """Convert symbol info to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "signature": self.signature,
            "docstring": self.docstring,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type,
            "visibility": self.visibility,
            "is_static": self.is_static,
            "is_abstract": self.is_abstract,
            "is_async": self.is_async,
            "parent_class": self.parent_class,
            "decorators": self.decorators,
            "generic_params": self.generic_params
        }


@dataclass
class ClassInfo:
    """Information about a class/struct definition."""
    name: str
    line_start: int
    line_end: int
    base_classes: List[str] = field(default_factory=list)  # Inheritance
    interfaces: List[str] = field(default_factory=list)  # Implemented interfaces
    methods: List[str] = field(default_factory=list)  # Method names
    fields: List[str] = field(default_factory=list)  # Field/property names
    visibility: Optional[str] = None
    is_abstract: bool = False
    is_interface: bool = False
    is_static: bool = False
    generic_params: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "base_classes": self.base_classes,
            "interfaces": self.interfaces,
            "methods": self.methods,
            "fields": self.fields,
            "visibility": self.visibility,
            "is_abstract": self.is_abstract,
            "is_interface": self.is_interface,
            "is_static": self.is_static,
            "generic_params": self.generic_params,
            "decorators": self.decorators,
            "docstring": self.docstring
        }


@dataclass
class ImportInfo:
    """Information about imports/dependencies."""
    module: str
    alias: Optional[str] = None
    items: List[str] = field(default_factory=list)  # for from imports
    line: Optional[int] = None
    import_type: str = "import"  # import, from, include, use, etc.
    is_wildcard: bool = False  # import * or use crate::*

    def to_dict(self) -> Dict[str, Any]:
        """Convert import info to dictionary for serialization."""
        return {
            "module": self.module,
            "alias": self.alias,
            "items": self.items,
            "line": self.line,
            "import_type": self.import_type,
            "is_wildcard": self.is_wildcard
        }


@dataclass
class RelationshipInfo:
    """Information about code relationships (calls, inheritance, etc.)."""
    type: str  # call, inheritance, implements, uses, etc.
    source: str  # Source symbol name
    target: str  # Target symbol name
    source_line: Optional[int] = None
    context: Optional[str] = None  # Additional context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "source": self.source,
            "target": self.target,
            "source_line": self.source_line,
            "context": self.context
        }


@dataclass
class ParseResult:
    """Result of parsing a code file."""
    file_path: Path
    language: Language
    ast_root: Optional[ASTNode]
    symbols: List[SymbolInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    relationships: List[RelationshipInfo] = field(default_factory=list)
    parse_success: bool = True
    parse_error: Optional[str] = None
    parse_time_ms: float = 0.0
    symbol_extraction_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert parse result to dictionary for serialization."""
        return {
            "file_path": str(self.file_path),
            "language": self.language.value,
            "ast_root": self.ast_root.to_dict() if self.ast_root else None,
            "symbols": [symbol.to_dict() for symbol in self.symbols],
            "classes": [cls.to_dict() for cls in self.classes],
            "imports": [imp.to_dict() for imp in self.imports],
            "relationships": [rel.to_dict() for rel in self.relationships],
            "parse_success": self.parse_success,
            "parse_error": self.parse_error,
            "parse_time_ms": self.parse_time_ms,
            "symbol_extraction_time_ms": self.symbol_extraction_time_ms
        }
