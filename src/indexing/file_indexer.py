"""
File Indexer

Multi-language file indexing with metadata extraction.
"""

import asyncio
import logging
import os
import sys
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone

from src.monitoring.metrics import metrics

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Import models module and expose forwarding functions so tests can patch either location
import src.indexing.models as _indexing_models


async def create_file_metadata(metadata: dict):
    """Create file metadata with graceful database failure handling"""
    try:
        return await _indexing_models.create_file_metadata(metadata)
    except Exception as e:
        logger.warning(f"Database unavailable for create_file_metadata: {e}. Continuing without metadata storage.")
        return None  # Graceful degradation - continue without DB


async def update_file_metadata(file_path: str, metadata: dict):
    """Update file metadata with graceful database failure handling"""
    try:
        return await _indexing_models.update_file_metadata(file_path, metadata)
    except Exception as e:
        logger.warning(f"Database unavailable for update_file_metadata: {e}. Continuing without metadata storage.")
        return None  # Graceful degradation - continue without DB


async def get_file_metadata(file_path: str):
    """Get file metadata with graceful database failure handling"""
    try:
        return await _indexing_models.get_file_metadata(file_path)
    except Exception as e:
        logger.warning(f"Database unavailable for get_file_metadata: {e}. Assuming file not in metadata DB.")
        return None  # Graceful degradation - assume file doesn't exist in DB


async def delete_file_metadata(file_path: str):
    """Delete file metadata with graceful database failure handling"""
    try:
        return await _indexing_models.delete_file_metadata(file_path)
    except Exception as e:
        logger.warning(f"Database unavailable for delete_file_metadata: {e}. Continuing without metadata deletion.")
        return False  # Graceful degradation - continue without DB


logger = logging.getLogger(__name__)


