"""
Multi-Root Vector Store

Per-project vector storage with isolated collections for workspace-wide search.
"""

import logging
from typing import Dict, List, Any, Optional
from qdrant_client.http import models

from src.vector_db.qdrant_client import get_qdrant_client
from src.config.settings import settings

logger = logging.getLogger(__name__)


class MultiRootVectorStore:
    """
    Multi-Root Vector Store

    Manages per-project vector collections for workspace-wide semantic search
    with collection isolation and cross-project search capabilities.
    """

    def __init__(self):
        """Initialize multi-root vector store"""
        self.collections: Dict[str, str] = {}  # project_id -> collection_name
        self.stats = {
            "collections_created": 0,
            "vectors_stored": 0,
            "searches_performed": 0,
            "errors": 0,
        }
        logger.info("MultiRootVectorStore initialized")

    async def ensure_project_collection(
        self, project_id: str, vector_size: Optional[int] = None
    ) -> bool:
        """
        Ensure collection exists for a project

        Args:
            project_id: Unique project identifier
            vector_size: Vector dimension (defaults to settings.qdrant_vector_size)

        Returns:
            bool: True if successful
        """
        if vector_size is None:
            vector_size = settings.qdrant_vector_size

        collection_name = f"project_{project_id}_vectors"
        client = get_qdrant_client()

        if not client:
            logger.error("Qdrant client not available")
            return False

        try:
            # Check if collection exists
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if collection_name in collection_names:
                # Verify vector dimensions
                collection_info = client.get_collection(collection_name)
                existing_dim = collection_info.config.params.vectors.size

                if existing_dim != vector_size:
                    logger.warning(
                        f"Collection {collection_name} has dimension mismatch "
                        f"(expected: {vector_size}, found: {existing_dim}). Recreating..."
                    )
                    # Delete and recreate
                    client.delete_collection(collection_name)
                else:
                    logger.debug(f"Collection {collection_name} already exists")
                    self.collections[project_id] = collection_name
                    return True

            # Create collection with project metadata in payload schema
            logger.info(f"Creating collection: {collection_name} (dimensions: {vector_size})")

            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size, distance=models.Distance.COSINE
                ),
            )

            # Store collection mapping
            self.collections[project_id] = collection_name
            self.stats["collections_created"] += 1

            logger.info(f"Created collection for project '{project_id}': {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Error ensuring collection for project {project_id}: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def add_vectors(
        self, project_id: str, vectors: List[Dict[str, Any]], project_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add vectors to a project's collection

        Args:
            project_id: Project identifier
            vectors: List of vector dictionaries with id, vector, payload
            project_metadata: Additional project metadata to include in payloads

        Returns:
            bool: True if successful
        """
        if project_id not in self.collections:
            logger.error(f"Project {project_id} collection not initialized")
            return False

        collection_name = self.collections[project_id]
        client = get_qdrant_client()

        if not client:
            logger.error("Qdrant client not available")
            return False

        try:
            from src.vector_db.vector_store import VectorStore

            # Enhance payloads with project metadata
            enhanced_vectors = []
            for vector_data in vectors:
                payload = vector_data.get("payload", {}).copy()
                payload["project_id"] = project_id

                if project_metadata:
                    payload["project_name"] = project_metadata.get("name", project_id)
                    payload["project_type"] = project_metadata.get("type", "unknown")

                # Generate deterministic UUID for the point
                point_id = VectorStore._generate_point_id(vector_data["id"])

                enhanced_vectors.append({
                    "id": point_id,
                    "vector": vector_data["vector"],
                    "payload": payload,
                })

            # Batch upsert
            points = [
                models.PointStruct(id=v["id"], vector=v["vector"], payload=v["payload"])
                for v in enhanced_vectors
            ]

            client.upsert(collection_name=collection_name, points=points)

            self.stats["vectors_stored"] += len(vectors)
            logger.debug(f"Added {len(vectors)} vectors to project '{project_id}'")
            return True

        except Exception as e:
            logger.error(f"Error adding vectors to project {project_id}: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def search_project(
        self,
        project_id: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search within a single project

        Args:
            project_id: Project identifier
            query_vector: Query embedding vector
            limit: Maximum results
            score_threshold: Minimum similarity score
            filter_conditions: Optional Qdrant filter conditions

        Returns:
            List of search results
        """
        if project_id not in self.collections:
            logger.error(f"Project {project_id} collection not found")
            return []

        collection_name = self.collections[project_id]
        client = get_qdrant_client()

        if not client:
            logger.error("Qdrant client not available")
            return []

        try:
            search_result = client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_conditions,
            )

            results = []
            for scored_point in search_result:
                result = {
                    "id": scored_point.id,
                    "score": scored_point.score,
                    "payload": scored_point.payload,
                    "project_id": project_id,
                }
                results.append(result)

            self.stats["searches_performed"] += 1
            logger.debug(f"Project search returned {len(results)} results for '{project_id}'")
            return results

        except Exception as e:
            logger.error(f"Error searching project {project_id}: {e}", exc_info=True)
            self.stats["errors"] += 1
            return []

    async def search_workspace(
        self,
        query_vector: List[float],
        project_ids: Optional[List[str]] = None,
        limit: int = 50,
        score_threshold: float = 0.0,
        relationship_boost: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search across multiple projects with merged results

        Args:
            query_vector: Query embedding vector
            project_ids: List of project IDs to search (None = all projects)
            limit: Maximum total results
            score_threshold: Minimum similarity score
            relationship_boost: Optional boost factors per project_id for related projects

        Returns:
            Merged and sorted list of search results
        """
        # Determine which projects to search
        search_projects = project_ids if project_ids else list(self.collections.keys())

        if not search_projects:
            logger.warning("No projects to search in workspace")
            return []

        try:
            # Search each project in parallel (could use asyncio.gather for true parallelism)
            all_results = []

            for project_id in search_projects:
                # Get per-project limit (distribute total limit across projects)
                per_project_limit = max(limit // len(search_projects), 10)

                results = await self.search_project(
                    project_id=project_id,
                    query_vector=query_vector,
                    limit=per_project_limit,
                    score_threshold=score_threshold,
                )

                # Apply relationship boost if provided
                if relationship_boost and project_id in relationship_boost:
                    boost_factor = relationship_boost[project_id]
                    for result in results:
                        result["score"] *= boost_factor
                        result["boosted"] = True

                all_results.extend(results)

            # Sort by score (descending) and limit
            all_results.sort(key=lambda x: x["score"], reverse=True)
            merged_results = all_results[:limit]

            logger.info(
                f"Workspace search across {len(search_projects)} projects "
                f"returned {len(merged_results)} results"
            )
            return merged_results

        except Exception as e:
            logger.error(f"Error in workspace search: {e}", exc_info=True)
            self.stats["errors"] += 1
            return []

    async def delete_project_collection(self, project_id: str) -> bool:
        """
        Delete a project's collection

        Args:
            project_id: Project identifier

        Returns:
            bool: True if successful
        """
        if project_id not in self.collections:
            logger.warning(f"Project {project_id} collection not found")
            return False

        collection_name = self.collections[project_id]
        client = get_qdrant_client()

        if not client:
            logger.error("Qdrant client not available")
            return False

        try:
            client.delete_collection(collection_name)
            del self.collections[project_id]
            logger.info(f"Deleted collection for project '{project_id}': {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting collection for project {project_id}: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def get_collection_info(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get collection information for a project

        Args:
            project_id: Project identifier

        Returns:
            Collection info dict or None
        """
        if project_id not in self.collections:
            return None

        collection_name = self.collections[project_id]
        client = get_qdrant_client()

        if not client:
            return None

        try:
            collection_info = client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance.value,
                "points_count": collection_info.points_count,
                "status": collection_info.status.value,
            }

        except Exception as e:
            logger.error(f"Error getting collection info for {project_id}: {e}", exc_info=True)
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get multi-root vector store statistics"""
        return {
            "collections": len(self.collections),
            "project_ids": list(self.collections.keys()),
            "collections_created": self.stats["collections_created"],
            "vectors_stored": self.stats["vectors_stored"],
            "searches_performed": self.stats["searches_performed"],
            "errors": self.stats["errors"],
        }
