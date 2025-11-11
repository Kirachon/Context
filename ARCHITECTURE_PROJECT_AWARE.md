# Project-Aware Context Engine Architecture
## Ultimate Enhancement Design Document

**Version:** 2.0.0
**Date:** 2025-11-11
**Status:** Implementation Ready

---

## 🎯 Vision

Transform Context from a single-folder code indexing tool into a **workspace-aware, multi-project context engine** that understands relationships across repositories, monorepos, and polyrepo architectures.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     WORKSPACE MANAGER                            │
│  (Orchestrates multiple projects, relationships, and search)     │
└───────────────┬─────────────────────────────────────────────────┘
                │
    ┌───────────┴───────────┬──────────────┬──────────────┐
    │                       │              │              │
┌───▼────┐          ┌───────▼──────┐  ┌───▼──────┐  ┌───▼──────┐
│Project │          │   Project    │  │ Project  │  │ Project  │
│   A    │◄────────►│      B       │  │    C     │  │    D     │
│Frontend│  refs    │   Backend    │  │  Shared  │  │  Docs    │
└───┬────┘          └───────┬──────┘  └────┬─────┘  └────┬─────┘
    │                       │              │              │
    │    ┌──────────────────┴──────────────┴──────────────┘
    │    │
    ▼    ▼
┌────────────────────────────────────────────┐
│      PROJECT RELATIONSHIP GRAPH            │
│  • Dependency tracking                     │
│  • Semantic similarity                     │
│  • Import/export relationships             │
│  • Cross-reference mapping                 │
└────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│      MULTI-ROOT VECTOR STORE               │
│  ┌──────────┬──────────┬──────────┐       │
│  │ project_a│ project_b│ project_c│       │
│  │ vectors  │ vectors  │ vectors  │       │
│  └──────────┴──────────┴──────────┘       │
│      (Isolated collections per project)    │
└────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│    CROSS-PROJECT SEMANTIC SEARCH           │
│  • Project-scoped search                   │
│  • Workspace-wide search                   │
│  • Relationship-aware ranking              │
│  • Multi-project result merging            │
└────────────────────────────────────────────┘
```

---

## 📦 Core Components

### 1. Workspace Configuration System

**File Format:** `.context-workspace.json` (VSCode-compatible)

```json
{
  "version": "2.0.0",
  "name": "My Full-Stack App",
  "projects": [
    {
      "id": "frontend",
      "name": "Frontend (React)",
      "path": "/home/user/projects/myapp-frontend",
      "type": "web_frontend",
      "language": ["typescript", "tsx"],
      "dependencies": ["backend", "shared"],
      "indexing": {
        "enabled": true,
        "priority": "high",
        "exclude": ["node_modules", "dist", ".next"]
      },
      "metadata": {
        "framework": "next.js",
        "version": "14.0.0"
      }
    },
    {
      "id": "backend",
      "name": "Backend (FastAPI)",
      "path": "/home/user/projects/myapp-backend",
      "type": "api_server",
      "language": ["python"],
      "dependencies": ["shared"],
      "indexing": {
        "enabled": true,
        "priority": "high",
        "exclude": ["venv", "__pycache__", ".pytest_cache"]
      },
      "metadata": {
        "framework": "fastapi",
        "version": "0.104.0"
      }
    },
    {
      "id": "shared",
      "name": "Shared Types & Utils",
      "path": "/home/user/projects/myapp-shared",
      "type": "library",
      "language": ["typescript", "python"],
      "dependencies": [],
      "indexing": {
        "enabled": true,
        "priority": "critical"
      }
    },
    {
      "id": "docs",
      "name": "Documentation",
      "path": "/home/user/projects/myapp-docs",
      "type": "documentation",
      "language": ["markdown"],
      "dependencies": [],
      "indexing": {
        "enabled": true,
        "priority": "low"
      }
    }
  ],
  "relationships": [
    {
      "from": "frontend",
      "to": "backend",
      "type": "api_client",
      "description": "Frontend calls backend REST API"
    },
    {
      "from": "frontend",
      "to": "shared",
      "type": "imports",
      "description": "Shared TypeScript types"
    },
    {
      "from": "backend",
      "to": "shared",
      "type": "imports",
      "description": "Shared Python utilities"
    }
  ],
  "search": {
    "default_scope": "workspace",
    "cross_project_ranking": true,
    "relationship_boost": 1.5
  }
}
```

**Features:**
- Multiple project paths (absolute or relative to workspace file)
- Project metadata (type, language, framework)
- Explicit dependency declarations
- Per-project indexing configuration
- Cross-project relationship definitions

---

### 2. Workspace Manager

**Location:** `src/workspace/manager.py`

**Responsibilities:**
- Load and parse `.context-workspace.json`
- Instantiate per-project components (indexers, monitors, vector stores)
- Manage project lifecycle (add, remove, reload)
- Coordinate cross-project operations
- Hot-reload on configuration changes

**Key Classes:**

```python
class WorkspaceManager:
    """Manages multiple projects within a workspace"""

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.config = WorkspaceConfig.load(workspace_path)
        self.projects: Dict[str, Project] = {}
        self.relationship_graph = ProjectRelationshipGraph()

    async def initialize(self):
        """Initialize all projects and build relationship graph"""

    async def add_project(self, project_config: ProjectConfig):
        """Add a new project to the workspace"""

    async def remove_project(self, project_id: str):
        """Remove a project from the workspace"""

    async def reload_project(self, project_id: str):
        """Reload a project's index"""

    def get_project(self, project_id: str) -> Project:
        """Get a specific project"""

    async def search_workspace(self, query: str, **kwargs) -> List[SearchResult]:
        """Search across all projects with relationship-aware ranking"""
