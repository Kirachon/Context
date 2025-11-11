# Workspace Search Documentation

## Overview

The Workspace Search system provides **cross-project semantic search** capabilities for multi-project code context engines. It enables intelligent search across multiple projects with relationship-aware ranking and advanced result merging.

## Features

- **4 Search Scopes**: PROJECT, DEPENDENCIES, WORKSPACE, RELATED
- **Cross-Project Ranking**: Considers project priority, relationships, recency, and exact matches
- **Result Merging**: Intelligent deduplication and score-based merging
- **Performance Optimized**: Parallel search, early termination, streaming results
- **Type-Safe**: Full type hints with Pydantic models

---

## Search Scopes

### 1. PROJECT
Search within a single project only.

```python
results, metrics = await search.search(
    query="authentication logic",
    scope=SearchScope.PROJECT,
    project_id="backend",
    limit=10
)
```

**Use Case**: When you know exactly which project contains relevant code.

---

### 2. DEPENDENCIES
Search within a project and all its dependencies.

```python
results, metrics = await search.search(
    query="API types",
    scope=SearchScope.DEPENDENCIES,
    project_id="frontend",
    include_dependencies=True,
    limit=20
)
```

**Use Case**: Finding code that might be in a project or its dependencies (shared libraries, APIs).

---

### 3. WORKSPACE
Search across all projects in the workspace.

```python
results, metrics = await search.search(
    query="error handling patterns",
    scope=SearchScope.WORKSPACE,
    limit=50
)
```

**Use Case**: Workspace-wide search when you don't know which project contains the code.

---

### 4. RELATED
Search semantically related projects based on similarity threshold.

```python
results, metrics = await search.search(
    query="database migrations",
    scope=SearchScope.RELATED,
    project_id="backend",
    similarity_threshold=0.7,
    limit=20
)
```

**Use Case**: Finding similar implementations across related projects.

---

## Enhanced Search Results

### EnhancedSearchResult

Extends base `SearchResult` with project-awareness:

```python
@dataclass
class EnhancedSearchResult(BaseSearchResult):
    project_id: str              # Project identifier
    project_name: str            # Human-readable project name
    relationship_context: List[str]  # Related project IDs
```

**Example Result**:

```python
EnhancedSearchResult(
    file_path="/home/user/backend/auth/models.py",
    file_name="models.py",
    file_type="python",
    similarity_score=0.89,
    confidence_score=0.92,
    file_size=2048,
    snippet="class User(Base):\n    id: int...",
    metadata={
        "indexed_time": "2024-01-15T10:30:00Z",
        "modified_time": "2024-01-14T15:20:00Z",
        "project_priority": "high",
        "keyword_score": 0.75
    },
    project_id="backend",
    project_name="Backend API",
    relationship_context=["frontend", "shared"]
)
```

---

## Cross-Project Ranking

### Ranking Formula

```python
final_score = (
    vector_similarity * 1.0 +
    project_priority_weight * 0.3 +
    relationship_boost * 0.2 +
    recency_boost * 0.1 +
    exact_match_boost * 0.5
)
```

### Ranking Factors

#### 1. Vector Similarity (Base Score)
- **Weight**: 1.0
- **Range**: 0.0 - 1.0
- Cosine similarity between query and document embeddings

#### 2. Project Priority
- **Weight**: 0.3
- **Multipliers**:
  - `critical`: 1.5x
  - `high`: 1.2x
  - `normal`: 1.0x
  - `low`: 0.7x

**Configuration**:
```json
{
  "projects": [
    {
      "id": "backend",
      "indexing": {
        "priority": "critical"
      }
    }
  ]
}
```

#### 3. Relationship Boost
- **Weight**: 0.2
- **Boost Values**:
  - Target project: 1.0 (full boost)
  - Direct dependency: 0.5 (half boost)
  - Semantic similarity: 0.0 - 1.0 (proportional)

#### 4. Recency Boost
- **Weight**: 0.1
- **Decay**: Linear over 30 days
- Files modified today: 1.0
- Files 30+ days old: 0.0

#### 5. Exact Match Boost
- **Weight**: 0.5
- **Computation**: Jaccard similarity of query tokens vs content tokens
- Rewards exact keyword matches

---

## Performance Optimizations

### 1. Parallel Search
Search multiple projects concurrently using `asyncio.gather`:

```python
# Configure concurrency
search = WorkspaceSearch()
search.max_concurrent_searches = 10  # Default: 10
```

### 2. Early Termination
Stop searching if high-scoring results are found:

```python
search.early_termination_threshold = 0.95  # Default: 0.95
```

### 3. Result Streaming
Stream results for large result sets:

```python
async for result in search.search_streaming(
    query="optimization algorithms",
    scope=SearchScope.WORKSPACE,
    limit=100
):
    process_result(result)
```

