"""
MCP Workspace Tools

Provides workspace management operations for multi-project environments.
These tools are only available when running in workspace mode.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_workspace_tools(mcp: FastMCP):
    """
    Register workspace tools with MCP server

    These tools are only registered when the server is running in workspace mode.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def list_workspace_projects() -> Dict[str, Any]:
        """
        List all projects in the workspace

        Returns comprehensive information about each project including:
        - Project ID and name
        - Project type and path
        - Indexing status
        - File counts

        Returns:
            Dict containing list of projects with their metadata
        """
        logger.info("MCP tool invoked: list_workspace_projects")

        try:
            from src.mcp_server.http_server import get_workspace_manager

            workspace_manager = get_workspace_manager()

            if not workspace_manager:
                return {
                    "error": "Not in workspace mode",
                    "projects": [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            projects_info = []

            for project_id, project in workspace_manager.projects.items():
                project_info = {
                    "id": project.id,
                    "name": project.name,
                    "path": str(project.path),
                    "type": project.config.type,
                    "status": project.status.value,
                    "languages": project.config.language,
                    "dependencies": project.config.dependencies,
                    "indexing": {
                        "enabled": project.config.indexing.enabled,
                        "priority": project.config.indexing.priority,
                        "files_indexed": project.stats.files_indexed,
                        "total_files": project.stats.total_files,
                        "errors": project.stats.errors,
                        "last_indexed": (
                            project.stats.last_indexed.isoformat()
                            if project.stats.last_indexed
                            else None
                        ),
                    },
                    "monitoring_active": (
                        project.file_monitor.is_running if project.file_monitor else False
                    ),
                }
                projects_info.append(project_info)

            result = {
                "workspace": {
                    "name": workspace_manager.config.name if workspace_manager.config else "unknown",
                    "config_path": str(workspace_manager.workspace_path),
                },
                "total_projects": len(projects_info),
                "projects": projects_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Listed {len(projects_info)} projects in workspace")
            return result

        except Exception as e:
            logger.error(f"Error listing workspace projects: {e}", exc_info=True)
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def get_project_status(project_id: str) -> Dict[str, Any]:
        """
        Get detailed status of a specific project

        Provides comprehensive information about a project's current state,
        indexing progress, and statistics.

        Args:
            project_id: Project identifier

        Returns:
            Dict containing detailed project status
        """
        logger.info(f"MCP tool invoked: get_project_status for project: {project_id}")

        try:
            from src.mcp_server.http_server import get_workspace_manager

            workspace_manager = get_workspace_manager()

            if not workspace_manager:
                return {
                    "error": "Not in workspace mode",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            project = workspace_manager.get_project(project_id)

            if not project:
                return {
                    "error": f"Project not found: {project_id}",
                    "available_projects": list(workspace_manager.projects.keys()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            status = await project.get_status()

            logger.info(f"Retrieved status for project: {project_id}")
            return {
                "project": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting project status: {e}", exc_info=True)
            return {
                "error": str(e),
                "project_id": project_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def get_workspace_status() -> Dict[str, Any]:
        """
        Get complete workspace status

        Returns comprehensive workspace information including:
        - All projects and their status
        - Relationship graph statistics
        - Multi-root vector store statistics
        - Overall workspace health

        Returns:
            Dict containing complete workspace status
        """
        logger.info("MCP tool invoked: get_workspace_status")

        try:
            from src.mcp_server.http_server import get_workspace_manager

            workspace_manager = get_workspace_manager()

            if not workspace_manager:
                return {
                    "error": "Not in workspace mode",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            # Get complete workspace status
            status = await workspace_manager.get_workspace_status()

            # Add summary statistics
            projects_by_status = {}
            total_files_indexed = 0
            total_errors = 0

            for project_id, project_status in status["projects"].items():
                status_value = project_status["status"]
                projects_by_status[status_value] = projects_by_status.get(status_value, 0) + 1
                total_files_indexed += project_status["indexing"]["files_indexed"]
                total_errors += project_status["indexing"]["errors"]

            status["summary"] = {
                "total_projects": len(status["projects"]),
                "projects_by_status": projects_by_status,
                "total_files_indexed": total_files_indexed,
                "total_errors": total_errors,
            }

            status["timestamp"] = datetime.now(timezone.utc).isoformat()

            logger.info("Retrieved complete workspace status")
            return status

        except Exception as e:
            logger.error(f"Error getting workspace status: {e}", exc_info=True)
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def get_project_relationships(project_id: str) -> Dict[str, Any]:
        """
        Get project dependencies and relationships

        Returns information about a project's relationships including:
        - Direct dependencies
        - Dependent projects (reverse dependencies)
        - Related projects
        - Relationship types

        Args:
            project_id: Project identifier

        Returns:
            Dict containing project relationships
        """
        logger.info(f"MCP tool invoked: get_project_relationships for project: {project_id}")

        try:
            from src.mcp_server.http_server import get_workspace_manager

            workspace_manager = get_workspace_manager()

            if not workspace_manager:
                return {
                    "error": "Not in workspace mode",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            project = workspace_manager.get_project(project_id)

            if not project:
                return {
                    "error": f"Project not found: {project_id}",
                    "available_projects": list(workspace_manager.projects.keys()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            relationship_graph = workspace_manager.relationship_graph

            # Get dependencies (projects this project depends on)
            dependencies = relationship_graph.get_dependencies(project_id)

            # Get dependents (projects that depend on this project)
            dependents = relationship_graph.get_dependents(project_id)

            # Get all relationships
            relationships = relationship_graph.get_project_relationships(project_id)

            result = {
                "project_id": project_id,
                "project_name": project.name,
                "dependencies": {
                    "count": len(dependencies),
                    "projects": dependencies,
                },
                "dependents": {
                    "count": len(dependents),
                    "projects": dependents,
                },
                "all_relationships": {
                    "count": len(relationships),
                    "relationships": [
                        {
                            "target_project": rel["to_id"],
                            "type": rel["type"].value,
                            "metadata": rel.get("metadata", {}),
                        }
                        for rel in relationships
                    ],
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(
                f"Retrieved relationships for project {project_id}: "
                f"{len(dependencies)} dependencies, {len(dependents)} dependents"
            )
            return result

        except Exception as e:
            logger.error(f"Error getting project relationships: {e}", exc_info=True)
            return {
                "error": str(e),
                "project_id": project_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @mcp.tool()
    async def search_workspace(
        query: str,
        scope: str = "workspace",
        project_id: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Explicit workspace search with scope control

        Provides fine-grained control over workspace search with explicit scope selection.
        This is a dedicated workspace-only search tool that complements the general
        semantic_search tool.

        Args:
            query: Natural language search query
            scope: Search scope - "project", "dependencies", "workspace", "related"
            project_id: Target project ID (required for project/dependencies/related scopes)
            limit: Maximum number of results (default: 20)

        Returns:
            Dict containing search results with project context
        """
        logger.info(
            f"MCP tool invoked: search_workspace with query: {query}, scope: {scope}, project: {project_id}"
        )

        try:
            from src.mcp_server.http_server import get_workspace_manager
            from src.search.workspace_search import SearchScope, get_workspace_search, initialize_workspace_search
            import time

            workspace_manager = get_workspace_manager()

            if not workspace_manager:
                return {
                    "error": "Not in workspace mode",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            # Initialize workspace search if needed
            workspace_search = get_workspace_search()
            if not workspace_search.workspace_manager:
                initialize_workspace_search(
                    workspace_manager=workspace_manager,
                    vector_store=None,
                    relationship_graph=workspace_manager.relationship_graph
                )
                workspace_search = get_workspace_search()

            # Convert scope string to enum
            try:
                search_scope = SearchScope(scope.lower())
            except ValueError:
                return {
                    "error": f"Invalid scope: {scope}",
                    "valid_scopes": ["project", "dependencies", "workspace", "related"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            # Validate project_id for scopes that require it
            if search_scope in [SearchScope.PROJECT, SearchScope.DEPENDENCIES, SearchScope.RELATED]:
                if not project_id:
                    return {
                        "error": f"project_id is required for scope '{scope}'",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                if project_id not in workspace_manager.projects:
                    return {
                        "error": f"Project not found: {project_id}",
                        "available_projects": list(workspace_manager.projects.keys()),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

            # Perform search
            start_time = time.time()
            enhanced_results, metrics = await workspace_search.search(
                query=query,
                scope=search_scope,
                project_id=project_id,
                limit=limit,
            )
            search_time_ms = (time.time() - start_time) * 1000

            # Format results
            formatted_results = []
            for result in enhanced_results:
                formatted_result = {
                    "file_path": result.file_path,
                    "file_name": result.file_name,
                    "file_type": result.file_type,
                    "similarity_score": round(result.similarity_score, 3),
                    "confidence_score": round(result.confidence_score, 3),
                    "snippet": (
                        result.snippet[:200] + "..."
                        if result.snippet and len(result.snippet) > 200
                        else result.snippet
                    ),
                    "project_id": result.project_id,
                    "project_name": result.project_name,
                    "relationship_context": result.relationship_context,
                }
                formatted_results.append(formatted_result)

            result = {
                "query": query,
                "scope": scope,
                "target_project": project_id,
                "total_results": len(enhanced_results),
                "returned_results": len(formatted_results),
                "search_time_ms": round(search_time_ms, 2),
                "results": formatted_results,
                "metrics": {
                    "projects_searched": metrics.projects_searched,
                    "projects_searched_list": metrics.projects_searched_list,
                    "total_time_ms": round(metrics.total_time_ms, 2),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(
                f"Workspace search completed: {len(enhanced_results)} results in {search_time_ms:.2f}ms"
            )
            return result

        except Exception as e:
            logger.error(f"Error in workspace search: {e}", exc_info=True)
            return {
                "error": str(e),
                "query": query,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    logger.info("Workspace tools registered successfully")