```

```python
class Project:
    """Represents a single project within a workspace"""

    def __init__(self, config: ProjectConfig):
        self.id = config.id
        self.name = config.name
        self.path = config.path
        self.config = config

        # Per-project instances (no more global singletons!)
        self.vector_store = VectorStore(collection_name=f"project_{self.id}")
        self.ast_store = ASTStore(base_collection=f"project_{self.id}")
        self.file_monitor = FileMonitor(paths=[self.path])
        self.indexer = FileIndexer(project=self)

    async def initialize(self):
        """Initialize project components"""

    async def index(self):
        """Index this project's files"""

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search within this project only"""
```

---

### 3. Project Relationship Graph

**Location:** `src/workspace/relationship_graph.py`

**Purpose:** Track dependencies, imports, and semantic relationships between projects

**Graph Structure:**

```python
class ProjectRelationshipGraph:
    """Graph of relationships between projects"""

    def __init__(self):
        self.graph = nx.DiGraph()  # NetworkX directed graph
        self.semantic_similarity_cache = {}

    def add_project(self, project: Project):
        """Add a project node to the graph"""

    def add_relationship(self, from_id: str, to_id: str, rel_type: str, metadata: dict):
        """Add explicit relationship (from workspace config)"""

    async def discover_relationships(self, project: Project):
        """Auto-discover implicit relationships via:
        - Import statement analysis
        - Cross-file references
        - Semantic similarity (embeddings)
        """

    def get_dependencies(self, project_id: str, depth: int = 1) -> List[str]:
        """Get all dependencies of a project (transitive)"""

    def get_dependents(self, project_id: str) -> List[str]:
        """Get all projects that depend on this project"""

    def get_related_projects(self, project_id: str, threshold: float = 0.7) -> List[Tuple[str, float]]:
        """Get semantically related projects with similarity scores"""

    async def compute_semantic_similarity(self, project_a: str, project_b: str) -> float:
        """Compute embedding-based similarity between projects"""
```

**Relationship Types:**
- `imports` - Direct code imports
- `api_client` - REST/GraphQL API consumption
- `shared_database` - Shared data layer
- `event_driven` - Message queue/event bus
- `semantic_similarity` - Embedding-based similarity
- `dependency` - Generic dependency (npm, pip, cargo)

---

### 4. Multi-Root Vector Store

**Location:** `src/vector_db/multi_root_store.py`

**Key Changes:**
- Per-project Qdrant collections (e.g., `project_frontend_vectors`)
- Project metadata stored with each vector
- Cross-collection search support
- Collection lifecycle management

```python
class MultiRootVectorStore:
    """Vector store supporting multiple project collections"""

    def __init__(self):
        self.client = None
        self.collections: Dict[str, str] = {}  # project_id -> collection_name

    async def ensure_project_collection(self, project: Project):
        """Create/verify collection for a project"""
        collection_name = f"project_{project.id}_vectors"

        # Create collection with project metadata in payload schema
        await self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            payload_schema={
                "file_path": PayloadSchemaType.KEYWORD,
                "project_id": PayloadSchemaType.KEYWORD,
                "project_name": PayloadSchemaType.KEYWORD,
                "language": PayloadSchemaType.KEYWORD,
                "chunk_index": PayloadSchemaType.INTEGER,
            }
        )

    async def add_vectors(self, project_id: str, vectors: List[VectorData]):
        """Add vectors to a project's collection"""
        collection_name = self.collections[project_id]
        # Add project_id, project_name to payload

    async def search_project(self, project_id: str, query_vector: List[float], limit: int = 10):
        """Search within a single project"""

    async def search_workspace(self, query_vector: List[float], project_ids: List[str], limit: int = 10):
        """Search across multiple projects with merged results"""
        # Parallel search across collections, merge by score