### 4. Smart Caching
- Query embeddings are generated once per search
- Project contexts are cached
- Relationship graph computed on initialization

---

## Search Metrics

### SearchMetrics

Track detailed search performance:

```python
@dataclass
class SearchMetrics:
    total_time_ms: float                # Total search time
    projects_searched: int              # Number of projects searched
    total_results_before_merge: int     # Results before deduplication
    total_results_after_merge: int      # Final result count
    deduplicated_count: int             # Number of duplicates removed
    projects_searched_list: List[str]   # List of searched project IDs
    embedding_time_ms: float            # Time to generate embeddings
    search_time_ms: float               # Time spent searching vectors
    ranking_time_ms: float              # Time spent ranking results
```

**Example**:
```python
results, metrics = await search.search(...)

print(f"Searched {metrics.projects_searched} projects in {metrics.total_time_ms:.2f}ms")
print(f"Found {metrics.total_results_after_merge} results")
print(f"Removed {metrics.deduplicated_count} duplicates")
```

---

## API Reference

### WorkspaceSearch Class

#### Constructor

```python
WorkspaceSearch(
    workspace_manager=None,      # WorkspaceManager instance
    vector_store=None,           # VectorStore instance
    relationship_graph=None      # ProjectRelationshipGraph instance
)
```

#### Main Search Method

```python
async def search(
    query: str,                          # Natural language query
    scope: SearchScope = WORKSPACE,      # Search scope
    project_id: Optional[str] = None,    # Target project (required for PROJECT/DEPS/RELATED)
    include_dependencies: bool = True,   # Include dependencies (DEPS scope)
    limit: int = 50,                     # Max results
    filters: Optional[SearchFilters] = None,  # Search filters
    similarity_threshold: float = 0.7    # Min similarity (RELATED scope)
) -> Tuple[List[EnhancedSearchResult], SearchMetrics]
```

#### Specialized Search Methods

```python
async def search_project(
    project_id: str,
    query: str,
    limit: int = 50,
    filters: Optional[SearchFilters] = None
) -> List[EnhancedSearchResult]

async def search_dependencies(
    project_id: str,
    query: str,
    include_dependencies: bool = True,
    limit: int = 50,
    filters: Optional[SearchFilters] = None
) -> List[EnhancedSearchResult]

async def search_workspace(
    query: str,
    limit: int = 50,
    filters: Optional[SearchFilters] = None
) -> List[EnhancedSearchResult]

async def search_related(
    project_id: str,
    query: str,
    similarity_threshold: float = 0.7,
    limit: int = 50,
    filters: Optional[SearchFilters] = None
) -> List[EnhancedSearchResult]

async def search_streaming(
    query: str,
    scope: SearchScope = WORKSPACE,
    project_id: Optional[str] = None,
    limit: int = 50
) -> AsyncGenerator[EnhancedSearchResult, None]
```

---

## Usage Examples

### Example 1: Basic Workspace Search

```python
from src.search.workspace_search import WorkspaceSearch, SearchScope

search = WorkspaceSearch()

results, metrics = await search.search(
    query="authentication implementation",
    scope=SearchScope.WORKSPACE,
    limit=20
)

for result in results[:5]:
    print(f"{result.file_name} ({result.project_name})")
    print(f"  Score: {result.confidence_score:.3f}")
    print(f"  Snippet: {result.snippet[:80]}...")
```

### Example 2: Search with Filters

```python
from src.search.filters import SearchFilters

filters = SearchFilters(
    file_types=[".py", ".ts"],
    directories=["src/", "app/"],
    exclude_patterns=["test", "__pycache__"],
    min_score=0.7
)

results, metrics = await search.search(
    query="database models",
    scope=SearchScope.PROJECT,
    project_id="backend",
    filters=filters,
    limit=10
)
```

### Example 3: Dependency-Aware Search

```python
# Initialize with relationship graph
from src.workspace.relationship_graph import ProjectRelationshipGraph

graph = ProjectRelationshipGraph()
graph.add_project("frontend")
graph.add_project("backend")
graph.add_relationship("frontend", "backend", RelationshipType.API_CLIENT)

search = WorkspaceSearch(relationship_graph=graph)

results, metrics = await search.search(
    query="API endpoints",
    scope=SearchScope.DEPENDENCIES,
    project_id="frontend",
    include_dependencies=True,
    limit=20
)

print(f"Searched projects: {metrics.projects_searched_list}")
```

### Example 4: Streaming Large Result Sets

```python
async def process_large_search():
    search = WorkspaceSearch()

    async for result in search.search_streaming(
        query="TODO comments",
        scope=SearchScope.WORKSPACE,
        limit=1000
    ):
        # Process each result as it arrives
        print(f"Found: {result.file_path}")
        await save_to_database(result)
```

---

## Integration with Workspace Manager

When integrated with a workspace manager:

