"""
Collection Management Service

Manages Qdrant collections for different codebases.
"""

import logging
import os
import sys
from typing import List, Optional, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from qdrant_client.http import models
from src.vector_db.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)


class CollectionManager:
    """
    Collection Manager

    Manages Qdrant collections with per-codebase strategy.
    """

    def __init__(self):
        """Initialize collection manager"""
        self.default_vector_size = 384  # all-MiniLM-L6-v2 dimension
        self.default_distance = models.Distance.COSINE

        logger.info("CollectionManager initialized")

    async def create_collection(
        self, name: str, vector_size: int = None, distance: models.Distance = None
    ) -> bool:
        """
        Create a new collection

        Args:
            name: Collection name
            vector_size: Vector dimension
            distance: Distance metric

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        vector_size = vector_size or self.default_vector_size
        distance = distance or self.default_distance

        try:
            # Check if collection already exists
            if await self.collection_exists(name):
                logger.warning(f"Collection {name} already exists")
                return True

            logger.info(
                f"Creating collection: {name} (size: {vector_size}, distance: {distance.value})"
            )

            # Create collection
            client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=vector_size, distance=distance),
            )

            logger.info(f"Collection {name} created successfully")
            return True

        except Exception as e:
            logger.error(f"Error creating collection {name}: {e}", exc_info=True)
            return False

    async def delete_collection(self, name: str) -> bool:
        """
        Delete a collection

        Args:
            name: Collection name

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        try:
            # Check if collection exists
            if not await self.collection_exists(name):
                logger.warning(f"Collection {name} does not exist")
                return True

            logger.info(f"Deleting collection: {name}")

            # Delete collection
            client.delete_collection(collection_name=name)

            logger.info(f"Collection {name} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Error deleting collection {name}: {e}", exc_info=True)
            return False

    async def collection_exists(self, name: str) -> bool:
        """
        Check if collection exists

        Args:
            name: Collection name

        Returns:
            bool: True if collection exists
        """
        client = get_qdrant_client()
        if not client:
            return False

        try:
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]
            return name in collection_names

        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    async def list_collections(self) -> List[str]:
        """
        List all collections

        Returns:
            List of collection names
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return []

        try:
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]

            logger.debug(f"Found {len(collection_names)} collections")
            return collection_names

        except Exception as e:
            logger.error(f"Error listing collections: {e}", exc_info=True)
            return []

    async def get_collection_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get collection statistics

        Args:
            name: Collection name

        Returns:
            dict: Collection statistics or None if error
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return None

        try:
            collection_info = client.get_collection(name)

            stats = {
                "name": name,
                "status": collection_info.status.value,
                "points_count": collection_info.points_count,
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance.value,
                "indexed_vectors_count": collection_info.indexed_vectors_count or 0,
                "segments_count": (
                    len(collection_info.segments) if collection_info.segments else 0
                ),
            }

            logger.debug(f"Retrieved stats for collection {name}")
            return stats

        except Exception as e:
            logger.error(
                f"Error getting collection stats for {name}: {e}", exc_info=True
            )
            return None

    async def get_all_collection_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all collections

        Returns:
            List of collection statistics
        """
        collections = await self.list_collections()
        stats = []

        for collection_name in collections:
            collection_stats = await self.get_collection_stats(collection_name)
            if collection_stats:
                stats.append(collection_stats)

        return stats

    async def cleanup_empty_collections(self) -> int:
        """
        Clean up collections with no vectors

        Returns:
            int: Number of collections cleaned up
        """
        collections = await self.list_collections()
        cleaned_count = 0

        for collection_name in collections:
            stats = await self.get_collection_stats(collection_name)

            if stats and stats["points_count"] == 0:
                logger.info(f"Cleaning up empty collection: {collection_name}")

                if await self.delete_collection(collection_name):
                    cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} empty collections")
        return cleaned_count

    def generate_collection_name(self, codebase_path: str) -> str:
        """
        Generate collection name for codebase

        Args:
            codebase_path: Path to codebase

        Returns:
            str: Collection name
        """
        # Use basename of path and sanitize
        basename = os.path.basename(codebase_path.rstrip("/\\"))

        # Replace invalid characters
        sanitized = basename.replace(" ", "_").replace("-", "_")
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")

        # Ensure it starts with letter
        if not sanitized or not sanitized[0].isalpha():
            sanitized = f"codebase_{sanitized}"

        # Add prefix for context
        collection_name = f"context_{sanitized.lower()}"

        return collection_name

    async def ensure_codebase_collection(self, codebase_path: str) -> Optional[str]:
        """
        Ensure collection exists for codebase

        Args:
            codebase_path: Path to codebase

        Returns:
            str: Collection name if successful, None otherwise
        """
        collection_name = self.generate_collection_name(codebase_path)

        if await self.create_collection(collection_name):
            return collection_name

        return None


# Global collection manager instance
collection_manager = CollectionManager()


async def create_collection(name: str, vector_size: int = None) -> bool:
    """Create collection (entry point for integration)"""
    return await collection_manager.create_collection(name, vector_size)


async def delete_collection(name: str) -> bool:
    """Delete collection (entry point for integration)"""
    return await collection_manager.delete_collection(name)


async def list_collections() -> List[str]:
    """List collections (entry point for integration)"""
    return await collection_manager.list_collections()


async def get_collection_stats(name: str) -> Optional[Dict[str, Any]]:
    """Get collection stats (entry point for integration)"""
    return await collection_manager.get_collection_stats(name)


def get_collection_manager() -> CollectionManager:
    """Get collection manager instance"""
    return collection_manager
