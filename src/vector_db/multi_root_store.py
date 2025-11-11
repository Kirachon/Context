"""
Multi-Root Vector Store

Manages separate Qdrant collections for multiple projects in a workspace,
enabling project-scoped and cross-project semantic search.

Architecture:
- Per-project collections (project_{project_id}_vectors)
- Project metadata stored with each vector
- Cross-collection search with result merging
- Collection lifecycle management
- Migration support from v1 single-collection
"""

import logging
import os
import sys
import uuid
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from src.vector_db.qdrant_client import get_qdrant_client
from src.config.settings import settings

logger = logging.getLogger(__name__)

# UUID namespace for generating deterministic UUIDs from file paths
# This ensures the same file path always generates the same UUID
FILE_PATH_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@dataclass
class ProjectMetadata:
    """Project metadata for vector storage"""
    project_id: str
    project_name: str
    project_type: Optional[str] = None
    language: Optional[str] = None


@dataclass
class VectorData:
    """Vector data with metadata"""
    id: str  # Typically file_path
    vector: List[float]
    file_path: str
    language: str
    chunk_index: int = 0
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchResult:
    """Cross-project search result"""
    id: str
    score: float
    file_path: str
    project_id: str
    project_name: str
    language: str
    chunk_index: int
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MultiRootVectorStore:
    """
    Multi-Root Vector Store

    Manages separate Qdrant collections for each project in a workspace.
    Enables project-scoped search and cross-project semantic search with
    result merging and ranking.
    """

    def __init__(self, vector_size: int = None):
        """
        Initialize multi-root vector store

        Args:
            vector_size: Dimension of vectors (defaults to settings.qdrant_vector_size)
        """
        self.vector_size = vector_size or settings.qdrant_vector_size
        self.collections: Dict[str, str] = {}  # project_id -> collection_name
        self.project_metadata: Dict[str, ProjectMetadata] = {}  # project_id -> metadata

        self.stats = {
            "projects_registered": 0,
            "collections_created": 0,
            "vectors_stored": 0,
            "vectors_retrieved": 0,
            "vectors_deleted": 0,
            "cross_project_searches": 0,
            "errors": 0,
        }

        logger.info(f"MultiRootVectorStore initialized (vector_size={self.vector_size})")

    @staticmethod
    def _generate_point_id(file_path: str, chunk_index: int = 0) -> str:
        """
        Generate a deterministic UUID from file path and chunk index

        Uses UUID v5 (SHA-1 hash) to create a consistent UUID for the same file path
        and chunk index. This ensures the same file chunk always gets the same UUID,
        enabling idempotent upserts.

        Args:
            file_path: File path to generate UUID from
            chunk_index: Chunk index within file (default: 0)

        Returns:
            str: UUID string
        """
        # Combine file path and chunk index for unique identification
        unique_key = f"{file_path}:chunk:{chunk_index}"
        return str(uuid.uuid5(FILE_PATH_NAMESPACE, unique_key))

    @staticmethod
    def _generate_collection_name(project_id: str) -> str:
        """
        Generate collection name for a project

        Format: project_{project_id}_vectors

        Args:
            project_id: Project identifier

        Returns:
            str: Collection name
        """
        # Sanitize project_id to ensure valid collection name
        sanitized_id = "".join(c if c.isalnum() or c == "_" else "_" for c in project_id)
        return f"project_{sanitized_id}_vectors"

    async def ensure_project_collection(
        self,
        project_id: str,
        project_name: str,
        project_type: Optional[str] = None,
        vector_size: Optional[int] = None,
        recreate: bool = False
    ) -> bool:
        """
        Ensure collection exists for a project

        Creates a new collection if it doesn't exist. If it exists, verifies
        vector dimensions match. If dimensions don't match and recreate=True,
        deletes and recreates the collection.

        Args:
            project_id: Project identifier
            project_name: Human-readable project name
            project_type: Project type (optional, e.g., "web_frontend", "api_server")
            vector_size: Vector dimension (defaults to self.vector_size)
            recreate: If True, recreate collection if dimensions mismatch

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        vector_size = vector_size or self.vector_size
        collection_name = self._generate_collection_name(project_id)

        try:
            # Check if collection exists
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if collection_name in collection_names:
                # Collection exists - verify dimensions
                collection_info = client.get_collection(collection_name)

                # Extract vector size (robust across single/multi-vector schemas)
                existing_dim = None
                try:
                    vectors_cfg = collection_info.config.params.vectors
                    existing_dim = getattr(vectors_cfg, 'size', None)

                    # Handle multi-vector schema
                    if existing_dim is None and isinstance(vectors_cfg, dict):
                        first = next(iter(vectors_cfg.values()), None)
                        if first:
                            existing_dim = getattr(first, 'size', None)
                except Exception as e:
                    logger.warning(f"Could not extract vector size: {e}")
                    existing_dim = None

                if existing_dim == vector_size:
                    logger.debug(
                        f"Collection {collection_name} exists with correct dimensions ({vector_size})"
                    )
                    # Register collection and metadata
                    self.collections[project_id] = collection_name
                    self.project_metadata[project_id] = ProjectMetadata(
                        project_id=project_id,
                        project_name=project_name,
                        project_type=project_type
                    )
                    return True

                # Dimension mismatch
                logger.warning(
                    f"⚠️ Vector dimension mismatch in collection '{collection_name}' "
                    f"(expected: {vector_size}, found: {existing_dim})"
                )

                if not recreate:
                    logger.error(
                        f"Collection dimension mismatch cannot be fixed automatically (recreate=False)"
                    )
                    return False

                # Get point count before deletion
                point_count = collection_info.points_count

                logger.warning(
                    f"🔧 Recreating collection '{collection_name}' "
                    f"(will delete {point_count} existing vectors)"
                )

                # Delete old collection
                client.delete_collection(collection_name)
                logger.info(f"Deleted collection '{collection_name}' with {point_count} vectors")

            # Create collection with project metadata schema
            logger.info(
                f"Creating collection: {collection_name} "
                f"(project: {project_name}, dimensions: {vector_size})"
            )

            # Create collection with payload indexing for efficient filtering
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                ),
            )

            # Create payload indexes for fast filtering
            # This enables efficient project-scoped queries
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name="project_id",
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name="file_path",
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name="language",
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name="chunk_index",
                    field_schema=models.PayloadSchemaType.INTEGER
                )
                logger.debug(f"Created payload indexes for {collection_name}")
            except Exception as e:
                # Non-critical - indexes are for performance optimization
                logger.warning(f"Could not create payload indexes: {e}")

            # Register collection and metadata
            self.collections[project_id] = collection_name
            self.project_metadata[project_id] = ProjectMetadata(
                project_id=project_id,
                project_name=project_name,
                project_type=project_type
            )

            self.stats["projects_registered"] += 1
            self.stats["collections_created"] += 1

            logger.info(
                f"✅ Collection {collection_name} created successfully "
                f"(project: {project_name}, vectors: {vector_size}D)"
            )
            return True

        except Exception as e:
            logger.error(f"Error ensuring project collection: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def delete_project_collection(self, project_id: str) -> bool:
        """
        Delete a project's collection

        Args:
            project_id: Project identifier

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        if project_id not in self.collections:
            logger.warning(f"Project {project_id} not registered")
            return True

        collection_name = self.collections[project_id]

        try:
            # Get collection info before deletion
            try:
                collection_info = client.get_collection(collection_name)
                point_count = collection_info.points_count
            except:
                point_count = 0

            logger.info(
                f"Deleting collection: {collection_name} "
                f"(project: {project_id}, vectors: {point_count})"
            )

            # Delete collection
            client.delete_collection(collection_name=collection_name)

            # Unregister
            del self.collections[project_id]
            if project_id in self.project_metadata:
                del self.project_metadata[project_id]

            logger.info(f"✅ Collection {collection_name} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Error deleting project collection: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def upsert_vectors(
        self,
        project_id: str,
        vectors: List[VectorData]
    ) -> bool:
        """
        Upsert multiple vectors for a project

        Args:
            project_id: Project identifier
            vectors: List of vector data objects

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        if project_id not in self.collections:
            logger.error(f"Project {project_id} not registered. Call ensure_project_collection first.")
            return False

        if not vectors:
            logger.warning("Empty vector list provided")
            return True

        collection_name = self.collections[project_id]
        project_meta = self.project_metadata[project_id]

        try:
            # Prepare points with project metadata
            points = []
            for vector_data in vectors:
                # Validate vector dimension
                if len(vector_data.vector) != self.vector_size:
                    logger.error(
                        f"Vector dimension mismatch for {vector_data.file_path}: "
                        f"vector has {len(vector_data.vector)} dimensions, "
                        f"but collection expects {self.vector_size} dimensions"
                    )
                    continue

                # Generate deterministic UUID
                point_id = self._generate_point_id(
                    vector_data.file_path,
                    vector_data.chunk_index
                )

                # Build payload with project metadata
                payload = {
                    "project_id": project_id,
                    "project_name": project_meta.project_name,
                    "file_path": vector_data.file_path,
                    "language": vector_data.language,
                    "chunk_index": vector_data.chunk_index,
                }

                # Add optional fields
                if project_meta.project_type:
                    payload["project_type"] = project_meta.project_type

                if vector_data.content:
                    payload["content"] = vector_data.content

                # Merge additional metadata
                if vector_data.metadata:
                    payload["metadata"] = vector_data.metadata

                point = models.PointStruct(
                    id=point_id,
                    vector=vector_data.vector,
                    payload=payload
                )
                points.append(point)

            if not points:
                logger.error("No valid vectors to upsert after validation")
                return False

            # Batch upsert
            client.upsert(
                collection_name=collection_name,
                points=points
            )

            self.stats["vectors_stored"] += len(points)
            logger.info(
                f"Upserted {len(points)} vectors for project {project_id} "
                f"(collection: {collection_name})"
            )
            return True

        except Exception as e:
            logger.error(f"Error upserting vectors: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def search_project(
        self,
        project_id: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search within a single project's collection

        Args:
            project_id: Project identifier
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Additional filter conditions (e.g., {"language": "python"})

        Returns:
            List of search results
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return []

        if project_id not in self.collections:
            logger.error(f"Project {project_id} not registered")
            return []

        collection_name = self.collections[project_id]

        try:
            # Build filter if provided
            query_filter = None
            if filter_conditions:
                must_conditions = []
                for key, value in filter_conditions.items():
                    must_conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
                query_filter = models.Filter(must=must_conditions)

            # Search
            search_result = client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter
            )

            # Format results
            results = []
            for scored_point in search_result:
                payload = scored_point.payload

                result = SearchResult(
                    id=str(scored_point.id),
                    score=scored_point.score,
                    file_path=payload.get("file_path", ""),
                    project_id=payload.get("project_id", project_id),
                    project_name=payload.get("project_name", ""),
                    language=payload.get("language", ""),
                    chunk_index=payload.get("chunk_index", 0),
                    content=payload.get("content"),
                    metadata=payload.get("metadata")
                )
                results.append(result)

            self.stats["vectors_retrieved"] += len(results)
            logger.debug(
                f"Search in project {project_id} returned {len(results)} results"
            )
            return results

        except Exception as e:
            logger.error(f"Error searching project: {e}", exc_info=True)
            self.stats["errors"] += 1
            return []

    async def search_workspace(
        self,
        query_vector: List[float],
        project_ids: List[str],
        limit: int = 50,
        score_threshold: float = 0.0,
        per_project_limit: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Search across multiple projects with merged results

        Performs parallel searches across specified projects and merges
        results by score, maintaining top-k overall.

        Args:
            query_vector: Query embedding vector
            project_ids: List of project IDs to search
            limit: Total number of results to return
            score_threshold: Minimum similarity score
            per_project_limit: Max results per project (defaults to limit)

        Returns:
            List of merged and ranked search results
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return []

        if not project_ids:
            logger.warning("No project IDs provided for workspace search")
            return []

        per_project_limit = per_project_limit or limit

        try:
            # Search each project collection
            all_results = []

            for project_id in project_ids:
                if project_id not in self.collections:
                    logger.warning(f"Project {project_id} not registered, skipping")
                    continue

                # Search this project
                project_results = await self.search_project(
                    project_id=project_id,
                    query_vector=query_vector,
                    limit=per_project_limit,
                    score_threshold=score_threshold
                )

                all_results.extend(project_results)

            # Merge and rank by score
            all_results.sort(key=lambda r: r.score, reverse=True)

            # Return top-k
            merged_results = all_results[:limit]

            self.stats["cross_project_searches"] += 1
            logger.info(
                f"Workspace search across {len(project_ids)} projects "
                f"returned {len(merged_results)} results "
                f"(from {len(all_results)} total)"
            )

            return merged_results

        except Exception as e:
            logger.error(f"Error searching workspace: {e}", exc_info=True)
            self.stats["errors"] += 1
            return []

    async def search_all(
        self,
        query_vector: List[float],
        limit: int = 50,
        score_threshold: float = 0.0
    ) -> List[SearchResult]:
        """
        Search across all registered projects

        Convenience method that searches all projects in the workspace.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of merged and ranked search results
        """
        project_ids = list(self.collections.keys())

        if not project_ids:
            logger.warning("No projects registered for search_all")
            return []

        return await self.search_workspace(
            query_vector=query_vector,
            project_ids=project_ids,
            limit=limit,
            score_threshold=score_threshold
        )

    async def delete_vectors(
        self,
        project_id: str,
        file_paths: List[str]
    ) -> bool:
        """
        Delete vectors for specific file paths in a project

        Args:
            project_id: Project identifier
            file_paths: List of file paths to delete

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        if project_id not in self.collections:
            logger.error(f"Project {project_id} not registered")
            return False

        if not file_paths:
            logger.warning("Empty file path list provided for deletion")
            return True

        collection_name = self.collections[project_id]

        try:
            # Generate point IDs for all chunks of each file
            # For simplicity, we'll use filter-based deletion
            # This deletes all chunks for the specified file paths

            for file_path in file_paths:
                # Delete using filter
                client.delete(
                    collection_name=collection_name,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="file_path",
                                    match=models.MatchValue(value=file_path)
                                )
                            ]
                        )
                    )
                )

            self.stats["vectors_deleted"] += len(file_paths)
            logger.info(
                f"Deleted vectors for {len(file_paths)} files from project {project_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error deleting vectors: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    async def list_collections(self) -> List[Dict[str, Any]]:
        """
        List all project collections

        Returns:
            List of collection information dictionaries
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return []

        try:
            # Get all collections from Qdrant
            collections = client.get_collections()

            # Filter to project collections only
            project_collections = []

            for collection in collections.collections:
                # Check if this is a project collection
                if collection.name.startswith("project_") and collection.name.endswith("_vectors"):
                    # Try to find matching project_id
                    project_id = None
                    for pid, cname in self.collections.items():
                        if cname == collection.name:
                            project_id = pid
                            break

                    collection_info = {
                        "collection_name": collection.name,
                        "project_id": project_id,
                    }

                    # Get metadata if project is registered
                    if project_id and project_id in self.project_metadata:
                        meta = self.project_metadata[project_id]
                        collection_info["project_name"] = meta.project_name
                        collection_info["project_type"] = meta.project_type

                    project_collections.append(collection_info)

            logger.debug(f"Found {len(project_collections)} project collections")
            return project_collections

        except Exception as e:
            logger.error(f"Error listing collections: {e}", exc_info=True)
            return []

    async def get_collection_stats(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a project's collection

        Args:
            project_id: Project identifier

        Returns:
            Dictionary with collection statistics or None if error
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return None

        if project_id not in self.collections:
            logger.error(f"Project {project_id} not registered")
            return None

        collection_name = self.collections[project_id]

        try:
            collection_info = client.get_collection(collection_name)

            # Extract vector size (robust across schemas)
            vec_size = None
            distance = None
            try:
                vectors_cfg = collection_info.config.params.vectors
                vec_size = getattr(vectors_cfg, 'size', None)
                dist_obj = getattr(vectors_cfg, 'distance', None)
                distance = getattr(dist_obj, 'value', dist_obj)

                # Handle multi-vector schema
                if vec_size is None and isinstance(vectors_cfg, dict):
                    first = next(iter(vectors_cfg.values()), None)
                    if first:
                        vec_size = getattr(first, 'size', None)
                        dist_obj = getattr(first, 'distance', None)
                        distance = getattr(dist_obj, 'value', dist_obj)
            except Exception:
                pass

            # Get counts
            points_count = getattr(collection_info, 'points_count', 0)
            vectors_count = getattr(collection_info, 'vectors_count', points_count)
            segments_count = getattr(collection_info, 'segments_count', 0)

            stats = {
                "project_id": project_id,
                "collection_name": collection_name,
                "status": getattr(
                    getattr(collection_info, 'status', None),
                    'value',
                    'unknown'
                ),
                "points_count": points_count,
                "vectors_count": vectors_count,
                "vector_size": vec_size,
                "distance": distance,
                "segments_count": segments_count,
            }

            # Add project metadata
            if project_id in self.project_metadata:
                meta = self.project_metadata[project_id]
                stats["project_name"] = meta.project_name
                stats["project_type"] = meta.project_type

            logger.debug(f"Retrieved stats for project {project_id}")
            return stats

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}", exc_info=True)
            return None

    async def migrate_legacy_collection(
        self,
        old_collection_name: str,
        project_id: str,
        project_name: str,
        batch_size: int = 100
    ) -> bool:
        """
        Migrate vectors from v1 single-collection to v2 per-project collection

        This method copies all vectors from an old collection to a new project
        collection, adding project metadata to each vector.

        Args:
            old_collection_name: Name of the legacy collection (e.g., "context_vectors")
            project_id: Target project ID
            project_name: Target project name
            batch_size: Number of vectors to migrate per batch

        Returns:
            bool: True if successful
        """
        client = get_qdrant_client()
        if not client:
            logger.error("Qdrant client not available")
            return False

        try:
            # Check if old collection exists
            collections = client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if old_collection_name not in collection_names:
                logger.error(f"Legacy collection {old_collection_name} does not exist")
                return False

            # Get old collection info
            old_collection_info = client.get_collection(old_collection_name)
            total_points = old_collection_info.points_count

            # Extract vector size
            vec_size = None
            try:
                vectors_cfg = old_collection_info.config.params.vectors
                vec_size = getattr(vectors_cfg, 'size', None)
                if vec_size is None and isinstance(vectors_cfg, dict):
                    first = next(iter(vectors_cfg.values()), None)
                    if first:
                        vec_size = getattr(first, 'size', None)
            except Exception:
                vec_size = self.vector_size

            logger.info(
                f"Starting migration from {old_collection_name} to project {project_id} "
                f"({total_points} vectors)"
            )

            # Ensure new project collection exists
            await self.ensure_project_collection(
                project_id=project_id,
                project_name=project_name,
                vector_size=vec_size,
                recreate=True
            )

            new_collection_name = self.collections[project_id]

            # Scroll through old collection and copy vectors
            offset = None
            migrated_count = 0

            while True:
                # Scroll batch
                scroll_result = client.scroll(
                    collection_name=old_collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=True
                )

                points, next_offset = scroll_result

                if not points:
                    break

                # Transform points to add project metadata
                new_points = []
                for point in points:
                    # Extract payload
                    payload = dict(point.payload) if point.payload else {}

                    # Add project metadata
                    payload["project_id"] = project_id
                    payload["project_name"] = project_name

                    # Ensure required fields have defaults
                    if "file_path" not in payload:
                        payload["file_path"] = str(point.id)
                    if "language" not in payload:
                        payload["language"] = "unknown"
                    if "chunk_index" not in payload:
                        payload["chunk_index"] = 0

                    new_point = models.PointStruct(
                        id=point.id,
                        vector=point.vector,
                        payload=payload
                    )
                    new_points.append(new_point)

                # Upsert to new collection
                client.upsert(
                    collection_name=new_collection_name,
                    points=new_points
                )

                migrated_count += len(new_points)
                logger.info(
                    f"Migrated {migrated_count}/{total_points} vectors "
                    f"({migrated_count/total_points*100:.1f}%)"
                )

                # Check if we're done
                if next_offset is None:
                    break

                offset = next_offset

            logger.info(
                f"✅ Migration complete: {migrated_count} vectors migrated from "
                f"{old_collection_name} to {new_collection_name}"
            )

            # Optionally delete old collection
            # (Commented out for safety - user should manually delete after verification)
            # client.delete_collection(old_collection_name)
            # logger.info(f"Deleted old collection: {old_collection_name}")

            return True

        except Exception as e:
            logger.error(f"Error migrating legacy collection: {e}", exc_info=True)
            self.stats["errors"] += 1
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics

        Returns:
            Dictionary with statistics
        """
        return {
            "projects_registered": self.stats["projects_registered"],
            "collections_created": self.stats["collections_created"],
            "active_projects": len(self.collections),
            "vectors_stored": self.stats["vectors_stored"],
            "vectors_retrieved": self.stats["vectors_retrieved"],
            "vectors_deleted": self.stats["vectors_deleted"],
            "cross_project_searches": self.stats["cross_project_searches"],
            "errors": self.stats["errors"],
            "vector_size": self.vector_size,
        }

    def get_project_info(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered project

        Args:
            project_id: Project identifier

        Returns:
            Dictionary with project information or None if not found
        """
        if project_id not in self.collections:
            return None

        info = {
            "project_id": project_id,
            "collection_name": self.collections[project_id],
        }

        if project_id in self.project_metadata:
            meta = self.project_metadata[project_id]
            info["project_name"] = meta.project_name
            info["project_type"] = meta.project_type
            info["language"] = meta.language

        return info

    def list_projects(self) -> List[str]:
        """
        List all registered project IDs

        Returns:
            List of project IDs
        """
        return list(self.collections.keys())


# Global multi-root vector store instance
multi_root_store = MultiRootVectorStore()


# Public API functions for integration
async def ensure_project_collection(
    project_id: str,
    project_name: str,
    project_type: Optional[str] = None,
    recreate: bool = False
) -> bool:
    """Ensure project collection exists (entry point)"""
    return await multi_root_store.ensure_project_collection(
        project_id, project_name, project_type, recreate=recreate
    )


async def delete_project_collection(project_id: str) -> bool:
    """Delete project collection (entry point)"""
    return await multi_root_store.delete_project_collection(project_id)


async def upsert_project_vectors(
    project_id: str,
    vectors: List[VectorData]
) -> bool:
    """Upsert vectors for a project (entry point)"""
    return await multi_root_store.upsert_vectors(project_id, vectors)


async def search_project(
    project_id: str,
    query_vector: List[float],
    limit: int = 10,
    score_threshold: float = 0.0
) -> List[SearchResult]:
    """Search within a project (entry point)"""
    return await multi_root_store.search_project(
        project_id, query_vector, limit, score_threshold
    )


async def search_workspace(
    query_vector: List[float],
    project_ids: List[str],
    limit: int = 50,
    score_threshold: float = 0.0
) -> List[SearchResult]:
    """Search across multiple projects (entry point)"""
    return await multi_root_store.search_workspace(
        query_vector, project_ids, limit, score_threshold
    )


async def search_all_projects(
    query_vector: List[float],
    limit: int = 50,
    score_threshold: float = 0.0
) -> List[SearchResult]:
    """Search all projects (entry point)"""
    return await multi_root_store.search_all(query_vector, limit, score_threshold)


async def list_project_collections() -> List[Dict[str, Any]]:
    """List all project collections (entry point)"""
    return await multi_root_store.list_collections()


async def get_project_collection_stats(project_id: str) -> Optional[Dict[str, Any]]:
    """Get project collection statistics (entry point)"""
    return await multi_root_store.get_collection_stats(project_id)


async def migrate_legacy_collection(
    old_collection_name: str,
    project_id: str,
    project_name: str
) -> bool:
    """Migrate v1 collection to v2 (entry point)"""
    return await multi_root_store.migrate_legacy_collection(
        old_collection_name, project_id, project_name
    )


def get_multi_root_store() -> MultiRootVectorStore:
    """Get multi-root vector store instance (entry point)"""
    return multi_root_store


def get_multi_root_stats() -> Dict[str, Any]:
    """Get multi-root store statistics (entry point)"""
    return multi_root_store.get_stats()