```

---

### 5. Cross-Project Semantic Search

**Location:** `src/search/workspace_search.py`

**Search Modes:**
1. **Project-scoped:** Search within one project only
2. **Dependency-aware:** Search project + its dependencies
3. **Workspace-wide:** Search all projects
4. **Related-projects:** Search semantically related projects

```python
class WorkspaceSearch:
    """Advanced search with project-awareness"""

    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace_manager = workspace_manager
        self.relationship_graph = workspace_manager.relationship_graph

    async def search(
        self,
        query: str,
        scope: SearchScope = SearchScope.WORKSPACE,
        project_id: Optional[str] = None,
        include_dependencies: bool = True,
        limit: int = 50
    ) -> List[SearchResult]:
        """
        Unified search interface

        scope:
        - PROJECT: Search within project_id only
        - DEPENDENCIES: Search project_id + dependencies
        - WORKSPACE: Search all projects
        - RELATED: Search semantically related projects
        """

    async def _rank_cross_project_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Re-rank results considering:
        - Vector similarity score (base score)
        - Project priority (from config)
        - Relationship boost (related projects rank higher)
        - Recency boost (recent files rank higher)
        """
```

**Search Result Format:**

```python
@dataclass
class SearchResult:
    file_path: str
    content: str
    score: float
    project_id: str
    project_name: str
    language: str
    chunk_index: int
    metadata: Dict[str, Any]
    relationship_context: Optional[List[str]] = None  # Related projects
```

---

### 6. Refactored Global Singletons

**Problem:** Current codebase has 6 global singletons that prevent multi-project support

**Solution:** Replace with workspace-scoped instances

| Old Global Singleton | New Workspace-Scoped |
|---------------------|---------------------|
| `file_monitor` (global) | `project.file_monitor` (per-project) |
| `file_indexer` (global) | `project.indexer` (per-project) |
| `vector_store` (global) | `workspace.multi_root_store` (workspace-level) |
| `indexing_queue` (global) | `project.indexing_queue` (per-project) |
| `real_time_watcher` (global) | `project.watcher` (per-project) |

**Migration Strategy:**
1. Add `project: Optional[Project]` parameter to all component constructors
2. Replace global instances with factory methods: `create_for_project(project)`
3. Update all call sites to pass project context
4. Remove global `= ClassName()` declarations

---

## 🔧 Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
1. **Workspace Configuration**
   - Create `src/workspace/config.py` with `WorkspaceConfig`, `ProjectConfig` models
   - Implement JSON schema validation
   - Add `.context-workspace.json` example files

2. **Workspace Manager**
   - Create `src/workspace/manager.py` with `WorkspaceManager`, `Project` classes
   - Implement project lifecycle (add, remove, reload)
   - Add workspace initialization

3. **Multi-Root Vector Store**
   - Create `src/vector_db/multi_root_store.py`
   - Implement per-project collection management
   - Add cross-collection search

### Phase 2: Relationship Graph (Week 1-2)
4. **Project Relationship Graph**
   - Create `src/workspace/relationship_graph.py`
   - Implement graph data structure (NetworkX)
   - Add relationship discovery (imports, references)
   - Compute semantic similarity between projects

### Phase 3: Search & Indexing (Week 2)
5. **Cross-Project Search**
   - Create `src/search/workspace_search.py`
   - Implement search scopes (project, dependencies, workspace)
   - Add relationship-aware ranking

6. **Refactor Singletons**
   - Update `FileMonitor` to accept project parameter
   - Update `FileIndexer` for per-project instances
   - Update `IndexingQueue` for per-project queues
   - Remove all global singleton instances

### Phase 4: MCP Tools & CLI (Week 2-3)
7. **Update MCP Tools**
   - Modify `search_codebase` tool to accept `project_id` parameter
   - Add `list_projects` tool
   - Add `search_workspace` tool
   - Add `get_project_relationships` tool
   - Update `get_indexing_status` to show per-project status

8. **CLI for Workspace Management**
   - Add `context workspace init` - Create workspace config
   - Add `context workspace add-project` - Add project to workspace
   - Add `context workspace list` - List all projects
   - Add `context workspace index` - Index all projects
   - Add `context workspace search` - Search workspace

### Phase 5: Testing & Documentation (Week 3)
9. **Comprehensive Tests**
   - Unit tests for all new components
   - Integration tests for multi-project scenarios
   - Performance tests (10+ projects, 100k+ files)

10. **Documentation**
    - Update README with multi-project examples
    - Write migration guide (v1 → v2)
    - Create workspace configuration guide
    - Add architecture diagrams

---

## 🎨 Example Usage

### Creating a Workspace

```bash
# Initialize workspace
context workspace init --name "MyApp Workspace"

# Add projects
context workspace add-project \
  --id frontend \
  --name "Frontend (React)" \
  --path /home/user/projects/myapp-frontend \
  --type web_frontend

context workspace add-project \
  --id backend \
  --name "Backend (FastAPI)" \
  --path /home/user/projects/myapp-backend \
  --type api_server \
  --depends-on frontend

# Index workspace
context workspace index

# Search across workspace
context workspace search "authentication logic"

# Search within project
context workspace search "user model" --project backend

# Search with dependencies
context workspace search "API types" --project frontend --include-deps
```

### MCP Tool Usage (Claude Desktop)

```typescript
// Search entire workspace
await search_workspace({
  query: "how is authentication handled?",
  scope: "workspace",
  limit: 20
});

// Search specific project
await search_workspace({
  query: "database models",
  scope: "project",
  project_id: "backend",
  limit: 10
});

// Get project relationships
await get_project_relationships({
  project_id: "frontend"
});
// Returns: ["backend", "shared"] with relationship types

// List all projects
await list_projects();
// Returns: [
//   {id: "frontend", name: "Frontend (React)", path: "...", status: "indexed"},
//   {id: "backend", name: "Backend (FastAPI)", path: "...", status: "indexing"},
// ]
```

---

## 📊 Performance Considerations

### Scaling Characteristics

| Metric | Single-Folder (v1) | Multi-Project (v2) |
|--------|-------------------|-------------------|
| Max Projects | 1 | 50+ |
| Max Files | 100k | 500k+ (across all projects) |
| Search Latency | ~100ms | ~200ms (10 projects) |
| Indexing Throughput | 100 files/sec | 100 files/sec per project |
| Memory Usage | 500MB | 500MB + (50MB × projects) |

### Optimizations
- **Parallel Indexing:** Index projects in parallel (ThreadPoolExecutor)
- **Lazy Loading:** Only load projects when accessed
- **Smart Caching:** Cache relationship graph and project metadata
- **Collection Sharding:** Use Qdrant sharding for large projects

---

## 🔒 Security & Privacy

- **Path Validation:** All project paths validated against filesystem access
- **Collection Isolation:** Each project's vectors in separate collections (no cross-contamination)
- **API Key Management:** Per-project API keys for embedding providers
- **Access Control:** Future: Role-based access to projects

---

## 🚀 Migration Guide (v1 → v2)

### Automatic Migration

```bash
# Convert existing single-folder setup to workspace
context migrate-to-workspace --from /home/user/project --workspace-name "My Project"
```

This will:
1. Create `.context-workspace.json` with single project
2. Rename `context_vectors` → `project_default_vectors`
3. Update settings.py to load workspace config

### Manual Migration

1. Create `.context-workspace.json`:
```json
{
  "version": "2.0.0",
  "name": "My Project",
  "projects": [
    {
      "id": "default",
      "name": "My Project",
      "path": "/home/user/project",
      "type": "application",
      "language": ["python"],
      "indexing": {"enabled": true}
    }
  ]
}
```

2. Re-index: `context workspace index`

---

## 🎯 Success Metrics

- ✅ Support 50+ projects per workspace
- ✅ <200ms search latency across 10 projects
- ✅ <5min initial indexing for 100k files workspace
- ✅ <100MB memory overhead per project
- ✅ 100% test coverage for new components
- ✅ Zero breaking changes to existing single-folder setups (backwards compatible)

---

## 📚 References

- **VSCode Multi-Root Workspaces:** https://code.visualstudio.com/docs/editing/workspaces/multi-root-workspaces
- **RepoHyper (arXiv 2403.06095):** Repository-level semantic graphs
- **txtai:** https://github.com/neuml/txtai - Multi-index semantic search
- **NetworkX:** https://networkx.org/ - Graph data structures

---

## ✅ Definition of Done

- [ ] All 8 singleton limitations fixed
- [ ] Workspace configuration system implemented
- [ ] Multi-root vector store operational
- [ ] Project relationship graph functional
- [ ] Cross-project search with ranking
- [ ] 10+ MCP tools updated
- [ ] CLI commands for workspace management
- [ ] 90%+ test coverage
- [ ] Documentation complete
- [ ] Migration guide tested
- [ ] Performance benchmarks met

---

**Next Steps:** Begin Phase 1 implementation with parallel agent deployment.
