"""
Workspace Search Example

Demonstrates cross-project semantic search capabilities with multiple search scopes.
"""

import asyncio
from src.search.workspace_search import (
    WorkspaceSearch,
    SearchScope,
    EnhancedSearchResult,
    SearchMetrics
)
from src.workspace.relationship_graph import ProjectRelationshipGraph, RelationshipType


async def example_basic_search():
    """Example: Basic workspace search without workspace manager"""
    print("=" * 60)
    print("Example 1: Basic Workspace Search (Single Project Mode)")
    print("=" * 60)

    # Initialize search in single-project fallback mode
    search = WorkspaceSearch()

    # Perform a search
    results, metrics = await search.search(
        query="authentication logic",
        scope=SearchScope.WORKSPACE,
        limit=10
    )

    print(f"\nQuery: 'authentication logic'")
    print(f"Scope: WORKSPACE")
    print(f"Results: {len(results)}")
    print(f"Search time: {metrics.total_time_ms:.2f}ms")

    for i, result in enumerate(results[:3], 1):
        print(f"\n{i}. {result.file_name}")
        print(f"   Path: {result.file_path}")
        print(f"   Project: {result.project_name} ({result.project_id})")
        print(f"   Score: {result.confidence_score:.3f}")
        print(f"   Snippet: {result.snippet[:100] if result.snippet else 'N/A'}...")


async def example_project_scoped_search():
    """Example: Search within a specific project"""
    print("\n" + "=" * 60)
    print("Example 2: Project-Scoped Search")
    print("=" * 60)

    search = WorkspaceSearch()

    # Search within specific project
    results, metrics = await search.search(
        query="database models",
        scope=SearchScope.PROJECT,
        project_id="backend",
        limit=10
    )

    print(f"\nQuery: 'database models'")
    print(f"Scope: PROJECT (backend)")
    print(f"Results: {len(results)}")
    print(f"Search time: {metrics.total_time_ms:.2f}ms")


async def example_dependency_search():
    """Example: Search project and its dependencies"""
    print("\n" + "=" * 60)
    print("Example 3: Dependency-Aware Search")
    print("=" * 60)

    # Create relationship graph
    rel_graph = ProjectRelationshipGraph()
    rel_graph.add_project("frontend")
    rel_graph.add_project("backend")
    rel_graph.add_project("shared")

    # Add relationships
    rel_graph.add_relationship(
        "frontend",
        "backend",
        RelationshipType.API_CLIENT,
        metadata={"description": "Frontend calls backend API"}
    )
    rel_graph.add_relationship(
        "frontend",
        "shared",
        RelationshipType.IMPORTS,
        metadata={"description": "Frontend imports shared types"}
    )

    # Initialize search with relationship graph
    search = WorkspaceSearch(relationship_graph=rel_graph)

    # Search with dependencies
    results, metrics = await search.search(
        query="API endpoints",
        scope=SearchScope.DEPENDENCIES,
        project_id="frontend",
        include_dependencies=True,
        limit=10
    )

    print(f"\nQuery: 'API endpoints'")
    print(f"Scope: DEPENDENCIES (frontend + deps)")
    print(f"Results: {len(results)}")
    print(f"Projects searched: {metrics.projects_searched_list}")
    print(f"Search time: {metrics.total_time_ms:.2f}ms")


async def example_related_projects_search():
    """Example: Search semantically related projects"""
    print("\n" + "=" * 60)
    print("Example 4: Related Projects Search")
    print("=" * 60)

    # Create relationship graph with semantic similarity
    rel_graph = ProjectRelationshipGraph()
    rel_graph.add_project("backend")
    rel_graph.add_project("api-gateway")
    rel_graph.add_project("microservice-auth")

    # Add semantic similarity relationships
    rel_graph.add_relationship(
        "backend",
        "api-gateway",
        RelationshipType.SEMANTIC_SIMILARITY,
        weight=0.85
    )
    rel_graph.add_relationship(
        "backend",
        "microservice-auth",
        RelationshipType.SEMANTIC_SIMILARITY,
        weight=0.75
    )

    search = WorkspaceSearch(relationship_graph=rel_graph)

    # Search related projects
    results, metrics = await search.search(
        query="authentication middleware",
        scope=SearchScope.RELATED,
        project_id="backend",
        similarity_threshold=0.7,
        limit=10
    )

    print(f"\nQuery: 'authentication middleware'")
    print(f"Scope: RELATED (similarity >= 0.7)")
    print(f"Target project: backend")
    print(f"Results: {len(results)}")

    # Show relationship context
    for result in results[:3]:
        if result.relationship_context:
            print(f"\n  File: {result.file_name}")
            print(f"  Project: {result.project_id}")
            print(f"  Related to: {', '.join(result.relationship_context)}")


async def example_streaming_search():
    """Example: Streaming search results"""
    print("\n" + "=" * 60)
    print("Example 5: Streaming Search Results")
    print("=" * 60)

    search = WorkspaceSearch()

    print(f"\nQuery: 'error handling'")
    print(f"Streaming results as they arrive...\n")

    count = 0
    async for result in search.search_streaming(
        query="error handling",
        scope=SearchScope.WORKSPACE,
        limit=5
    ):
        count += 1
        print(f"{count}. {result.file_name} (score: {result.confidence_score:.3f})")


async def example_search_metrics():
    """Example: Understanding search metrics"""
    print("\n" + "=" * 60)
    print("Example 6: Search Metrics and Performance")
    print("=" * 60)

    search = WorkspaceSearch()

    results, metrics = await search.search(
        query="optimization algorithms",
        scope=SearchScope.WORKSPACE,
        limit=20
    )

    print(f"\nSearch Metrics:")
    print(f"  Total time: {metrics.total_time_ms:.2f}ms")
    print(f"  Projects searched: {metrics.projects_searched}")
    print(f"  Projects list: {metrics.projects_searched_list}")
    print(f"  Results before merge: {metrics.total_results_before_merge}")
    print(f"  Results after merge: {metrics.total_results_after_merge}")
    print(f"  Duplicates removed: {metrics.deduplicated_count}")
    print(f"  Embedding time: {metrics.embedding_time_ms:.2f}ms")
    print(f"  Search time: {metrics.search_time_ms:.2f}ms")
    print(f"  Ranking time: {metrics.ranking_time_ms:.2f}ms")


async def example_ranking_factors():
    """Example: Understanding cross-project ranking"""
    print("\n" + "=" * 60)
    print("Example 7: Cross-Project Ranking Factors")
    print("=" * 60)

    search = WorkspaceSearch()

    print("\nRanking Formula:")
    print("final_score = (")
    print(f"  vector_similarity * {search.vector_similarity_weight} +")
    print(f"  project_priority * {search.project_priority_weight} +")
    print(f"  relationship_boost * {search.relationship_boost_weight} +")
    print(f"  recency_boost * {search.recency_boost_weight} +")
    print(f"  exact_match_boost * {search.exact_match_boost_weight}")
    print(")")

    print("\nProject Priority Multipliers:")
    for priority, multiplier in search.priority_multipliers.items():
        print(f"  {priority}: {multiplier}x")


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("WORKSPACE SEARCH EXAMPLES")
    print("=" * 60)

    try:
        await example_basic_search()
        await example_project_scoped_search()
        await example_dependency_search()
        await example_related_projects_search()
        await example_streaming_search()
        await example_search_metrics()
        await example_ranking_factors()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
