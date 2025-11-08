"""
AST Indexer

Integration layer that connects the parsing pipeline with AST vector storage.
Handles indexing of parsed AST metadata into Qdrant collections.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from src.parsing.parser import get_parser
from src.vector_db.ast_store import get_ast_vector_store
from src.indexing.file_indexer import FileIndexer

logger = logging.getLogger(__name__)


class ASTIndexer:
    """
    AST Indexer

    Handles the complete pipeline from file parsing to AST metadata storage
    in vector database collections.
    """

    def __init__(self):
        """Initialize AST indexer."""
        self.parser = get_parser()
        self.ast_store = get_ast_vector_store()
        self.file_indexer = FileIndexer()

        self.stats = {
            "files_processed": 0,
            "files_indexed": 0,
            "unique_files_indexed": 0,
            "symbols_indexed": 0,
            "classes_indexed": 0,
            "imports_indexed": 0,
            "errors": 0,
            "total_processing_time_ms": 0.0,
        }

        self.indexed_files: set = set()  # Track unique files

        logger.info("ASTIndexer initialized")

    async def index_file(self, file_path: Path) -> bool:
        """
        Index a single file's AST metadata.

        Args:
            file_path: Path to the file to index

        Returns:
            bool: True if successful
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Check if file should be indexed
            language = await self.file_indexer.detect_file_type(str(file_path))
            if not language:
                logger.debug(f"Skipping unsupported file: {file_path}")
                return False

            # Parse the file
            logger.debug(f"Parsing file: {file_path}")
            parse_result = self.parser.parse(file_path)

            if not parse_result.parse_success:
                logger.warning(
                    f"Failed to parse {file_path}: {parse_result.parse_error}"
                )
                self.stats["errors"] += 1
                return False

            # Store AST metadata in vector database
            logger.debug(f"Storing AST metadata for: {file_path}")
            storage_success = await self.ast_store.store_parse_result(parse_result)

            if storage_success:
                # Update statistics
                self.stats["files_indexed"] += 1

                # Track unique files
                file_path_str = str(file_path)
                if file_path_str not in self.indexed_files:
                    self.indexed_files.add(file_path_str)
                    self.stats["unique_files_indexed"] += 1

                self.stats["symbols_indexed"] += len(parse_result.symbols)
                self.stats["classes_indexed"] += len(parse_result.classes)
                self.stats["imports_indexed"] += len(parse_result.imports)

                logger.info(f"Successfully indexed {file_path}")
                logger.debug(
                    f"Indexed: {len(parse_result.symbols)} symbols, {len(parse_result.classes)} classes, {len(parse_result.imports)} imports"
                )
            else:
                logger.error(f"Failed to store AST metadata for {file_path}")
                self.stats["errors"] += 1

            self.stats["files_processed"] += 1
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self.stats["total_processing_time_ms"] += processing_time

            return storage_success

        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}", exc_info=True)
            self.stats["errors"] += 1
            self.stats["files_processed"] += 1
            return False

    async def index_directory(
        self, directory_path: Path, recursive: bool = True
    ) -> Dict[str, Any]:
        """
        Index all supported files in a directory.

        Args:
            directory_path: Path to directory to index
            recursive: Whether to index subdirectories

        Returns:
            Dict with indexing results and statistics
        """
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Directory does not exist: {directory_path}")

        logger.info(
            f"Starting directory indexing: {directory_path} (recursive: {recursive})"
        )
        start_time = asyncio.get_event_loop().time()

        # Find all supported files
        files_to_index = []

        if recursive:
            for file_path in directory_path.rglob("*"):
                if file_path.is_file() and await self._should_index_file(file_path):
                    files_to_index.append(file_path)
        else:
            for file_path in directory_path.iterdir():
                if file_path.is_file() and await self._should_index_file(file_path):
                    files_to_index.append(file_path)

        logger.info(f"Found {len(files_to_index)} files to index")

        # Index files in batches
        batch_size = 10  # Process 10 files concurrently
        successful_indexes = 0

        for i in range(0, len(files_to_index), batch_size):
            batch = files_to_index[i : i + batch_size]

            # Process batch concurrently
            tasks = [self.index_file(file_path) for file_path in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful indexes
            for result in results:
                if result is True:
                    successful_indexes += 1
                elif isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")

            # Log progress
            progress = min(i + batch_size, len(files_to_index))
            logger.info(f"Processed {progress}/{len(files_to_index)} files")

        total_time = (asyncio.get_event_loop().time() - start_time) * 1000

        result = {
            "directory": str(directory_path),
            "files_found": len(files_to_index),
            "files_indexed": successful_indexes,
            "files_failed": len(files_to_index) - successful_indexes,
            "symbols_indexed": self.stats["symbols_indexed"],
            "classes_indexed": self.stats["classes_indexed"],
            "imports_indexed": self.stats["imports_indexed"],
            "total_time_ms": total_time,
            "recursive": recursive,
        }

        logger.info(
            f"Directory indexing completed: {successful_indexes}/{len(files_to_index)} files indexed in {total_time:.2f}ms"
        )
        return result

    async def _should_index_file(self, file_path: Path) -> bool:
        """Check if file should be indexed."""
        # Check file extension
        language = await self.file_indexer.detect_file_type(str(file_path))
        if not language:
            return False

        # Skip common exclude patterns
        exclude_patterns = [
            "__pycache__",
            ".git",
            ".venv",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            "target",  # Rust
            "build",
            "dist",
        ]

        file_str = str(file_path)
        for pattern in exclude_patterns:
            if pattern in file_str:
                return False

        return True

    async def reindex_file(self, file_path: Path) -> bool:
        """
        Reindex a file (useful when file content changes).

        Args:
            file_path: Path to file to reindex

        Returns:
            bool: True if successful
        """
        # For now, just index the file (Qdrant upsert will replace existing entries)
        return await self.index_file(file_path)

    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        avg_processing_time = 0.0
        if self.stats["files_processed"] > 0:
            avg_processing_time = (
                self.stats["total_processing_time_ms"] / self.stats["files_processed"]
            )

        return {
            "files_processed": self.stats["files_processed"],
            "files_indexed": self.stats["files_indexed"],
            "unique_files_indexed": self.stats["unique_files_indexed"],
            "symbols_indexed": self.stats["symbols_indexed"],
            "classes_indexed": self.stats["classes_indexed"],
            "imports_indexed": self.stats["imports_indexed"],
            "errors": self.stats["errors"],
            "average_processing_time_ms": avg_processing_time,
            "success_rate": self.stats["files_indexed"]
            / max(self.stats["files_processed"], 1),
        }

    def reset_stats(self):
        """Reset indexing statistics."""
        self.stats = {
            "files_processed": 0,
            "files_indexed": 0,
            "unique_files_indexed": 0,
            "symbols_indexed": 0,
            "classes_indexed": 0,
            "imports_indexed": 0,
            "errors": 0,
            "total_processing_time_ms": 0.0,
        }
        self.indexed_files.clear()


# Global AST indexer instance
_global_ast_indexer: Optional[ASTIndexer] = None


def get_ast_indexer() -> ASTIndexer:
    """Get the global AST indexer instance."""
    global _global_ast_indexer
    if _global_ast_indexer is None:
        _global_ast_indexer = ASTIndexer()
    return _global_ast_indexer
