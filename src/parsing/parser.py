"""
Tree-sitter Code Parser

Implements comprehensive AST parsing for multiple programming languages using tree-sitter.
"""

import time
from pathlib import Path
from typing import Dict, Optional, List, Any
import logging
from .models import Language, ParseResult, ASTNode, SymbolInfo, ImportInfo, ClassInfo, RelationshipInfo

logger = logging.getLogger(__name__)

# Global parser cache to avoid recreating parsers
_parser_cache: Dict[Language, Any] = {}


def detect_language(file_path: Path) -> Optional[Language]:
    """Detect programming language from file extension."""
    suffix = file_path.suffix.lower()
    
    language_map = {
        '.py': Language.PYTHON,
        '.js': Language.JAVASCRIPT,
        '.jsx': Language.JAVASCRIPT,
        '.ts': Language.TYPESCRIPT,
        '.tsx': Language.TYPESCRIPT,
        '.java': Language.JAVA,
        '.cpp': Language.CPP,
        '.cc': Language.CPP,
        '.cxx': Language.CPP,
        '.c++': Language.CPP,
        '.hpp': Language.CPP,
        '.h': Language.CPP,
        '.go': Language.GO,
        '.rs': Language.RUST,
    }
    
    return language_map.get(suffix)


def _get_tree_sitter_parser(language: Language):
    """Get or create a tree-sitter parser for the given language."""
    if language in _parser_cache:
        return _parser_cache[language]

    try:
        # Import tree-sitter and use our language loader
        import tree_sitter
        from .ts_loader import load_language

        # Load language using our loader (tries prebuilt first, then compiled)
        lang = load_language(language.value)

        parser = tree_sitter.Parser()
        parser.set_language(lang)
        _parser_cache[language] = parser
        logger.debug(f"Created tree-sitter parser for {language.value}")
        return parser

    except ImportError as e:
        logger.warning(f"Tree-sitter library not available for {language.value}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to create parser for {language.value}: {e}")
        return None


def _tree_sitter_node_to_ast_node(ts_node, source_bytes: bytes) -> ASTNode:
    """Convert tree-sitter node to our ASTNode representation."""
    # Extract text for this node
    node_text = source_bytes[ts_node.start_byte:ts_node.end_byte].decode('utf-8', errors='replace')

    # Handle different tree-sitter versions for point access
    try:
        # Try new tuple format first (tree-sitter 0.21+)
        if isinstance(ts_node.start_point, tuple):
            start_point = ts_node.start_point  # (row, column)
            end_point = ts_node.end_point      # (row, column)
        else:
            # Fallback to object format (older versions)
            start_point = (ts_node.start_point.row, ts_node.start_point.column)
            end_point = (ts_node.end_point.row, ts_node.end_point.column)
    except AttributeError:
        # Fallback if point access fails
        start_point = (0, 0)
        end_point = (0, 0)

    # Create our AST node
    ast_node = ASTNode(
        type=ts_node.type,
        text=node_text,
        start_byte=ts_node.start_byte,
        end_byte=ts_node.end_byte,
        start_point=start_point,
        end_point=end_point
    )

    # Recursively convert children
    for child in ts_node.children:
        child_ast_node = _tree_sitter_node_to_ast_node(child, source_bytes)
        child_ast_node.parent = ast_node
        ast_node.children.append(child_ast_node)

    return ast_node


class CodeParser:
    """Main code parser using tree-sitter for AST generation."""
    
    def __init__(self):
        """Initialize the code parser."""
        self.supported_languages = set(Language)
        logger.info(f"CodeParser initialized with support for: {[lang.value for lang in self.supported_languages]}")
    
    def parse(self, file_path: Path, content: Optional[str] = None) -> ParseResult:
        """
        Parse a code file and return comprehensive AST and structure information.
        
        Args:
            file_path: Path to the code file
            content: Optional file content (if None, will read from file_path)
            
        Returns:
            ParseResult with AST, symbols, imports, and metadata
        """
        start_time = time.time()
        
        # Detect language
        language = detect_language(file_path)
        if not language:
            return ParseResult(
                file_path=file_path,
                language=Language.PYTHON,  # fallback
                ast_root=None,
                parse_success=False,
                parse_error=f"Unsupported file extension: {file_path.suffix}",
                parse_time_ms=(time.time() - start_time) * 1000
            )
        
        # Read content if not provided
        if content is None:
            try:
                content = file_path.read_text(encoding='utf-8')
            except Exception as e:
                return ParseResult(
                    file_path=file_path,
                    language=language,
                    ast_root=None,
                    parse_success=False,
                    parse_error=f"Failed to read file: {e}",
                    parse_time_ms=(time.time() - start_time) * 1000
                )
        
        # Get parser for this language
        parser = _get_tree_sitter_parser(language)
        if not parser:
            return ParseResult(
                file_path=file_path,
                language=language,
                ast_root=None,
                parse_success=False,
                parse_error=f"Parser not available for {language.value}",
                parse_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            # Parse the code
            source_bytes = content.encode('utf-8')
            tree = parser.parse(source_bytes)
            
            # Convert to our AST representation
            ast_root = _tree_sitter_node_to_ast_node(tree.root_node, source_bytes)

            # Extract symbols, classes, imports, and relationships
            symbol_start_time = time.time()
            symbols, classes, imports, relationships = self._extract_symbols(ast_root, language)
            symbol_extraction_time_ms = (time.time() - symbol_start_time) * 1000

            parse_time_ms = (time.time() - start_time) * 1000
            logger.debug(f"Successfully parsed {file_path} ({language.value}) in {parse_time_ms:.2f}ms")
            logger.debug(f"Symbol extraction took {symbol_extraction_time_ms:.2f}ms")
            logger.debug(f"Extracted {len(symbols)} symbols, {len(classes)} classes, {len(imports)} imports")

            return ParseResult(
                file_path=file_path,
                language=language,
                ast_root=ast_root,
                symbols=symbols,
                classes=classes,
                imports=imports,
                relationships=relationships,
                parse_success=True,
                parse_time_ms=parse_time_ms,
                symbol_extraction_time_ms=symbol_extraction_time_ms
            )
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return ParseResult(
                file_path=file_path,
                language=language,
                ast_root=None,
                parse_success=False,
                parse_error=str(e),
                parse_time_ms=(time.time() - start_time) * 1000
            )

    def _extract_symbols(self, ast_root: ASTNode, language: Language) -> tuple[
        List[SymbolInfo], List[ClassInfo], List[ImportInfo], List[RelationshipInfo]
    ]:
        """Extract symbols from AST using language-specific extractors."""
        try:
            from .extractors import get_symbol_extractor
            extractor = get_symbol_extractor()
            return extractor.extract_symbols(ast_root, language)
        except Exception as e:
            logger.warning(f"Symbol extraction failed for {language.value}: {e}")
            return [], [], [], []


# Global parser instance
_global_parser: Optional[CodeParser] = None


def get_parser() -> CodeParser:
    """Get the global parser instance."""
    global _global_parser
    if _global_parser is None:
        _global_parser = CodeParser()
    return _global_parser
