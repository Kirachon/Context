"""
Vector Store Service

Handles vector storage and retrieval operations with Qdrant.
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

    async def ensure_collection(self, vector_size: int = 384) -> bool:
        """
        Ensure collection exists, create if not

        Args:
            vector_size: Dimension of vectors

        Returns:
            bool: True if collection exists or was created
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
                logger.debug(f"Collection {self.collection_name} already exists")
                return True

            # Create collection
            logger.info(f"Creating collection: {self.collection_name}")

            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size, distance=models.Distance.COSINE
                ),
            )

            logger.info(f"Collection {self.collection_name} created successfully")
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
            id: Unique identifier for the vector
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
            # Ensure collection exists
            if not await self.ensure_collection(len(vector)):
                return False

            # Prepare point
            point = models.PointStruct(id=id, vector=vector, payload=payload)

            # Upsert point
            client.upsert(collection_name=self.collection_name, points=[point])

            self.stats["vectors_stored"] += 1
            logger.debug(f"Vector upserted successfully: {id}")
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
            # Ensure collection exists (use first vector's dimension)
            first_vector = vectors[0]["vector"]
            if not await self.ensure_collection(len(first_vector)):
                return False

            # Prepare points
            points = []
            for vector_data in vectors:
                point = models.PointStruct(
                    id=vector_data["id"],
                    vector=vector_data["vector"],
                    payload=vector_data.get("payload", {}),
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
            id: Vector ID to delete

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        try:
            # Delete point
            client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[id]),
            )

            self.stats["vectors_deleted"] += 1
            logger.debug(f"Vector deleted successfully: {id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting vector {id}: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def delete_batch(self, ids: List[str]) -> bool:
        """
        Delete multiple vectors by IDs

        Args:
            ids: List of vector IDs to delete

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
            # Batch delete
            client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=ids),
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