class FileIndexer:
    """
    File Indexer Service

    Handles file type detection, metadata extraction, and indexing operations.
    """

    # Supported file types and their language mappings
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".hpp": "cpp",
        ".h": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
    }

    def __init__(self):
        """Initialize file indexer"""
        logger.info("FileIndexer initialized")
        self.stats = {"total_indexed": 0, "total_errors": 0, "by_language": {}}

    async def detect_file_type(self, file_path: str) -> Optional[str]:
        """
        Detect file type/language from file extension

        Args:
            file_path: Path to file

        Returns:
            str: Language name or None if unsupported
        """
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()

        language = self.LANGUAGE_EXTENSIONS.get(extension)

        if language:
            logger.debug(f"Detected language '{language}' for file: {file_path}")
        else:
            logger.debug(f"Unsupported file type '{extension}' for file: {file_path}")

        return language

    async def extract_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from file

        Args:
            file_path: Path to file

        Returns:
            dict: File metadata or None if file doesn't exist
        """
        try:
            path_obj = Path(file_path)

            if not path_obj.exists():
                logger.warning(f"File does not exist: {file_path}")
                return None

            # Get file stats
            stat_info = path_obj.stat()

            # Detect language
            language = await self.detect_file_type(file_path)

            if not language:
                logger.debug(f"Skipping unsupported file: {file_path}")
                return None

            # Extract metadata
            metadata = {
                "file_path": str(path_obj.absolute()),
                "file_name": path_obj.name,
                "file_type": language,
                "size": stat_info.st_size,
                "modified_time": datetime.fromtimestamp(stat_info.st_mtime),
                "created_time": datetime.fromtimestamp(stat_info.st_ctime),
                "extension": path_obj.suffix,
            }

            logger.debug(f"Extracted metadata for {file_path}: {metadata}")
            return metadata

        except Exception as e:
            logger.error(
                f"Error extracting metadata from {file_path}: {e}", exc_info=True
            )
            return None

    async def index_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Index a single file

        Args:
            file_path: Path to file to index

        Returns:
            dict: File metadata if successful, None otherwise
        """
        logger.info(f"Indexing file: {file_path}")

        # Metrics
        c_files = metrics.counter(
            "indexing_files_total", "Indexed files", ("status", "lang")
        )
        h_file = metrics.histogram("indexing_file_seconds", "Indexing file latency")
        _t0 = asyncio.get_event_loop().time()

        try:
            # Extract metadata
            metadata = await self.extract_metadata(file_path)

            if not metadata:
                try:
                    h_file.labels().observe(asyncio.get_event_loop().time() - _t0)
                    c_files.labels("skipped", "unknown").inc()
                except Exception:
                    pass
                return None

            # Add indexing timestamp
            metadata["indexed_time"] = datetime.now(timezone.utc)
            metadata["status"] = "indexed"

            # Store in database (functions imported at module level for testability)
            existing = await get_file_metadata(file_path)
            if existing:
                # Update existing record
                await update_file_metadata(file_path, metadata)
                logger.info(f"Updated existing metadata for {file_path}")
            else:
                # Create new record
                await create_file_metadata(metadata)
                logger.info(f"Created new metadata for {file_path}")

            # Generate and store vector embedding
            try:
                from src.vector_db.embeddings import generate_code_embedding
                from src.vector_db.vector_store import upsert_vector

                # Read file content for embedding
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Generate embedding
                embedding = await generate_code_embedding(
                    code=content, file_path=file_path, language=metadata["file_type"]
                )

                if embedding:
                    # Store vector with metadata
                    vector_payload = {
                        "file_path": metadata["file_path"],
                        "file_name": metadata["file_name"],
                        "file_type": metadata["file_type"],
                        "size": metadata["size"],
                        "indexed_time": metadata["indexed_time"].isoformat(),
                    }

                    await upsert_vector(
                        id=metadata["file_path"],
                        vector=embedding,
                        payload=vector_payload,
                    )

                    logger.info(f"Generated and stored embedding for {file_path}")
                else:
                    logger.warning(f"Failed to generate embedding for {file_path}")

            except Exception as e:
                logger.error(
                    f"Error generating embedding for {file_path}: {e}", exc_info=True
                )

            # Update stats
            self.stats["total_indexed"] += 1
            language = metadata["file_type"]
            self.stats["by_language"][language] = (
                self.stats["by_language"].get(language, 0) + 1
            )
            try:
                h_file.labels().observe(asyncio.get_event_loop().time() - _t0)
                c_files.labels("success", language).inc()
            except Exception:
                pass

            logger.info(f"Successfully indexed {file_path} as {language}")
            return metadata

        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}", exc_info=True)
            self.stats["total_errors"] += 1
            try:
                h_file.labels().observe(asyncio.get_event_loop().time() - _t0)
                c_files.labels("error", "unknown").inc()
            except Exception:
                pass
            return None

    async def remove_file(self, file_path: str) -> bool:
        """
        Remove file from index

        Args:
            file_path: Path to file to remove

        Returns:
            bool: True if successful
        """
        logger.info(f"Removing file from index: {file_path}")

        try:
            # Remove from database (function imported at module level for testability)
            success = await delete_file_metadata(file_path)

            # Remove from vector database
            try:
                from src.vector_db.vector_store import delete_vector

                await delete_vector(file_path)
                logger.info(f"Removed vector for {file_path}")
            except Exception as e:
                logger.error(f"Error removing vector for {file_path}: {e}")

            if success:
                logger.info(f"Successfully removed {file_path} from index")
            else:
                logger.warning(f"File {file_path} not found in index")

            return success

        except Exception as e:
            logger.error(f"Error removing file {file_path}: {e}", exc_info=True)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get indexing statistics

        Returns:
            dict: Indexing statistics
        """
        return {
            "total_indexed": self.stats["total_indexed"],
            "total_errors": self.stats["total_errors"],
            "by_language": self.stats["by_language"],
            "supported_languages": list(set(self.LANGUAGE_EXTENSIONS.values())),
        }

    def is_supported(self, file_path: str) -> bool:
        """
        Check if file type is supported

        Args:
            file_path: Path to file

        Returns:
            bool: True if file type is supported
        """
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()
        return extension in self.LANGUAGE_EXTENSIONS


# Global file indexer instance
file_indexer = FileIndexer()


async def index_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Index a file (entry point for integration)

    Args:
        file_path: Path to file to index

    Returns:
        dict: File metadata if successful
    """
    return await file_indexer.index_file(file_path)


async def remove_file(file_path: str) -> bool:
    """
    Remove file from index (entry point for integration)

    Args:
        file_path: Path to file to remove

    Returns:
        bool: True if successful
    """
    return await file_indexer.remove_file(file_path)


def get_indexer_stats() -> Dict[str, Any]:
    """Get indexer statistics (entry point for status endpoints)"""
    return file_indexer.get_stats()
