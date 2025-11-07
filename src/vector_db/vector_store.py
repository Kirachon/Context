"""
Vector Store Service

Handles vector storage and retrieval operations with Qdrant.
"""

import logging
import os
import sys
import uuid
from typing import List, Optional, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from qdrant_client.http import models
from src.vector_db.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)

# UUID namespace for generating deterministic UUIDs from file paths
# This ensures the same file path always generates the same UUID
FILE_PATH_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class VectorStore:
    """
    Vector Store Service

    Manages vector storage and retrieval operations with Qdrant.
    """

    def __init__(self, collection_name: str = "context_vectors"):
        """
        Initialize vector store

        Args:
            collection_name: Name of the Qdrant collection
        """
        self.collection_name = collection_name
        self.stats = {
            "vectors_stored": 0,
            "vectors_retrieved": 0,
            "vectors_deleted": 0,
            "batch_operations": 0,
            "errors": 0,
        }

        logger.info(f"VectorStore initialized for collection: {collection_name}")

    @staticmethod
    def _generate_point_id(file_path: str) -> str:
        """
        Generate a deterministic UUID from a file path

        Uses UUID v5 (SHA-1 hash) to create a consistent UUID for the same file path.
        This ensures the same file always gets the same UUID, enabling idempotent upserts.

        Args:
            file_path: File path to generate UUID from

        Returns:
            str: UUID string
        """
        return str(uuid.uuid5(FILE_PATH_NAMESPACE, file_path))

    async def ensure_collection(self, vector_size: int = 384, auto_fix_mismatch: bool = True) -> bool:
        """
        Ensure collection exists with correct vector dimensions

        If collection exists but has wrong dimensions, it will be recreated
        if auto_fix_mismatch is True (default).

        Args:
            vector_size: Dimension of vectors (default: 384 for all-MiniLM-L6-v2)
            auto_fix_mismatch: Automatically recreate collection if dimensions don't match

        Returns:
            bool: True if collection exists or was created with correct dimensions
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        try:
            # Check if collection exists
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name in collection_names:
                # Collection exists - verify dimensions match
                collection_info = client.get_collection(self.collection_name)
                existing_dim = collection_info.config.params.vectors.size

                if existing_dim == vector_size:
                    logger.debug(f"Collection {self.collection_name} exists with correct dimensions ({vector_size})")
                    return True

                # Dimension mismatch detected
                logger.warning(
                    f"⚠️ Vector dimension mismatch detected in collection '{self.collection_name}'"
                )
                logger.warning(f"   Expected: {vector_size} dimensions (current embedding model)")
                logger.warning(f"   Found: {existing_dim} dimensions (existing collection)")

                if not auto_fix_mismatch:
                    logger.error(
                        f"Collection dimension mismatch cannot be fixed automatically (auto_fix_mismatch=False)"
                    )
                    return False

                # Get point count before deletion
                point_count = collection_info.points_count

                logger.warning(
                    f"🔧 Auto-fixing dimension mismatch: Recreating collection '{self.collection_name}'"
                )
                logger.warning(
                    f"   This will delete {point_count} existing vectors and recreate the collection"
                )
                logger.warning(
                    f"   Files will need to be re-indexed to populate the collection"
                )

                # Delete old collection
                client.delete_collection(self.collection_name)
                logger.info(f"Deleted collection '{self.collection_name}' with {point_count} vectors")

                # Fall through to create new collection with correct dimensions

            # Create collection with correct dimensions
            logger.info(f"Creating collection: {self.collection_name} (dimensions: {vector_size})")

            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size, distance=models.Distance.COSINE
                ),
            )

            logger.info(f"✅ Collection {self.collection_name} created successfully with {vector_size} dimensions")
            return True

        except Exception as e:
            logger.error(f"Error ensuring collection: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def upsert_vector(
        self, id: str, vector: List[float], payload: Dict[str, Any]
    ) -> bool:
        """
        Upsert a single vector

        Args:
            id: Unique identifier for the vector (typically a file path)
            vector: Vector embedding
            payload: Metadata payload

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        try:
            # Ensure collection exists with configured dimensions
            # DO NOT use len(vector) here - it will create collection with wrong dimensions!
            from src.config.settings import settings
            if not await self.ensure_collection(settings.qdrant_vector_size):
                return False

            # Validate vector dimension matches collection
            if len(vector) != settings.qdrant_vector_size:
                logger.error(
                    f"Vector dimension mismatch: vector has {len(vector)} dimensions, "
                    f"but collection expects {settings.qdrant_vector_size} dimensions"
                )
                return False

            # Generate deterministic UUID from the ID (file path)
            point_id = self._generate_point_id(id)

            # Ensure the original ID (file path) is stored in the payload for retrieval
            # This allows searching by file path even though we use UUIDs as point IDs
            enhanced_payload = payload.copy()
            if "file_path" not in enhanced_payload:
                enhanced_payload["file_path"] = id

            # Prepare point with UUID
            point = models.PointStruct(id=point_id, vector=vector, payload=enhanced_payload)

            # Upsert point
            client.upsert(collection_name=self.collection_name, points=[point])

            self.stats["vectors_stored"] += 1
            logger.debug(f"Vector upserted successfully: {id} (UUID: {point_id})")
            return True

        except Exception as e:
            logger.error(f"Error upserting vector {id}: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def upsert_batch(self, vectors: List[Dict[str, Any]]) -> bool:
        """
        Upsert multiple vectors in batch

        Args:
            vectors: List of vector dictionaries with id, vector, payload

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        if not vectors:
            logger.warning("Empty vector batch provided")
            return True

        try:
            # Ensure collection exists with configured dimensions
            # DO NOT use len(first_vector) here - it will create collection with wrong dimensions!
            from src.config.settings import settings
            if not await self.ensure_collection(settings.qdrant_vector_size):
                return False

            # Prepare points with UUID conversion
            points = []
            for vector_data in vectors:
                original_id = vector_data["id"]
                vector = vector_data["vector"]

                # Validate vector dimension matches collection
                if len(vector) != settings.qdrant_vector_size:
                    logger.error(
                        f"Vector dimension mismatch for {original_id}: vector has {len(vector)} dimensions, "
                        f"but collection expects {settings.qdrant_vector_size} dimensions"
                    )
                    continue  # Skip this vector

                # Generate deterministic UUID from the ID (file path)
                point_id = self._generate_point_id(original_id)

                # Ensure the original ID (file path) is stored in the payload
                payload = vector_data.get("payload", {}).copy()
                if "file_path" not in payload:
                    payload["file_path"] = original_id

                point = models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
                points.append(point)

            # Batch upsert
            client.upsert(collection_name=self.collection_name, points=points)

            self.stats["vectors_stored"] += len(vectors)
            self.stats["batch_operations"] += 1
            logger.info(f"Batch upserted {len(vectors)} vectors successfully")
            return True

        except Exception as e:
            logger.error(f"Error batch upserting vectors: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def search(
        self, query_vector: List[float], limit: int = 10, score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors

        Args:
            query_vector: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of search results with id, score, and payload
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return []

        try:
            # Search vectors
            search_result = client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )

            # Format results
            results = []
            for scored_point in search_result:
                result = {
                    "id": scored_point.id,
                    "score": scored_point.score,
                    "payload": scored_point.payload,
                }
                results.append(result)

            self.stats["vectors_retrieved"] += len(results)
            logger.debug(f"Search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error searching vectors: {e}", exc_info=True)
            self.stats["errors"] += 1
            return []

    async def delete_vector(self, id: str) -> bool:
        """
        Delete a vector by ID

        Args:
            id: Vector ID to delete (typically a file path)

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        try:
            # Convert file path to UUID
            point_id = self._generate_point_id(id)

            # Delete point
            client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[point_id]),
            )

            self.stats["vectors_deleted"] += 1
            logger.debug(f"Vector deleted successfully: {id} (UUID: {point_id})")
            return True

        except Exception as e:
            logger.error(f"Error deleting vector {id}: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def delete_batch(self, ids: List[str]) -> bool:
        """
        Delete multiple vectors by IDs

        Args:
            ids: List of vector IDs to delete (typically file paths)

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        if not ids:
            logger.warning("Empty ID list provided for deletion")
            return True

        try:
            # Convert file paths to UUIDs
            point_ids = [self._generate_point_id(id) for id in ids]

            # Batch delete
            client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=point_ids),
            )

            self.stats["vectors_deleted"] += len(ids)
            logger.info(f"Batch deleted {len(ids)} vectors successfully")
            return True

        except Exception as e:
            logger.error(f"Error batch deleting vectors: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def get_collection_info(self) -> Optional[Dict[str, Any]]:
        """
        Get collection information

        Returns:
            dict: Collection information or None if error
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return None

        try:
            collection_info = client.get_collection(self.collection_name)

            return {
                "name": collection_info.config.params.vectors.size,
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance.value,
                "points_count": collection_info.points_count,
                "status": collection_info.status.value,
            }

        except Exception as e:
            logger.error(f"Error getting collection info: {e}", exc_info=True)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics

        Returns:
            dict: Statistics
        """
        return {
            "collection_name": self.collection_name,
            "vectors_stored": self.stats["vectors_stored"],
            "vectors_retrieved": self.stats["vectors_retrieved"],
            "vectors_deleted": self.stats["vectors_deleted"],
            "batch_operations": self.stats["batch_operations"],
            "errors": self.stats["errors"],
        }


# Global vector store instance
vector_store = VectorStore()


async def upsert_vector(id: str, vector: List[float], payload: Dict[str, Any]) -> bool:
    """Upsert vector (entry point for integration)"""
    return await vector_store.upsert_vector(id, vector, payload)


async def search_vectors(
    query_vector: List[float], limit: int = 10
) -> List[Dict[str, Any]]:
    """Search vectors (entry point for integration)"""
    return await vector_store.search(query_vector, limit)


async def delete_vector(id: str) -> bool:
    """Delete vector (entry point for integration)"""
    return await vector_store.delete_vector(id)


def get_vector_store() -> VectorStore:
    """Get vector store instance"""
    return vector_store


def get_vector_stats() -> Dict[str, Any]:
    """Get vector statistics (entry point for status endpoints)"""
    return vector_store.get_stats()
