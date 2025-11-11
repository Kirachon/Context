"""
Workspace Manager

Orchestrates multiple projects within a workspace with relationship tracking,
cross-project search, and lifecycle management.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from src.workspace.config import WorkspaceConfig, ProjectConfig
from src.workspace.multi_root_store import MultiRootVectorStore
from src.workspace.relationship_graph import ProjectRelationshipGraph, RelationshipType
from src.indexing.file_monitor import FileMonitor
from src.indexing.file_indexer import FileIndexer
from src.vector_db.ast_store import ASTVectorStore
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ProjectStatus(Enum):
    """Project initialization and indexing status"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ProjectStats:
    """Project statistics"""
    files_indexed: int = 0
    total_files: int = 0
    errors: int = 0
    last_indexed: Optional[datetime] = None
    indexing_duration_seconds: Optional[float] = None


class Project:
    """
    Represents a single project within a workspace

    Each project has its own vector store, AST store, file monitor,
    and indexer instances (no global singletons).
    """

    def __init__(
        self,
        config: ProjectConfig,
        workspace_manager: "WorkspaceManager",
    ):
        """
        Initialize project

        Args:
            config: Project configuration
            workspace_manager: Reference to parent workspace manager
        """
        self.id = config.id
        self.name = config.name
        self.path = config.get_resolved_path() or Path(config.path)
        self.config = config
        self.workspace_manager = workspace_manager

        # Status tracking
        self.status = ProjectStatus.PENDING
        self.stats = ProjectStats()
        self.initialization_error: Optional[str] = None

        # Per-project component instances (NOT global singletons!)
        # These will be initialized in async initialize() method
        self.vector_store: Optional[MultiRootVectorStore] = None
        self.ast_store: Optional[ASTVectorStore] = None
        self.file_monitor: Optional[FileMonitor] = None
        self.indexer: Optional[FileIndexer] = None

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        logger.info(f"Project created: {self.id} ({self.name})")

    async def initialize(self) -> bool:
        """
        Initialize project components

        Returns:
            bool: True if successful
        """
        async with self._lock:
            if self.status != ProjectStatus.PENDING:
                logger.warning(f"Project {self.id} already initialized (status: {self.status.value})")
                return self.status == ProjectStatus.READY

            self.status = ProjectStatus.INITIALIZING
            logger.info(f"Initializing project: {self.id}")

            try:
                # Validate project path exists
                if not self.path.exists():
                    raise ValueError(f"Project path does not exist: {self.path}")

                if not self.path.is_dir():
                    raise ValueError(f"Project path is not a directory: {self.path}")

                # Initialize per-project vector store (using workspace-level MultiRootVectorStore)
                self.vector_store = self.workspace_manager.multi_root_store
                await self.vector_store.ensure_project_collection(self.id)

                # Initialize per-project AST store
                self.ast_store = ASTVectorStore(base_collection_name=f"project_{self.id}")
                await self.ast_store.ensure_collections()

                # Initialize per-project file monitor
                self.file_monitor = FileMonitor(
                    paths=[str(self.path)],
                    on_change_callback=self._on_file_change,
                )

                # Initialize per-project indexer
                self.indexer = FileIndexer()

                logger.info(f"Project {self.id} initialized successfully")
                self.status = ProjectStatus.READY
                return True

            except Exception as e:
                logger.error(f"Failed to initialize project {self.id}: {e}", exc_info=True)
                self.status = ProjectStatus.FAILED
                self.initialization_error = str(e)
                return False

    async def index(self, force: bool = False) -> bool:
        """
        Index all files in the project

        Args:
            force: Force re-indexing even if already indexed

        Returns:
            bool: True if successful
        """
        async with self._lock:
            if self.status == ProjectStatus.FAILED:
                logger.error(f"Cannot index failed project: {self.id}")
                return False

            if not self.config.indexing.enabled and not force:
                logger.info(f"Indexing disabled for project: {self.id}")
                return True

            logger.info(f"Indexing project: {self.id} (path: {self.path})")
            self.status = ProjectStatus.INDEXING

            start_time = asyncio.get_event_loop().time()

            try:
                # Get all supported files
                supported_extensions = {
                    ".py", ".js", ".jsx", ".ts", ".tsx",
                    ".java", ".cpp", ".hpp", ".h", ".cc", ".cxx"
                }

                files_to_index = []
                exclude_patterns = set(self.config.indexing.exclude)

                for file_path in self.path.rglob("*"):
                    # Skip if not a file
                    if not file_path.is_file():
                        continue

                    # Skip if extension not supported
                    if file_path.suffix not in supported_extensions:
                        continue

                    # Skip if matches exclude patterns
                    should_exclude = False
                    for pattern in exclude_patterns:
                        if pattern in file_path.parts:
                            should_exclude = True
                            break

                    if should_exclude:
                        continue

                    files_to_index.append(file_path)

                self.stats.total_files = len(files_to_index)
                logger.info(f"Found {len(files_to_index)} files to index in project {self.id}")

                # Index files
                indexed_count = 0
                error_count = 0

                for file_path in files_to_index:
                    try:
                        # Index file
                        metadata = await self.indexer.index_file(str(file_path))

                        if metadata:
                            indexed_count += 1

                            # Note: Vector embedding is already handled by FileIndexer.index_file()
                            # which calls vector_store.upsert_vector()
                            # We just need to track project-specific stats

                    except Exception as e:
                        logger.error(f"Error indexing file {file_path}: {e}")
                        error_count += 1

                # Update stats
                self.stats.files_indexed = indexed_count
                self.stats.errors = error_count
                self.stats.last_indexed = datetime.now()
                self.stats.indexing_duration_seconds = asyncio.get_event_loop().time() - start_time

                logger.info(
                    f"Indexed project {self.id}: "
                    f"{indexed_count}/{len(files_to_index)} files "
                    f"({error_count} errors) "
                    f"in {self.stats.indexing_duration_seconds:.2f}s"
                )

                self.status = ProjectStatus.READY
                return True

            except Exception as e:
                logger.error(f"Error indexing project {self.id}: {e}", exc_info=True)
                self.status = ProjectStatus.FAILED
                self.stats.errors += 1
                return False

    async def search(
        self, query: str, limit: int = 10, score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search within this project only

        Args:
            query: Search query
            limit: Maximum results
            score_threshold: Minimum score threshold

        Returns:
            List of search results
        """
        if self.status != ProjectStatus.READY:
            logger.warning(f"Cannot search project {self.id} (status: {self.status.value})")
            return []

        try:
            # Generate query embedding
            from src.vector_db.embeddings import generate_code_embedding

            query_vector = await generate_code_embedding(code=query, file_path="", language="")

            if not query_vector:
                logger.error("Failed to generate query embedding")
                return []

            # Search project collection
            results = await self.vector_store.search_project(
                project_id=self.id,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )

            logger.debug(f"Project search in {self.id} returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error searching project {self.id}: {e}", exc_info=True)
            return []

    async def start_monitoring(self) -> bool:
        """
        Start file system monitoring for real-time updates

        Returns:
            bool: True if successful
        """
        if not self.file_monitor:
            logger.error(f"File monitor not initialized for project {self.id}")
            return False

        try:
            await self.file_monitor.start()
            logger.info(f"Started file monitoring for project {self.id}")
            return True

        except Exception as e:
            logger.error(f"Error starting file monitor for {self.id}: {e}", exc_info=True)
            return False

    async def stop_monitoring(self) -> bool:
        """
        Stop file system monitoring

        Returns:
            bool: True if successful
        """
        if not self.file_monitor:
            return True

        try:
            await self.file_monitor.stop()
            logger.info(f"Stopped file monitoring for project {self.id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping file monitor for {self.id}: {e}", exc_info=True)
            return False

    async def _on_file_change(self, event_type: str, file_path: str) -> None:
        """
        Handle file system change events

        Args:
            event_type: Type of event (created, modified, deleted)
            file_path: Path to changed file
        """
        logger.debug(f"File change in project {self.id}: {event_type} - {file_path}")

        try:
            if event_type in ("created", "modified"):
                # Re-index the file
                await self.indexer.index_file(file_path)
                logger.info(f"Re-indexed file in project {self.id}: {file_path}")

            elif event_type == "deleted":
                # Remove from index
                await self.indexer.remove_file(file_path)
                logger.info(f"Removed file from project {self.id}: {file_path}")

        except Exception as e:
            logger.error(f"Error handling file change in project {self.id}: {e}", exc_info=True)

    async def get_status(self) -> Dict[str, Any]:
        """
        Get project status and statistics

        Returns:
            Status dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "type": self.config.type,
            "status": self.status.value,
            "initialization_error": self.initialization_error,
            "indexing": {
                "enabled": self.config.indexing.enabled,
                "priority": self.config.indexing.priority,
                "files_indexed": self.stats.files_indexed,
                "total_files": self.stats.total_files,
                "errors": self.stats.errors,
                "last_indexed": self.stats.last_indexed.isoformat() if self.stats.last_indexed else None,
                "duration_seconds": self.stats.indexing_duration_seconds,
            },
            "monitoring": {
                "active": self.file_monitor.is_running if self.file_monitor else False,
            },
        }


