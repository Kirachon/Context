"""
AST Vector Store

Specialized vector storage for AST metadata including symbols, classes, and imports.
"""

import logging
import hashlib
import uuid
from typing import Dict, Any, Optional
from pathlib import Path

from qdrant_client.http import models
from src.vector_db.qdrant_client import get_qdrant_client
from src.vector_db.embeddings import EmbeddingService
from src.search.ast_models import (
    SymbolEmbeddingPayload,
    ClassEmbeddingPayload,
    ImportEmbeddingPayload,
)
from src.parsing.models import ParseResult, SymbolInfo, ClassInfo, ImportInfo

logger = logging.getLogger(__name__)

# UUID namespace for deterministic UUID generation (same as vector_store.py)
AST_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class ASTVectorStore:
    """
    AST Vector Store

    Manages vector storage and retrieval for AST metadata with specialized
    collections for symbols, classes, and imports.
    """

    def __init__(self, base_collection_name: str = "context"):
        """Initialize AST vector store."""
        self.base_collection_name = base_collection_name
        self.symbol_collection = f"{base_collection_name}_symbols"
        self.class_collection = f"{base_collection_name}_classes"
        self.import_collection = f"{base_collection_name}_imports"

        self.embedding_service = EmbeddingService()

        self.stats = {
            "symbols_stored": 0,
            "classes_stored": 0,
            "imports_stored": 0,
            "searches_performed": 0,
            "errors": 0,
        }

        logger.info(
            f"ASTVectorStore initialized with collections: {self.symbol_collection}, {self.class_collection}, {self.import_collection}"
        )

    async def ensure_collections(self) -> bool:
        """Ensure all AST collections exist."""
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        try:
            # Get embedding dimension
            await self.embedding_service.initialize()
            vector_size = self.embedding_service.embedding_dim

            collections_to_create = [
                self.symbol_collection,
                self.class_collection,
                self.import_collection,
            ]

            # Get existing collections
            existing_collections = client.get_collections()
            existing_names = [col.name for col in existing_collections.collections]

            # Create missing collections
            for collection_name in collections_to_create:
                if collection_name not in existing_names:
                    logger.info(f"Creating AST collection: {collection_name}")
                    client.create_collection(
                        collection_name=collection_name,
                        vectors_config=models.VectorParams(
                            size=vector_size, distance=models.Distance.COSINE
                        ),
                    )
                    logger.info(f"Created collection: {collection_name}")
                else:
                    logger.debug(f"Collection already exists: {collection_name}")

            return True

        except Exception as e:
            logger.error(f"Error ensuring AST collections: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def store_parse_result(self, parse_result: ParseResult) -> bool:
        """
        Store complete parse result in vector database.

        Args:
            parse_result: ParseResult from AST parsing

        Returns:
            bool: True if successful
        """
        if not parse_result.parse_success:
            logger.warning(
                f"Skipping storage for failed parse: {parse_result.file_path}"
            )
            return False

        try:
            # Ensure collections exist
            if not await self.ensure_collections():
                return False

            # Calculate file hash for cache invalidation
            file_hash = self._calculate_file_hash(parse_result.file_path)

            # Store symbols
            symbols_success = await self._store_symbols(parse_result, file_hash)

            # Store classes
            classes_success = await self._store_classes(parse_result, file_hash)

            # Store imports
            imports_success = await self._store_imports(parse_result, file_hash)

            success = symbols_success and classes_success and imports_success

            if success:
                logger.info(
                    f"Successfully stored AST data for {parse_result.file_path}"
                )
                logger.debug(
                    f"Stored: {len(parse_result.symbols)} symbols, {len(parse_result.classes)} classes, {len(parse_result.imports)} imports"
                )
            else:
                logger.warning(
                    f"Partial failure storing AST data for {parse_result.file_path}"
                )

            return success

        except Exception as e:
            logger.error(
                f"Error storing parse result for {parse_result.file_path}: {e}",
                exc_info=True,
            )
            self.stats["errors"] += 1
            return False

    async def _store_symbols(self, parse_result: ParseResult, file_hash: str) -> bool:
        """Store symbols in vector database."""
        if not parse_result.symbols:
            return True

        client = get_qdrant_client()
        if not client:
            return False

        try:
            points = []

            for symbol in parse_result.symbols:
                # Generate search text for embedding
                search_text = self._generate_symbol_search_text(symbol, parse_result)

                # Generate embedding
                embedding = await self.embedding_service.generate_embedding(search_text)
                if not embedding:
                    logger.warning(
                        f"Failed to generate embedding for symbol: {symbol.name}"
                    )
                    continue

                # Create payload
                payload = SymbolEmbeddingPayload(
                    file_path=str(parse_result.file_path),
                    symbol_name=symbol.name,
                    symbol_type=symbol.type,
                    language=parse_result.language.value,
                    line_start=symbol.line_start,
                    line_end=symbol.line_end,
                    signature=symbol.signature,
                    docstring=symbol.docstring,
                    parameters=[p.to_dict() for p in symbol.parameters],
                    return_type=symbol.return_type,
                    decorators=symbol.decorators,
                    parent_class=symbol.parent_class,
                    visibility=symbol.visibility,
                    is_static=symbol.is_static,
                    is_abstract=symbol.is_abstract,
                    is_async=symbol.is_async,
                    file_hash=file_hash,
                    search_text=search_text,
                )

                # Create point
                point_id = self._generate_symbol_id(parse_result.file_path, symbol)
                point = models.PointStruct(
                    id=point_id, vector=embedding, payload=payload.to_dict()
                )
                points.append(point)

            # Batch upsert
            if points:
                client.upsert(collection_name=self.symbol_collection, points=points)
                self.stats["symbols_stored"] += len(points)
                logger.debug(
                    f"Stored {len(points)} symbols for {parse_result.file_path}"
                )

            return True

        except Exception as e:
            logger.error(f"Error storing symbols: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def _store_classes(self, parse_result: ParseResult, file_hash: str) -> bool:
        """Store classes in vector database."""
        if not parse_result.classes:
            return True

        client = get_qdrant_client()
        if not client:
            return False

        try:
            points = []

            for class_info in parse_result.classes:
                # Generate search text for embedding
                search_text = self._generate_class_search_text(class_info, parse_result)

                # Generate embedding
                embedding = await self.embedding_service.generate_embedding(search_text)
                if not embedding:
                    logger.warning(
                        f"Failed to generate embedding for class: {class_info.name}"
                    )
                    continue

                # Create payload
                payload = ClassEmbeddingPayload(
                    file_path=str(parse_result.file_path),
                    class_name=class_info.name,
                    language=parse_result.language.value,
                    line_start=class_info.line_start,
                    line_end=class_info.line_end,
                    docstring=class_info.docstring,
                    base_classes=class_info.base_classes,
                    interfaces=class_info.interfaces,
                    methods=class_info.methods,
                    fields=class_info.fields,
                    decorators=class_info.decorators,
                    generic_params=class_info.generic_params,
                    visibility=class_info.visibility,
                    is_abstract=class_info.is_abstract,
                    is_interface=class_info.is_interface,
                    is_static=class_info.is_static,
                    file_hash=file_hash,
                    search_text=search_text,
                )

                # Create point
                point_id = self._generate_class_id(parse_result.file_path, class_info)
                point = models.PointStruct(
                    id=point_id, vector=embedding, payload=payload.to_dict()
                )
                points.append(point)

            # Batch upsert
            if points:
                client.upsert(collection_name=self.class_collection, points=points)
                self.stats["classes_stored"] += len(points)
                logger.debug(
                    f"Stored {len(points)} classes for {parse_result.file_path}"
                )

            return True

        except Exception as e:
            logger.error(f"Error storing classes: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def _store_imports(self, parse_result: ParseResult, file_hash: str) -> bool:
        """Store imports in vector database."""
        if not parse_result.imports:
            return True

        client = get_qdrant_client()
        if not client:
            return False

        try:
            points = []

            for import_info in parse_result.imports:
                # Generate search text for embedding
                search_text = self._generate_import_search_text(
                    import_info, parse_result
                )

                # Generate embedding
                embedding = await self.embedding_service.generate_embedding(search_text)
                if not embedding:
                    logger.warning(
                        f"Failed to generate embedding for import: {import_info.module}"
                    )
                    continue

                # Create payload
                payload = ImportEmbeddingPayload(
                    file_path=str(parse_result.file_path),
                    module=import_info.module,
                    language=parse_result.language.value,
                    import_type=import_info.import_type,
                    alias=import_info.alias,
                    items=import_info.items,
                    is_wildcard=import_info.is_wildcard,
                    line=import_info.line,
                    file_hash=file_hash,
                    search_text=search_text,
                )

                # Create point
                point_id = self._generate_import_id(parse_result.file_path, import_info)
                point = models.PointStruct(
                    id=point_id, vector=embedding, payload=payload.to_dict()
                )
                points.append(point)

            # Batch upsert
            if points:
                client.upsert(collection_name=self.import_collection, points=points)
                self.stats["imports_stored"] += len(points)
                logger.debug(
                    f"Stored {len(points)} imports for {parse_result.file_path}"
                )

            return True

        except Exception as e:
            logger.error(f"Error storing imports: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    def _generate_symbol_search_text(
        self, symbol: SymbolInfo, parse_result: ParseResult
    ) -> str:
        """Generate optimized search text for symbol embedding."""
        parts = []

        # Language and type context
        parts.append(f"Language: {parse_result.language.value}")
        parts.append(f"Type: {symbol.type}")

        # Symbol name and signature
        parts.append(f"Name: {symbol.name}")
        if symbol.signature:
            parts.append(f"Signature: {symbol.signature}")

        # Parameters
        if symbol.parameters:
            param_names = [p.name for p in symbol.parameters]
            parts.append(f"Parameters: {', '.join(param_names)}")

        # Return type
        if symbol.return_type:
            parts.append(f"Returns: {symbol.return_type}")

        # Documentation
        if symbol.docstring:
            parts.append(f"Documentation: {symbol.docstring}")

        # Context
        if symbol.parent_class:
            parts.append(f"Class: {symbol.parent_class}")

        # Modifiers
        modifiers = []
        if symbol.is_async:
            modifiers.append("async")
        if symbol.is_static:
            modifiers.append("static")
        if symbol.is_abstract:
            modifiers.append("abstract")
        if symbol.visibility:
            modifiers.append(symbol.visibility)
        if modifiers:
            parts.append(f"Modifiers: {', '.join(modifiers)}")

        # Decorators
        if symbol.decorators:
            parts.append(f"Decorators: {', '.join(symbol.decorators)}")

        return " | ".join(parts)

    def _generate_class_search_text(
        self, class_info: ClassInfo, parse_result: ParseResult
    ) -> str:
        """Generate optimized search text for class embedding."""
        parts = []

        # Language and type context
        parts.append(f"Language: {parse_result.language.value}")
        if class_info.is_interface:
            parts.append("Type: interface")
        else:
            parts.append("Type: class")

        # Class name
        parts.append(f"Name: {class_info.name}")

        # Inheritance
        if class_info.base_classes:
            parts.append(f"Extends: {', '.join(class_info.base_classes)}")

        # Interfaces
        if class_info.interfaces:
            parts.append(f"Implements: {', '.join(class_info.interfaces)}")

        # Methods and fields
        if class_info.methods:
            parts.append(f"Methods: {', '.join(class_info.methods)}")
        if class_info.fields:
            parts.append(f"Fields: {', '.join(class_info.fields)}")

        # Documentation
        if class_info.docstring:
            parts.append(f"Documentation: {class_info.docstring}")

        # Modifiers
        modifiers = []
        if class_info.is_abstract:
            modifiers.append("abstract")
        if class_info.is_static:
            modifiers.append("static")
        if class_info.visibility:
            modifiers.append(class_info.visibility)
        if modifiers:
            parts.append(f"Modifiers: {', '.join(modifiers)}")

        # Decorators
        if class_info.decorators:
            parts.append(f"Decorators: {', '.join(class_info.decorators)}")

        return " | ".join(parts)

    def _generate_import_search_text(
        self, import_info: ImportInfo, parse_result: ParseResult
    ) -> str:
        """Generate optimized search text for import embedding."""
        parts = []

        # Language context
        parts.append(f"Language: {parse_result.language.value}")
        parts.append(f"Import: {import_info.import_type}")

        # Module
        parts.append(f"Module: {import_info.module}")

        # Alias
        if import_info.alias:
            parts.append(f"Alias: {import_info.alias}")

        # Items (for from imports)
        if import_info.items:
            parts.append(f"Items: {', '.join(import_info.items)}")

        # Wildcard
        if import_info.is_wildcard:
            parts.append("Wildcard: true")

        return " | ".join(parts)

    def _generate_symbol_id(self, file_path: Path, symbol: SymbolInfo) -> str:
        """
        Generate unique UUID for symbol.

        Uses UUID v5 (SHA-1 hash) to create a consistent UUID for the same symbol.
        This ensures Qdrant compatibility (requires UUID or unsigned integer as point ID).
        """
        content = f"{file_path}:{symbol.name}:{symbol.type}:{symbol.line_start}"
        return str(uuid.uuid5(AST_NAMESPACE, content))

    def _generate_class_id(self, file_path: Path, class_info: ClassInfo) -> str:
        """
        Generate unique UUID for class.

        Uses UUID v5 (SHA-1 hash) to create a consistent UUID for the same class.
        This ensures Qdrant compatibility (requires UUID or unsigned integer as point ID).
        """
        content = f"{file_path}:{class_info.name}:class:{class_info.line_start}"
        return str(uuid.uuid5(AST_NAMESPACE, content))

    def _generate_import_id(self, file_path: Path, import_info: ImportInfo) -> str:
        """
        Generate unique UUID for import.

        Uses UUID v5 (SHA-1 hash) to create a consistent UUID for the same import.
        This ensures Qdrant compatibility (requires UUID or unsigned integer as point ID).
        """
        content = f"{file_path}:{import_info.module}:{import_info.import_type}:{import_info.line or 0}"
        return str(uuid.uuid5(AST_NAMESPACE, content))

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file content for cache invalidation."""
        try:
            content = file_path.read_bytes()
            return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}: {e}")
            return ""

    def get_stats(self) -> Dict[str, Any]:
        """Get AST vector store statistics."""
        return {
            "symbol_collection": self.symbol_collection,
            "class_collection": self.class_collection,
            "import_collection": self.import_collection,
            "symbols_stored": self.stats["symbols_stored"],
            "classes_stored": self.stats["classes_stored"],
            "imports_stored": self.stats["imports_stored"],
            "searches_performed": self.stats["searches_performed"],
            "errors": self.stats["errors"],
        }


# Global AST vector store instance
_global_ast_store: Optional[ASTVectorStore] = None


def get_ast_vector_store() -> ASTVectorStore:
    """Get the global AST vector store instance."""
    global _global_ast_store
    if _global_ast_store is None:
        _global_ast_store = ASTVectorStore()
    return _global_ast_store