```python
from src.workspace.manager import WorkspaceManager
from src.workspace.multi_root_store import MultiRootVectorStore
from src.workspace.relationship_graph import ProjectRelationshipGraph

# Initialize workspace components
workspace = WorkspaceManager(workspace_path=".context-workspace.json")
await workspace.initialize()

# Initialize workspace search with full context
search = WorkspaceSearch(
    workspace_manager=workspace,
    vector_store=workspace.multi_root_store,
    relationship_graph=workspace.relationship_graph
)

# Now search has full project awareness
results, metrics = await search.search(
    query="user authentication",
    scope=SearchScope.WORKSPACE,
    limit=50
)
```

---

## Configuration

### Ranking Weights

Customize ranking weights:

```python
search = WorkspaceSearch()

# Adjust weights
search.vector_similarity_weight = 1.0      # Semantic relevance
search.project_priority_weight = 0.5       # Boost important projects
search.relationship_boost_weight = 0.3     # Boost related projects
search.recency_boost_weight = 0.2          # Boost recent files
search.exact_match_boost_weight = 0.4      # Boost keyword matches
```

### Priority Multipliers

Customize project priority multipliers:

```python
search.priority_multipliers = {
    "critical": 2.0,   # 2x boost
    "high": 1.5,       # 1.5x boost
    "normal": 1.0,     # No boost
    "low": 0.5         # 0.5x (penalty)
}
```

### Performance Settings

```python
search.parallel_search_enabled = True
search.max_concurrent_searches = 10
search.early_termination_threshold = 0.95
```

---

## Best Practices

### 1. Choose the Right Scope
- Use **PROJECT** when you know the project
- Use **DEPENDENCIES** for features spanning multiple projects
- Use **WORKSPACE** for exploratory searches
- Use **RELATED** for cross-project pattern discovery

### 2. Optimize Query Construction
```python
# Good: Specific, descriptive
"user authentication with JWT tokens"

# Bad: Too generic
"auth"

# Good: Include context
"database migration rollback strategy"

# Bad: Single word
"migration"
```

### 3. Use Filters Appropriately
```python
# Narrow down by file type
filters = SearchFilters(file_types=[".py"])

# Exclude test files
filters = SearchFilters(exclude_patterns=["test_", "_test.py"])

# Search specific directories
filters = SearchFilters(directories=["src/core/", "app/"])
```

### 4. Handle Large Result Sets
```python
# Use streaming for large searches
async for result in search.search_streaming(query, limit=1000):
    process(result)

# Or paginate
page_size = 50
for page in range(0, total, page_size):
    results, _ = await search.search(query, limit=page_size, offset=page)
```

### 5. Monitor Performance
```python
results, metrics = await search.search(query)

if metrics.total_time_ms > 1000:
    logger.warning(f"Slow search: {metrics.total_time_ms}ms")

if metrics.deduplicated_count > 10:
    logger.info(f"Many duplicates: {metrics.deduplicated_count}")
```

---

## Troubleshooting

### Problem: Slow searches across many projects

**Solution**: Reduce concurrency or enable early termination
```python
search.max_concurrent_searches = 5
search.early_termination_threshold = 0.90
```

### Problem: Irrelevant results

**Solution**: Adjust ranking weights
```python
# Increase exact match weight
search.exact_match_boost_weight = 1.0

# Decrease similarity weight
search.vector_similarity_weight = 0.7
```

### Problem: Missing expected results

**Solution**: Check project relationships
```python
# Verify project is in workspace
context = await workspace.get_project("project_id")

# Check dependencies
deps = relationship_graph.get_dependencies("project_id")
print(f"Dependencies: {deps}")
```

### Problem: Duplicate results

**Solution**: Enable automatic deduplication (enabled by default)
```python
# Deduplication happens in _merge_and_rank_results
# Keeps highest-scoring duplicate by file path
```

---

## Testing

Run workspace search tests:

```bash
# All tests
pytest tests/test_workspace_search.py -v

# Specific test class
pytest tests/test_workspace_search.py::TestWorkspaceSearch -v

# With coverage
pytest tests/test_workspace_search.py --cov=src.search.workspace_search
```

---

## See Also

- [Architecture Document](../ARCHITECTURE_PROJECT_AWARE.md)
- [Workspace Configuration](./WORKSPACE_CONFIG.md)
- [Relationship Graph](./RELATIONSHIP_GRAPH.md)
- [Multi-Root Vector Store](./MULTI_ROOT_STORE.md)

---

## Future Enhancements

1. **Query Expansion**: Automatically expand queries with synonyms
2. **Negative Filters**: Exclude results matching patterns
3. **Custom Ranking**: User-defined ranking functions
4. **Result Clustering**: Group similar results
5. **Search History**: Track and suggest previous queries
6. **Faceted Search**: Filter results by project, language, date
7. **Incremental Search**: Real-time results as user types

---

## License

Part of the Context project. See LICENSE file for details.
