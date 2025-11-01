"""
AST Parsing Cache

Redis-based caching for parsed AST results with file change invalidation.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from .models import (
    ParseResult,
    Language,
    ASTNode,
    SymbolInfo,
    ImportInfo,
    ClassInfo,
    RelationshipInfo,
    ParameterInfo,
)

logger = logging.getLogger(__name__)

# Global cache instance
_global_cache: Optional["ASTCache"] = None


class ASTCache:
    """Redis-based cache for AST parsing results."""

    def __init__(self, redis_client=None):
        """Initialize AST cache with Redis client."""
        self.redis_client = redis_client
        self.cache_prefix = "ast_cache:"
        self.enabled = redis_client is not None

        if self.enabled:
            logger.info("AST cache initialized with Redis backend")
        else:
            logger.warning("AST cache disabled - no Redis client provided")

    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        """Get hash of file content for cache invalidation."""
        try:
            content = file_path.read_bytes()
            return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash file {file_path}: {e}")
            return None

    def _get_cache_key(self, file_path: Path) -> str:
        """Generate cache key for file."""
        return f"{self.cache_prefix}{str(file_path)}"

    def _serialize_parse_result(self, result: ParseResult) -> str:
        """Serialize ParseResult to JSON string."""
        return json.dumps(result.to_dict())

    def _deserialize_parse_result(self, data: str) -> ParseResult:
        """Deserialize JSON string to ParseResult."""
        parsed = json.loads(data)

        # Reconstruct AST node if present
        ast_root = None
        if parsed.get("ast_root"):
            ast_root = self._dict_to_ast_node(parsed["ast_root"])

        # Reconstruct symbols
        symbols = []
        for symbol_data in parsed.get("symbols", []):
            # Reconstruct parameters
            params = [ParameterInfo(**p) for p in symbol_data.get("parameters", [])]
            symbol_data["parameters"] = params
            symbols.append(SymbolInfo(**symbol_data))

        # Reconstruct classes
        classes = [ClassInfo(**class_data) for class_data in parsed.get("classes", [])]

        # Reconstruct imports
        imports = [
            ImportInfo(**import_data) for import_data in parsed.get("imports", [])
        ]

        # Reconstruct relationships
        relationships = [
            RelationshipInfo(**rel_data) for rel_data in parsed.get("relationships", [])
        ]

        return ParseResult(
            file_path=Path(parsed["file_path"]),
            language=Language(parsed["language"]),
            ast_root=ast_root,
            symbols=symbols,
            classes=classes,
            imports=imports,
            relationships=relationships,
            parse_success=parsed["parse_success"],
            parse_error=parsed.get("parse_error"),
            parse_time_ms=parsed["parse_time_ms"],
            symbol_extraction_time_ms=parsed.get("symbol_extraction_time_ms", 0.0),
        )

    def _dict_to_ast_node(self, data: Dict[str, Any]) -> ASTNode:
        """Convert dictionary back to ASTNode."""
        node = ASTNode(
            type=data["type"],
            text=data["text"],
            start_byte=data["start_byte"],
            end_byte=data["end_byte"],
            start_point=tuple(data["start_point"]),
            end_point=tuple(data["end_point"]),
        )

        # Recursively reconstruct children
        for child_data in data.get("children", []):
            child_node = self._dict_to_ast_node(child_data)
            child_node.parent = node
            node.children.append(child_node)

        return node

    def get(self, file_path: Path) -> Optional[ParseResult]:
        """Get cached parse result for file."""
        if not self.enabled:
            return None

        try:
            cache_key = self._get_cache_key(file_path)
            cached_data = self.redis_client.hgetall(cache_key)

            if not cached_data:
                logger.debug(f"Cache miss for {file_path}")
                return None

            # Check if file has changed
            current_hash = self._get_file_hash(file_path)
            cached_hash = cached_data.get(b"file_hash", b"").decode()

            if current_hash != cached_hash:
                logger.debug(f"Cache invalidated for {file_path} (file changed)")
                self.redis_client.delete(cache_key)
                return None

            # Deserialize cached result
            result_data = cached_data.get(b"result", b"").decode()
            if result_data:
                result = self._deserialize_parse_result(result_data)
                logger.debug(f"Cache hit for {file_path}")
                return result

        except Exception as e:
            logger.warning(f"Failed to get cached result for {file_path}: {e}")

        return None

    def set(self, file_path: Path, result: ParseResult, ttl_seconds: int = 3600):
        """Cache parse result for file."""
        if not self.enabled:
            return

        try:
            cache_key = self._get_cache_key(file_path)
            file_hash = self._get_file_hash(file_path)

            if file_hash is None:
                return

            # Serialize and cache
            result_data = self._serialize_parse_result(result)

            pipe = self.redis_client.pipeline()
            pipe.hset(
                cache_key, mapping={"file_hash": file_hash, "result": result_data}
            )
            pipe.expire(cache_key, ttl_seconds)
            pipe.execute()

            logger.debug(f"Cached parse result for {file_path}")

        except Exception as e:
            logger.warning(f"Failed to cache result for {file_path}: {e}")

    def invalidate(self, file_path: Path):
        """Invalidate cached result for file."""
        if not self.enabled:
            return

        try:
            cache_key = self._get_cache_key(file_path)
            self.redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for {file_path}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for {file_path}: {e}")

    def clear(self):
        """Clear all cached AST results."""
        if not self.enabled:
            return

        try:
            pattern = f"{self.cache_prefix}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cached AST results")
        except Exception as e:
            logger.warning(f"Failed to clear AST cache: {e}")


def get_ast_cache() -> ASTCache:
    """Get the global AST cache instance."""
    global _global_cache
    if _global_cache is None:
        # Try to get Redis client from config
        try:
            from src.config.settings import settings

            redis_client = getattr(settings, "redis_client", None)
            _global_cache = ASTCache(redis_client)
        except Exception:
            _global_cache = ASTCache(None)  # Disabled cache
    return _global_cache