class WorkspaceManager:
    """
    Workspace Manager

    Orchestrates multiple projects within a workspace with relationship tracking,
    cross-project search, and lifecycle management.
    """

    def __init__(self, workspace_path: str):
        """
        Initialize workspace manager

        Args:
            workspace_path: Path to .context-workspace.json file
        """
        self.workspace_path = Path(workspace_path)
        self.config: Optional[WorkspaceConfig] = None
        self.projects: Dict[str, Project] = {}

        # Shared workspace-level components
        self.multi_root_store = MultiRootVectorStore()
        self.relationship_graph = ProjectRelationshipGraph()

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        logger.info(f"WorkspaceManager created for: {workspace_path}")

    async def initialize(self, lazy_load: bool = False) -> bool:
        """
        Initialize workspace and all projects

        Args:
            lazy_load: If True, don't initialize projects immediately

        Returns:
            bool: True if successful
        """
        async with self._lock:
            logger.info("Initializing workspace...")

            try:
                # Load workspace configuration
                self.config = WorkspaceConfig.load(self.workspace_path, validate_paths=True)
                logger.info(f"Loaded workspace: {self.config.name} ({len(self.config.projects)} projects)")

                # Build relationship graph from config
                await self._build_relationship_graph()

                # Initialize projects
                if not lazy_load:
                    success = await self._initialize_all_projects()
                    if not success:
                        logger.warning("Some projects failed to initialize")
                else:
                    logger.info("Lazy loading enabled - projects will be initialized on demand")

                logger.info("Workspace initialization complete")
                return True

            except Exception as e:
                logger.error(f"Failed to initialize workspace: {e}", exc_info=True)
                return False

    async def _initialize_all_projects(self) -> bool:
        """
        Initialize all projects in parallel

        Returns:
            bool: True if all projects initialized successfully
        """
        logger.info("Initializing all projects...")

        # Create project instances
        for project_config in self.config.projects:
            project = Project(config=project_config, workspace_manager=self)
            self.projects[project.id] = project

        # Initialize projects in parallel using asyncio.gather
        init_tasks = [
            project.initialize()
            for project in self.projects.values()
        ]

        results = await asyncio.gather(*init_tasks, return_exceptions=True)

        # Check results
        success_count = 0
        failed_count = 0

        for project, result in zip(self.projects.values(), results):
            if isinstance(result, Exception):
                logger.error(f"Project {project.id} initialization failed: {result}")
                failed_count += 1
            elif result:
                success_count += 1
            else:
                failed_count += 1

        logger.info(
            f"Project initialization complete: "
            f"{success_count} successful, {failed_count} failed"
        )

        return failed_count == 0

    async def _build_relationship_graph(self) -> None:
        """Build relationship graph from workspace configuration"""
        logger.info("Building relationship graph...")

        # Add projects to graph
        for project_config in self.config.projects:
            metadata = {
                "name": project_config.name,
                "type": project_config.type,
                "languages": project_config.language,
            }
            self.relationship_graph.add_project(project_config.id, metadata)

        # Add explicit relationships from config
        for rel_config in self.config.relationships:
            # Map string type to RelationshipType enum
            try:
                rel_type = RelationshipType(rel_config.type)
            except ValueError:
                rel_type = RelationshipType.EXPLICIT

            self.relationship_graph.add_relationship(
                from_id=rel_config.from_project,
                to_id=rel_config.to_project,
                rel_type=rel_type,
                metadata={"description": rel_config.description} if rel_config.description else {},
            )

        # Add dependency relationships
        for project_config in self.config.projects:
            for dep_id in project_config.dependencies:
                self.relationship_graph.add_relationship(
                    from_id=project_config.id,
                    to_id=dep_id,
                    rel_type=RelationshipType.DEPENDENCY,
                )

        graph_stats = self.relationship_graph.get_stats()
        logger.info(
            f"Relationship graph built: "
            f"{graph_stats['projects']} projects, "
            f"{graph_stats['relationships']} relationships"
        )

    async def add_project(self, project_config: ProjectConfig) -> bool:
        """
        Add a new project to the workspace

        Args:
            project_config: Project configuration

        Returns:
            bool: True if successful
        """
        async with self._lock:
            if project_config.id in self.projects:
                logger.error(f"Project {project_config.id} already exists")
                return False

            try:
                # Add to config
                self.config.add_project(project_config)

                # Create and initialize project
                project = Project(config=project_config, workspace_manager=self)
                success = await project.initialize()

                if success:
                    self.projects[project.id] = project
                    self.relationship_graph.add_project(project.id)
                    logger.info(f"Added project: {project.id}")
                    return True
                else:
                    logger.error(f"Failed to initialize project: {project.id}")
                    return False

            except Exception as e:
                logger.error(f"Error adding project {project_config.id}: {e}", exc_info=True)
                return False

    async def remove_project(self, project_id: str) -> bool:
        """
        Remove a project from the workspace

        Args:
            project_id: Project identifier

        Returns:
            bool: True if successful
        """
        async with self._lock:
            if project_id not in self.projects:
                logger.error(f"Project {project_id} not found")
                return False

            try:
                project = self.projects[project_id]

                # Stop monitoring
                await project.stop_monitoring()

                # Delete vector collection
                await self.multi_root_store.delete_project_collection(project_id)

                # Remove from config and graph
                self.config.remove_project(project_id)

                # Remove from projects dict
                del self.projects[project_id]

                logger.info(f"Removed project: {project_id}")
                return True

            except Exception as e:
                logger.error(f"Error removing project {project_id}: {e}", exc_info=True)
                return False

    async def reload_project(self, project_id: str) -> bool:
        """
        Reload a project's index

        Args:
            project_id: Project identifier

        Returns:
            bool: True if successful
        """
        if project_id not in self.projects:
            logger.error(f"Project {project_id} not found")
            return False

        project = self.projects[project_id]

        try:
            logger.info(f"Reloading project: {project_id}")
            success = await project.index(force=True)
            return success

        except Exception as e:
            logger.error(f"Error reloading project {project_id}: {e}", exc_info=True)
            return False

    def get_project(self, project_id: str) -> Optional[Project]:
        """
        Get project instance

        Args:
            project_id: Project identifier

        Returns:
            Project instance or None
        """
        return self.projects.get(project_id)

    async def search_workspace(
        self,
        query: str,
        project_ids: Optional[List[str]] = None,
        limit: int = 50,
        score_threshold: float = 0.0,
        use_relationship_boost: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search across workspace with relationship-aware ranking

        Args:
            query: Search query
            project_ids: Optional list of project IDs to search (None = all)
            limit: Maximum results
            score_threshold: Minimum score threshold
            use_relationship_boost: Apply relationship-based ranking boost

        Returns:
            List of search results
        """
        try:
            # Generate query embedding
            from src.vector_db.embeddings import generate_code_embedding

            query_vector = await generate_code_embedding(code=query, file_path="", language="")

            if not query_vector:
                logger.error("Failed to generate query embedding")
                return []

            # Determine which projects to search
            search_projects = project_ids if project_ids else list(self.projects.keys())

            # Calculate relationship boosts if enabled
            relationship_boosts = None
            if use_relationship_boost and self.config.search.cross_project_ranking:
                # For now, use a simple boost based on the relationship graph
                # In a more sophisticated implementation, this would consider
                # the query context and boost related projects accordingly
                relationship_boosts = {}
                boost_factor = self.config.search.relationship_boost

                for project_id in search_projects:
                    boosts = self.relationship_graph.get_relationship_boost_factors(
                        project_id, boost_factor
                    )
                    relationship_boosts.update(boosts)

            # Search workspace
            results = await self.multi_root_store.search_workspace(
                query_vector=query_vector,
                project_ids=search_projects,
                limit=limit,
                score_threshold=score_threshold,
                relationship_boost=relationship_boosts,
            )

            logger.info(f"Workspace search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error in workspace search: {e}", exc_info=True)
            return []

    async def index_all_projects(self, parallel: bool = True) -> Dict[str, bool]:
        """
        Index all projects in the workspace

        Args:
            parallel: Index projects in parallel

        Returns:
            Dict mapping project_id -> success boolean
        """
        logger.info("Indexing all projects...")

        if parallel:
            # Index in parallel
            index_tasks = [
                project.index()
                for project in self.projects.values()
                if project.config.indexing.enabled
            ]

            results = await asyncio.gather(*index_tasks, return_exceptions=True)

            # Map results
            result_map = {}
            for project, result in zip(
                [p for p in self.projects.values() if p.config.indexing.enabled],
                results
            ):
                if isinstance(result, Exception):
                    logger.error(f"Project {project.id} indexing failed: {result}")
                    result_map[project.id] = False
                else:
                    result_map[project.id] = result

        else:
            # Index sequentially
            result_map = {}
            for project in self.projects.values():
                if project.config.indexing.enabled:
                    result_map[project.id] = await project.index()

        success_count = sum(1 for v in result_map.values() if v)
        logger.info(
            f"Project indexing complete: "
            f"{success_count}/{len(result_map)} successful"
        )

        return result_map

    async def watch_for_changes(self) -> None:
        """
        Hot-reload on workspace configuration changes

        Note: This is a placeholder for file system watching on the
        .context-workspace.json file. Full implementation would use
        watchdog to monitor the config file and reload on changes.
        """
        logger.info("Watching for workspace config changes (placeholder)")
        # TODO: Implement config file watching
        pass

    async def get_workspace_status(self) -> Dict[str, Any]:
        """
        Get complete workspace status

        Returns:
            Status dictionary
        """
        project_statuses = {}
        for project_id, project in self.projects.items():
            project_statuses[project_id] = await project.get_status()

        return {
            "workspace": {
                "name": self.config.name if self.config else "unknown",
                "version": self.config.version if self.config else "unknown",
                "config_path": str(self.workspace_path),
            },
            "projects": project_statuses,
            "relationship_graph": self.relationship_graph.get_stats(),
            "multi_root_store": self.multi_root_store.get_stats(),
        }
