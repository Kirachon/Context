# Context - Technical Specification

**Author:** BMad Technical Specification Agent
**Date:** 2025-10-31
**Project Level:** 3
**Project Type:** Large-scale enterprise software application
**Development Context:** 100% offline AI coding assistant with MCP integration

---

## Source Tree Structure

```
context/
├── src/
│   ├── mcp_server/                 # MCP protocol server implementation
│   │   ├── __init__.py
│   │   ├── server.py              # FastMCP server core
│   │   ├── tools/                 # MCP tool implementations
│   │   │   ├── __init__.py
│   │   │   ├── search.py          # Semantic search tool
│   │   │   ├── index.py           # Code indexing tool
│   │   │   ├── status.py          # System status tool
│   │   │   └── config.py          # Configuration tool
│   │   └── handlers/              # Request/response handlers
│   │       ├── __init__.py
│   │       ├── search_handler.py
│   │       ├── index_handler.py
│   │       └── health_handler.py
│   ├── code_intelligence/         # Code parsing and analysis
│   │   ├── __init__.py
│   │   ├── parser.py              # Tree-sitter integration
│   │   ├── analyzer.py            # Code structure analysis
│   │   ├── pattern_recognizer.py  # Pattern detection
│   │   ├── languages/             # Language-specific parsers
│   │   │   ├── __init__.py
│   │   │   ├── python_parser.py
│   │   │   ├── javascript_parser.py
│   │   │   ├── typescript_parser.py
│   │   │   ├── java_parser.py
│   │   │   ├── cpp_parser.py
│   │   │   ├── go_parser.py
│   │   │   └── rust_parser.py
│   │   └── models/                # Data models for code structures
│   │       ├── __init__.py
│   │       ├── ast_models.py
│   │       ├── pattern_models.py
│   │       └── relationship_models.py
│   ├── vector_database/           # Qdrant integration
│   │   ├── __init__.py
│   │   ├── client.py              # Qdrant client wrapper
│   │   ├── embeddings.py          # Embedding generation
│   │   ├── collections.py         # Collection management
│   │   ├── search.py              # Vector search operations
│   │   └── indexing.py            # Vector indexing logic
│   ├── ai_processing/             # Ollama integration
│   │   ├── __init__.py
│   │   ├── client.py              # Ollama client
│   │   ├── prompt_analyzer.py     # Query analysis
│   │   ├── context_enhancer.py    # Context enrichment
│   │   ├── response_generator.py  # AI response generation
│   │   └── models/                # AI model management
│   │       ├── __init__.py
│   │       ├── model_manager.py
│   │       └── model_cache.py
│   ├── file_monitor/              # File system monitoring
│   │   ├── __init__.py
│   │   ├── watcher.py             # File system watcher
│   │   ├── indexer.py             # Incremental indexing
│   │   ├── queue_manager.py       # Indexing queue
│   │   └── change_detector.py     # Change classification
│   ├── caching/                   # Redis caching
│   │   ├── __init__.py
│   │   ├── cache_client.py        # Redis client wrapper
│   │   ├── query_cache.py         # Query result caching
│   │   ├── session_cache.py       # Session management
│   │   └── cache_manager.py       # Cache coordination
│   ├── data_storage/              # PostgreSQL integration
│   │   ├── __init__.py
│   │   ├── database.py            # Database connection
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── repositories/          # Data access layer
│   │   │   ├── __init__.py
│   │   │   ├── metadata_repo.py
│   │   │   ├── audit_repo.py
│   │   │   └── config_repo.py
│   │   └── migrations/            # Database migrations
│   │       └── versions/
│   ├── security/                  # Security and authentication
│   │   ├── __init__.py
│   │   ├── auth.py                # Authentication
│   │   ├── authorization.py       # RBAC
│   │   ├── encryption.py          # Data encryption
│   │   └── audit.py               # Security auditing
│   ├── monitoring/                # Monitoring and observability
│   │   ├── __init__.py
│   │   ├── metrics.py             # Prometheus metrics
│   │   ├── logging.py             # Structured logging
│   │   ├── health.py              # Health checks
│   │   └── performance.py         # Performance monitoring
│   ├── config/                    # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py            # Application settings
│   │   ├── environment.py         # Environment handling
│   │   └── validation.py          # Config validation
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── exceptions.py          # Custom exceptions
│       ├── helpers.py             # Helper functions
│       └── constants.py           # Application constants
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   ├── performance/               # Performance tests
│   └── fixtures/                  # Test data
├── docs/                          # Documentation
│   ├── api/                       # API documentation
│   ├── deployment/                # Deployment guides
│   └── user_guide/                # User documentation
├── deployment/                    # Deployment configurations
│   ├── docker/                    # Docker configurations
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── docker-compose.prod.yml
│   ├── kubernetes/                # Kubernetes manifests
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── helm/                      # Helm charts
│       └── context/
├── scripts/                       # Utility scripts
│   ├── setup.sh                   # Development setup
│   ├── migrate.py                 # Database migration
│   └── benchmark.py               # Performance benchmarking
├── requirements/                  # Dependencies
│   ├── base.txt                   # Base dependencies
│   ├── dev.txt                    # Development dependencies
│   └── prod.txt                   # Production dependencies
├── .env.example                   # Environment variables template
├── pyproject.toml                 # Python project configuration
├── README.md                      # Project documentation
└── Makefile                       # Common tasks
```

---

## Technical Approach

### Core Architecture Principles

1. **Microservices Architecture**: Each major component (search, indexing, AI processing) operates as an independent service with clear boundaries and APIs.

2. **Local-First Processing**: All data processing occurs locally with no external dependencies. The system is designed for air-gapped deployments.

3. **Event-Driven Design**: Components communicate through events and message queues for loose coupling and scalability.

4. **Caching Strategy**: Multi-layer caching (Redis, application-level, query-level) optimizes performance for frequently accessed data.

5. **Incremental Processing**: File system changes trigger incremental indexing and updates rather than full reprocessing.

### Implementation Approach

**Phase 1: Core Infrastructure (Stories 1.1-1.4)**
- Set up Docker Compose development environment
- Implement basic FastMCP server with health checks
- Integrate Qdrant vector database with basic operations
- Set up PostgreSQL for metadata storage

**Phase 2: Search Foundation (Stories 1.5-2.1)**
- Implement Tree-sitter multi-language parsing
- Build vector embedding generation pipeline
- Create basic semantic search functionality
- Add file system monitoring and incremental indexing

**Phase 3: AI Integration (Stories 2.2-3.2)**
- Integrate Ollama for local LLM inference
- Implement prompt analysis and enhancement
- Build context-aware response generation
- Add Git history integration

**Phase 4: Advanced Features (Stories 3.3-5.5)**
- Implement advanced filtering and ranking
- Add pattern recognition and categorization
- Build enterprise security features
- Optimize performance for large scale

---

## Implementation Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Language** | Python | 3.11+ | Primary implementation language |
| **MCP Framework** | FastMCP | 1.0+ | Claude Code CLI integration |
| **Vector Database** | Qdrant | 1.7+ | Semantic search storage |
| **Local LLM** | Ollama | 0.1.0+ | AI inference |
| **Code Parsing** | Tree-sitter | 0.20+ | Multi-language AST generation |
| **Caching** | Redis | 7.2+ | Query performance optimization |
| **Database** | PostgreSQL | 15+ | Metadata and persistence |
| **Containerization** | Docker | 24.0+ | Application packaging |
| **Orchestration** | Docker Compose | 2.20+ | Development environment |
| **Orchestration** | Kubernetes | 1.28+ | Production deployment |

### Development Dependencies

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Web Framework** | FastAPI | 0.104+ | API development |
| **Async Runtime** | uvicorn | 0.24+ | ASGI server |
| **Database ORM** | SQLAlchemy | 2.0+ | Database operations |
| **Migration Tool** | Alembic | 1.12+ | Database migrations |
| **Testing** | pytest | 7.4+ | Test framework |
| **Async Testing** | pytest-asyncio | 0.21+ | Async test support |
| **HTTP Testing** | httpx | 0.25+ | HTTP client testing |
| **Code Quality** | black | 23.10+ | Code formatting |
| **Linting** | ruff | 0.1+ | Code linting |
| **Type Checking** | mypy | 1.7+ | Static type checking |

### Machine Learning Dependencies

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **ML Framework** | sentence-transformers | 2.2+ | Text embeddings |
| **Numerical Computing** | numpy | 1.25+ | Vector operations |
| **Data Processing** | pandas | 2.1+ | Data manipulation |
| **ML Client** | ollama-python | 0.1+ | Ollama API client |
| **Vector Operations** | qdrant-client | 1.7+ | Qdrant database client |

### Monitoring and Observability

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Metrics** | prometheus-client | 0.19+ | Application metrics |
| **Logging** | structlog | 23.2+ | Structured logging |
| **Distributed Tracing** | opentelemetry | 1.21+ | Request tracing |
| **Health Checks** | starlette-prometheus | 0.22+ | HTTP metrics |

---

## Technical Details

### Component 1: MCP Server Implementation

**FastMCP Server Configuration**
```python
# src/mcp_server/server.py
from fastmcp import FastMCP
from src.mcp_server.tools.search import search_tool
from src.mcp_server.tools.index import index_tool
from src.mcp_server.tools.status import status_tool

# Initialize FastMCP server
app = FastMCP(
    name="context",
    version="1.0.0",
    description="100% offline AI coding assistant"
)

# Register tools
app.add_tool(search_tool)
app.add_tool(index_tool)
app.add_tool(status_tool)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

**Tool Interface Specifications**
```python
# src/mcp_server/tools/search.py
from fastmcp.tools import tool
from src.vector_database.search import VectorSearchEngine

@tool
async def semantic_search(
    query: str,
    file_types: list[str] = None,
    directories: list[str] = None,
    limit: int = 10
) -> dict:
    """
    Search codebase using natural language queries

    Args:
        query: Natural language search query
        file_types: Filter by file extensions
        directories: Filter by directory paths
        limit: Maximum number of results

    Returns:
        Search results with code snippets and metadata
    """
    search_engine = VectorSearchEngine()
    results = await search_engine.search(
        query=query,
        filters={
            "file_types": file_types,
            "directories": directories
        },
        limit=limit
    )
    return results
```

### Component 2: Code Intelligence Engine

**Tree-sitter Integration**
```python
# src/code_intelligence/parser.py
from tree_sitter import Language, Parser
import tree_sitter_python, tree_sitter_javascript

class CodeParser:
    def __init__(self):
        self.parsers = {
            'python': self._create_parser(tree_sitter_python.language()),
            'javascript': self._create_parser(tree_sitter_javascript.language()),
            'typescript': self._create_parser(tree_sitter_typescript.language()),
            # Additional languages...
        }

    def parse_file(self, file_path: str, content: str) -> dict:
        """Parse code file and extract AST and metadata"""
        language = self._detect_language(file_path)
        parser = self.parsers[language]
        tree = parser.parse(bytes(content, 'utf-8'))

        return {
            'ast': tree,
            'functions': self._extract_functions(tree, language),
            'classes': self._extract_classes(tree, language),
            'imports': self._extract_imports(tree, language),
            'relationships': self._analyze_relationships(tree)
        }
```

**Pattern Recognition**
```python
# src/code_intelligence/pattern_recognizer.py
class PatternRecognizer:
    def __init__(self):
        self.patterns = {
            'error_handling': self._compile_error_pattern(),
            'api_endpoint': self._compile_api_pattern(),
            'database_query': self._compile_db_pattern(),
            # Additional patterns...
        }

    def recognize_patterns(self, ast_tree, language: str) -> list[dict]:
        """Identify common patterns in code"""
        patterns_found = []

        for pattern_name, pattern_query in self.patterns.items():
            matches = pattern_query.captures(ast_tree.root_node)
            if matches:
                patterns_found.append({
                    'pattern': pattern_name,
                    'matches': matches,
                    'confidence': self._calculate_confidence(matches)
                })

        return patterns_found
```

### Component 3: Vector Database Integration

**Qdrant Client Wrapper**
```python
# src/vector_database/client.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class VectorDatabaseClient:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)

    async def create_collection(self, collection_name: str, vector_size: int = 768):
        """Create collection for code embeddings"""
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )

    async def upsert_vectors(self, collection_name: str, points: list[PointStruct]):
        """Store code embeddings with metadata"""
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )

    async def search_similar(
        self,
        collection_name: str,
        query_vector: list[float],
        filters: dict = None,
        limit: int = 10
    ) -> list[dict]:
        """Search for similar code patterns"""
        search_filter = self._build_filter(filters) if filters else None

        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )

        return [
            {
                'id': point.id,
                'score': point.score,
                'payload': point.payload
            }
            for point in results
        ]
```

**Embedding Generation**
```python
# src/vector_database/embeddings.py
from sentence_transformers import SentenceTransformer
import torch

class EmbeddingGenerator:
    def __init__(self, model_name: str = "microsoft/codebert-base"):
        self.model = SentenceTransformer(model_name)
        self.model.eval()

    def generate_code_embedding(self, code_snippet: str, context: str = "") -> list[float]:
        """Generate vector embedding for code snippet"""
        # Combine code with context for better semantic understanding
        text = f"{context}\n{code_snippet}" if context else code_snippet

        with torch.no_grad():
            embedding = self.model.encode(text, convert_to_numpy=True)

        return embedding.tolist()

    def generate_query_embedding(self, query: str) -> list[float]:
        """Generate embedding for natural language query"""
        with torch.no_grad():
            embedding = self.model.encode(query, convert_to_numpy=True)

        return embedding.tolist()
```

### Component 4: AI Processing Layer

**Ollama Integration**
```python
# src/ai_processing/client.py
import aiohttp
import json

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    async def generate_response(
        self,
        prompt: str,
        model: str = "codellama:7b",
        context: dict = None
    ) -> str:
        """Generate AI response using local Ollama model"""

        # Enhance prompt with context
        enhanced_prompt = self._enhance_prompt(prompt, context)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": enhanced_prompt,
                    "stream": False
                }
            ) as response:
                result = await response.json()
                return result.get("response", "")

    def _enhance_prompt(self, prompt: str, context: dict) -> str:
        """Enhance prompt with relevant context"""
        if not context:
            return prompt

        context_str = "\n".join([
            f"Relevant code: {context.get('code', '')}",
            f"File: {context.get('file_path', '')}",
            f"Recent changes: {context.get('recent_changes', '')}"
        ])

        return f"""
Context:
{context_str}

Query: {prompt}

Please provide a helpful response based on the context above.
"""
```

**Prompt Analysis**
```python
# src/ai_processing/prompt_analyzer.py
class PromptAnalyzer:
    def __init__(self):
        self.intent_patterns = {
            'search': ['find', 'search', 'look for', 'where is'],
            'explain': ['explain', 'what does', 'how does', 'why'],
            'generate': ['create', 'write', 'implement', 'add'],
            'fix': ['fix', 'debug', 'error', 'issue'],
            'refactor': ['refactor', 'improve', 'optimize', 'clean up']
        }

    def analyze_intent(self, query: str) -> dict:
        """Analyze user query intent and extract key information"""
        query_lower = query.lower()

        # Detect intent
        intent = self._detect_intent(query_lower)

        # Extract entities
        entities = self._extract_entities(query)

        # Determine search scope
        scope = self._determine_scope(query)

        return {
            'intent': intent,
            'entities': entities,
            'scope': scope,
            'confidence': self._calculate_confidence(intent, entities)
        }

    def _detect_intent(self, query: str) -> str:
        """Detect primary intent from query"""
        for intent, patterns in self.intent_patterns.items():
            if any(pattern in query for pattern in patterns):
                return intent
        return 'general'
```

### Component 5: File System Monitoring

**File Watcher Implementation**
```python
# src/file_monitor/watcher.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
from pathlib import Path

class CodeFileWatcher(FileSystemEventHandler):
    def __init__(self, index_queue: asyncio.Queue):
        self.index_queue = index_queue
        self.supported_extensions = {
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h',
            '.go', '.rs', '.jsx', '.tsx', '.vue', '.html', '.css'
        }

    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory and self._is_supported_file(event.src_path):
            asyncio.create_task(
                self.index_queue.put({
                    'action': 'update',
                    'file_path': event.src_path,
                    'timestamp': time.time()
                })
            )

    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory and self._is_supported_file(event.src_path):
            asyncio.create_task(
                self.index_queue.put({
                    'action': 'create',
                    'file_path': event.src_path,
                    'timestamp': time.time()
                })
            )

    def on_deleted(self, event):
        """Handle file deletion events"""
        if not event.is_directory and self._is_supported_file(event.src_path):
            asyncio.create_task(
                self.index_queue.put({
                    'action': 'delete',
                    'file_path': event.src_path,
                    'timestamp': time.time()
                })
            )

    def _is_supported_file(self, file_path: str) -> bool:
        """Check if file type is supported for indexing"""
        return Path(file_path).suffix.lower() in self.supported_extensions
```

### Component 6: Caching Layer

**Redis Cache Implementation**
```python
# src/caching/cache_client.py
import redis.asyncio as redis
import json
import pickle
from typing import Any, Optional

class CacheClient:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        value = await self.redis.get(key)
        if value:
            return pickle.loads(value)
        return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: int = 3600
    ) -> bool:
        """Set cache value with expiration"""
        serialized = pickle.dumps(value)
        return await self.redis.setex(key, expire, serialized)

    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        return bool(await self.redis.delete(key))

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0

class QueryCache:
    def __init__(self, cache_client: CacheClient):
        self.cache = cache_client
        self.default_ttl = 1800  # 30 minutes

    async def get_search_results(self, query_hash: str) -> Optional[list]:
        """Get cached search results"""
        return await self.cache.get(f"search:{query_hash}")

    async def cache_search_results(
        self,
        query_hash: str,
        results: list,
        ttl: int = None
    ):
        """Cache search results"""
        ttl = ttl or self.default_ttl
        await self.cache.set(
            f"search:{query_hash}",
            results,
            expire=ttl
        )

    async def invalidate_file_results(self, file_path: str):
        """Invalidate cache entries for specific file"""
        pattern = f"*:{file_path}:*"
        await self.cache.invalidate_pattern(pattern)
```

### Component 7: Data Persistence

**PostgreSQL Integration**
```python
# src/data_storage/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class CodeFile(Base):
    __tablename__ = "code_files"

    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), unique=True, nullable=False)
    file_hash = Column(String(64), nullable=False)
    language = Column(String(50), nullable=False)
    indexed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    metadata = Column(JSON)
    is_active = Column(Boolean, default=True)

class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True)
    query = Column(Text, nullable=False)
    query_hash = Column(String(64), nullable=False)
    results_count = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    user_id = Column(String(100))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(200), nullable=False)
    user_id = Column(String(100))
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
```

---

## Development Setup

### Prerequisites

**System Requirements**
- **Operating System**: Linux, macOS, or Windows (with WSL2)
- **Python**: 3.11 or higher
- **RAM**: Minimum 8GB, recommended 16GB for large codebases
- **Storage**: Minimum 10GB free space
- **CPU**: 4+ cores recommended

**External Dependencies**
- **Docker**: 24.0+ for containerized services
- **Ollama**: 0.1.0+ for local LLM inference
- **Git**: For version control integration

### Development Environment Setup

**1. Clone and Setup Repository**
```bash
git clone <repository-url>
cd context
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**2. Install Dependencies**
```bash
pip install -r requirements/dev.txt
pre-commit install  # Set up git hooks
```

**3. Start Development Services**
```bash
# Start all services with Docker Compose
docker-compose -f deployment/docker/docker-compose.yml up -d

# Verify services are running
make health-check
```

**4. Initialize Ollama**
```bash
# Pull required models
ollama pull codellama:7b
ollama pull mistral:7b

# Verify models are available
ollama list
```

**5. Initialize Database**
```bash
# Run database migrations
python scripts/migrate.py

# Load sample data (optional)
python scripts/load_sample_data.py
```

**6. Start Development Server**
```bash
# Start MCP server
python -m src.mcp_server.server

# Alternative: Start with auto-reload
uvicorn src.mcp_server.server:app --reload --host 0.0.0.0 --port 8000
```

### Development Tools Configuration

**VS Code Configuration (.vscode/settings.json)**
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

**Pre-commit Configuration (.pre-commit-config.yaml)**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.10.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Environment Configuration

**Development Environment (.env.development)**
```bash
# Database Configuration
DATABASE_URL=postgresql://context:password@localhost:5432/context_dev
REDIS_URL=redis://localhost:6379/0

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=context_dev

# AI Processing
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=codellama:7b

# MCP Server
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
MCP_LOG_LEVEL=DEBUG

# File System
INDEXED_PATHS=./sample_codebase
IGNORE_PATTERNS=.git,.venv,__pycache__,node_modules

# Cache Configuration
CACHE_TTL_SEARCH=1800
CACHE_TTL_EMBEDDINGS=3600
```

**Testing Environment (.env.testing)**
```bash
# Use test databases
DATABASE_URL=postgresql://context:password@localhost:5432/context_test
REDIS_URL=redis://localhost:6379/1
QDRANT_COLLECTION=context_test

# Disable external services for testing
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=mock

# Enable test-specific features
MOCK_EXTERNAL_SERVICES=true
ENABLE_TEST_FIXTURES=true
```

---

## Implementation Guide

### Phase 1: Core Infrastructure (Weeks 1-4)

**Sprint 1.1: Project Setup and Docker Environment**
```bash
# Create project structure
mkdir -p src/{mcp_server,code_intelligence,vector_database,ai_processing}
mkdir -p tests/{unit,integration,performance}
mkdir -p deployment/{docker,kubernetes,helm}

# Set up Docker Compose
cat > deployment/docker/docker-compose.yml << 'EOF'
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:v1.7.0
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: context
      POSTGRES_USER: context
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  qdrant_data:
  postgres_data:
  redis_data:
EOF
```

**Sprint 1.2: Basic MCP Server Implementation**
```python
# src/mcp_server/server.py
from fastmcp import FastMCP
from fastapi import FastAPI
import uvicorn

app = FastMCP(
    name="context",
    version="0.1.0",
    description="Context - 100% offline AI coding assistant"
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}

@app.tool
async def search_code(query: str) -> dict:
    """Basic search tool placeholder"""
    return {"query": query, "results": [], "status": "placeholder"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Sprint 1.3: Vector Database Integration**
```python
# src/vector_database/client.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

class VectorDB:
    def __init__(self):
        self.client = QdrantClient(host="localhost", port=6333)

    async def initialize_collection(self, name: str):
        self.client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )

    async def search(self, collection: str, query_vector: list[float]) -> list:
        results = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=10
        )
        return results
```

### Phase 2: Code Intelligence (Weeks 5-8)

**Sprint 2.1: Tree-sitter Integration**
```python
# src/code_intelligence/parser.py
from tree_sitter import Language, Parser

class CodeParser:
    def __init__(self):
        # Load language parsers
        self.python_lang = Language(tree_sitter_python.language())
        self.javascript_lang = Language(tree_sitter_javascript.language())

    def parse_python(self, code: str):
        parser = Parser()
        parser.set_language(self.python_lang)
        tree = parser.parse(bytes(code, 'utf-8'))
        return self.extract_functions(tree)

    def extract_functions(self, tree):
        functions = []
        query = self.python_lang.query(
            """(function_definition
               name: (identifier) @func_name
               parameters: (parameters) @params
               body: (block) @body)"""
        )
        captures = query.captures(tree.root_node)
        # Process captures to extract function information
        return functions
```

**Sprint 2.2: Embedding Generation**
```python
# src/vector_database/embeddings.py
from sentence_transformers import SentenceTransformer
import torch

class EmbeddingGenerator:
    def __init__(self):
        self.model = SentenceTransformer('microsoft/codebert-base')

    def generate_embedding(self, text: str) -> list[float]:
        with torch.no_grad():
            embedding = self.model.encode(text)
        return embedding.tolist()

    def process_code_file(self, file_path: str, content: str):
        # Split code into meaningful chunks
        chunks = self.chunk_code(content)
        embeddings = []

        for chunk in chunks:
            embedding = self.generate_embedding(chunk)
            embeddings.append({
                'text': chunk,
                'embedding': embedding,
                'file_path': file_path,
                'line_number': chunk['line_start']
            })

        return embeddings
```

### Phase 3: Search and AI Integration (Weeks 9-12)

**Sprint 3.1: Semantic Search Implementation**
```python
# src/mcp_server/tools/search.py
from fastmcp.tools import tool
from src.vector_database.client import VectorDB
from src.vector_database.embeddings import EmbeddingGenerator

@tool
async def semantic_search(query: str, limit: int = 10) -> dict:
    """Search codebase using semantic similarity"""

    # Generate query embedding
    embedder = EmbeddingGenerator()
    query_embedding = embedder.generate_embedding(query)

    # Search vector database
    vector_db = VectorDB()
    results = await vector_db.search("code_embeddings", query_embedding)

    # Format results
    formatted_results = []
    for result in results:
        formatted_results.append({
            'file_path': result.payload['file_path'],
            'line_number': result.payload['line_number'],
            'code_snippet': result.payload['text'],
            'similarity_score': result.score
        })

    return {
        'query': query,
        'results': formatted_results,
        'total_results': len(formatted_results)
    }
```

**Sprint 3.2: Ollama Integration**
```python
# src/ai_processing/client.py
import aiohttp
import json

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url

    async def generate_response(self, prompt: str, model="codellama:7b") -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            ) as response:
                result = await response.json()
                return result.get("response", "")

# src/ai_processing/context_enhancer.py
class ContextEnhancer:
    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client

    async def enhance_query(self, query: str, context: dict) -> str:
        enhanced_prompt = f"""
        Based on this context from the codebase:
        {json.dumps(context, indent=2)}

        Help me understand: {query}

        Provide a helpful response with specific code examples.
        """

        return await self.ollama.generate_response(enhanced_prompt)
```

### Phase 4: Advanced Features (Weeks 13-16)

**Sprint 4.1: File System Monitoring**
```python
# src/file_monitor/watcher.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio

class CodeWatcher(FileSystemEventHandler):
    def __init__(self, index_queue: asyncio.Queue):
        self.index_queue = index_queue

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            asyncio.create_task(
                self.index_queue.put({
                    'action': 'reindex',
                    'file_path': event.src_path
                })
            )

# File monitoring service
async def start_file_monitor(watch_path: str):
    index_queue = asyncio.Queue()
    event_handler = CodeWatcher(index_queue)
    observer = Observer()
    observer.schedule(event_handler, watch_path, recursive=True)
    observer.start()

    # Process indexing queue
    async for item in index_queue:
        await process_index_request(item)
```

**Sprint 4.2: Performance Optimization**
```python
# src/caching/performance_cache.py
import redis.asyncio as redis
from functools import wraps

class PerformanceCache:
    def __init__(self):
        self.redis = redis.from_url("redis://localhost:6379")

    def cache_result(self, ttl: int = 300):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

                # Try to get from cache
                cached = await self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)

                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.redis.setex(
                    cache_key,
                    ttl,
                    json.dumps(result, default=str)
                )

                return result
            return wrapper
        return decorator

# Usage in search service
@performance_cache.cache_result(ttl=600)
async def search_with_cache(query: str):
    return await semantic_search(query)
```

### Implementation Best Practices

**Error Handling Strategy**
```python
# src/utils/exceptions.py
class ContextException(Exception):
    """Base exception for Context application"""
    pass

class SearchError(ContextException):
    """Search-related errors"""
    pass

class IndexingError(ContextException):
    """Indexing-related errors"""
    pass

class AIServiceError(ContextException):
    """AI processing errors"""
    pass

# src/utils/error_handler.py
import structlog

logger = structlog.get_logger()

async def handle_search_error(error: Exception, query: str):
    logger.error("Search failed", error=str(error), query=query)

    if isinstance(error, AIServiceError):
        return {
            'error': 'AI service temporarily unavailable',
            'fallback_results': await fallback_keyword_search(query)
        }
    else:
        return {
            'error': 'Search temporarily unavailable',
            'retry_after': 30
        }
```

**Configuration Management**
```python
# src/config/settings.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database settings
    database_url: str = "postgresql://context:password@localhost:5432/context"
    redis_url: str = "redis://localhost:6379/0"

    # Vector database
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "context"

    # AI processing
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "codellama:7b"

    # Performance settings
    max_search_results: int = 50
    cache_ttl_seconds: int = 1800
    indexing_batch_size: int = 100

    # File system
    indexed_paths: List[str] = ["./*"]
    ignore_patterns: List[str] = [".git", ".venv", "__pycache__"]

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Testing Approach

### Test Strategy Overview

**Test Pyramid Structure**
- **Unit Tests (70%)**: Individual component testing
- **Integration Tests (20%)**: Component interaction testing
- **End-to-End Tests (10%)**: Full workflow testing

### Unit Testing

**Core Component Tests**
```python
# tests/unit/test_vector_database.py
import pytest
from src.vector_database.client import VectorDB
from qdrant_client.models import PointStruct
import uuid

@pytest.mark.asyncio
class TestVectorDB:
    async def setup_method(self):
        self.vector_db = VectorDB()
        self.test_collection = "test_collection"
        await self.vector_db.initialize_collection(self.test_collection)

    async def test_create_collection(self):
        # Test collection creation
        collection_info = self.vector_db.client.get_collection(self.test_collection)
        assert collection_info.name == self.test_collection

    async def test_upsert_vectors(self):
        # Test vector insertion
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=[0.1] * 768,
                payload={"file_path": "test.py", "content": "def test(): pass"}
            )
        ]

        await self.vector_db.upsert_vectors(self.test_collection, points)

        # Verify insertion
        results = self.vector_db.client.count(self.test_collection)
        assert results.count == 1

    async def test_search_vectors(self):
        # Insert test data
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=[0.1] * 768,
                payload={"file_path": "test.py", "content": "def hello(): pass"}
            )
        ]
        await self.vector_db.upsert_vectors(self.test_collection, points)

        # Search for similar vectors
        query_vector = [0.1] * 768
        results = await self.vector_db.search_similar(
            self.test_collection,
            query_vector
        )

        assert len(results) == 1
        assert results[0]['payload']['file_path'] == "test.py"
```

**Code Intelligence Tests**
```python
# tests/unit/test_code_parser.py
import pytest
from src.code_intelligence.parser import CodeParser

class TestCodeParser:
    def setup_method(self):
        self.parser = CodeParser()

    def test_parse_python_functions(self):
        code = """
def hello_world():
    print("Hello, World!")
    return True

def add_numbers(a, b):
    return a + b
"""

        result = self.parser.parse_python(code)
        functions = result['functions']

        assert len(functions) == 2
        assert functions[0]['name'] == 'hello_world'
        assert functions[1]['name'] == 'add_numbers'
        assert 'return True' in functions[0]['body']
        assert 'return a + b' in functions[1]['body']

    def test_extract_imports(self):
        code = """
import os
import sys
from pathlib import Path
from typing import List, Dict
"""

        result = self.parser.parse_python(code)
        imports = result['imports']

        assert len(imports) == 4
        assert any(imp['module'] == 'os' for imp in imports)
        assert any(imp['module'] == 'pathlib' and imp['name'] == 'Path' for imp in imports)

    def test_parse_javascript_functions(self):
        code = """
function greet(name) {
    console.log(`Hello, ${name}!`);
}

const add = (a, b) => a + b;
"""

        result = self.parser.parse_javascript(code)
        functions = result['functions']

        assert len(functions) == 2
        assert functions[0]['name'] == 'greet'
        assert functions[1]['name'] == 'add'
```

### Integration Testing

**MCP Server Integration Tests**
```python
# tests/integration/test_mcp_server.py
import pytest
from httpx import AsyncClient
from src.mcp_server.server import app

@pytest.mark.asyncio
class TestMCPServer:
    async def test_health_check(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    async def test_search_tool_integration(self):
        # Mock data setup
        await setup_test_data()

        async with AsyncClient(app=app, base_url="http://test") as client:
            search_request = {
                "tool": "semantic_search",
                "arguments": {
                    "query": "function that adds two numbers",
                    "limit": 5
                }
            }

            response = await client.post("/tools/call", json=search_request)
            assert response.status_code == 200

            result = response.json()
            assert "results" in result
            assert isinstance(result["results"], list)

async def setup_test_data():
    """Set up test data for integration tests"""
    # Insert test code files into vector database
    # Set up test database entries
    # Initialize test cache data
    pass
```

**Database Integration Tests**
```python
# tests/integration/test_database.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.data_storage.models import Base, CodeFile
from src.data_storage.repositories.metadata_repo import MetadataRepository

@pytest.mark.asyncio
class TestDatabaseIntegration:
    @pytest.fixture
    def db_session(self):
        engine = create_engine("sqlite:///test.db")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    async def test_create_code_file(self, db_session):
        repo = MetadataRepository(db_session)

        code_file = CodeFile(
            file_path="/test/example.py",
            file_hash="abc123",
            language="python",
            metadata={"functions": 3, "classes": 1}
        )

        created = await repo.create_file(code_file)
        assert created.id is not None
        assert created.file_path == "/test/example.py"

    async def test_search_by_language(self, db_session):
        repo = MetadataRepository(db_session)

        # Insert test data
        await repo.create_file(CodeFile(
            file_path="/test/python_file.py",
            file_hash="hash1",
            language="python"
        ))
        await repo.create_file(CodeFile(
            file_path="/test/javascript_file.js",
            file_hash="hash2",
            language="javascript"
        ))

        # Search for Python files
        python_files = await repo.search_by_language("python")
        assert len(python_files) == 1
        assert python_files[0].language == "python"
```

### Performance Testing

**Search Performance Tests**
```python
# tests/performance/test_search_performance.py
import pytest
import asyncio
import time
from src.vector_database.client import VectorDB
from src.vector_database.embeddings import EmbeddingGenerator

@pytest.mark.asyncio
class TestSearchPerformance:
    async def setup_method(self):
        self.vector_db = VectorDB()
        self.embedder = EmbeddingGenerator()
        await self.setup_large_dataset()

    async def setup_large_dataset(self):
        """Create large test dataset for performance testing"""
        # Insert 10,000 code snippets
        batch_size = 100
        for i in range(100):
            batch = []
            for j in range(batch_size):
                embedding = self.embedder.generate_embedding(f"test function {i*batch_size + j}")
                batch.append(PointStruct(
                    id=str(i*batch_size + j),
                    vector=embedding,
                    payload={
                        "file_path": f"test_file_{i}.py",
                        "content": f"def function_{i*batch_size + j}(): pass"
                    }
                ))
            await self.vector_db.upsert_vectors("performance_test", batch)

    async def test_search_latency_under_200ms(self):
        """Test that search completes in under 200ms"""
        query_embedding = self.embedder.generate_embedding("search for test functions")

        start_time = time.time()
        results = await self.vector_db.search_similar(
            "performance_test",
            query_embedding,
            limit=10
        )
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        assert latency_ms < 200, f"Search took {latency_ms}ms, expected < 200ms"
        assert len(results) <= 10

    async def test_concurrent_searches(self):
        """Test performance under concurrent load"""
        async def single_search():
            query_embedding = self.embedder.generate_embedding("concurrent test query")
            return await self.vector_db.search_similar(
                "performance_test",
                query_embedding,
                limit=5
            )

        # Run 50 concurrent searches
        start_time = time.time()
        tasks = [single_search() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time
        avg_time_per_search = total_time / 50

        assert avg_time_per_search < 0.5, f"Average search time: {avg_time_per_search}s"
        assert all(len(result) <= 5 for result in results)
```

### End-to-End Testing

**Full Workflow Tests**
```python
# tests/e2e/test_complete_workflow.py
import pytest
import tempfile
import os
from pathlib import Path
from src.file_monitor.watcher import CodeWatcher
from src.mcp_server.server import app

@pytest.mark.asyncio
class TestCompleteWorkflow:
    async def test_file_indexing_to_search_workflow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test code file
            test_file = Path(temp_dir) / "example.py"
            test_file.write_text("""
def calculate_sum(a, b):
    return a + b

def calculate_product(a, b):
    return a * b
""")

            # Initialize components
            watcher = CodeWatcher(index_queue=asyncio.Queue())

            # Simulate file creation event
            await watcher.on_created(type('Event', (), {
                'is_directory': False,
                'src_path': str(test_file)
            })())

            # Process indexing queue
            index_item = await watcher.index_queue.get()
            assert index_item['action'] == 'create'
            assert index_item['file_path'] == str(test_file)

            # Wait for indexing to complete
            await asyncio.sleep(1)

            # Test search functionality
            async with AsyncClient(app=app, base_url="http://test") as client:
                search_response = await client.post("/tools/call", json={
                    "tool": "semantic_search",
                    "arguments": {
                        "query": "function that adds two numbers",
                        "limit": 5
                    }
                })

                assert search_response.status_code == 200
                results = search_response.json()["results"]
                assert len(results) > 0

                # Verify the correct function is found
                found_functions = [r for r in results if "calculate_sum" in r["code_snippet"]]
                assert len(found_functions) > 0
```

### Test Data and Fixtures

**Test Fixtures**
```python
# tests/fixtures/code_samples.py
PYTHON_SAMPLES = {
    "simple_function": """
def hello_world():
    print("Hello, World!")
    return True
""",
    "class_definition": """
class Calculator:
    def __init__(self):
        self.history = []

    def add(self, a, b):
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result
""",
    "error_handling": """
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
"""
}

JAVASCRIPT_SAMPLES = {
    "arrow_function": """
const multiply = (a, b) => a * b;
""",
    "async_function": """
async function fetch_data(url) {
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error('Fetch failed:', error);
        return null;
    }
"""
}
```

### Test Configuration

**Pytest Configuration (pytest.ini)**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    e2e: End-to-end tests
    slow: Slow running tests
```

### Continuous Integration Testing

**GitHub Actions Workflow (.github/workflows/test.yml)**
```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: password
          POSTGRES_USER: context
          POSTGRES_DB: context_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7.2-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      qdrant:
        image: qdrant/qdrant:v1.7.0
        options: >-
          --health-cmd "curl -f http://localhost:6333/health || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/dev.txt

    - name: Run linting
      run: |
        ruff check src/
        black --check src/
        mypy src/

    - name: Run unit tests
      run: |
        pytest tests/unit/ -v

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v
      env:
        DATABASE_URL: postgresql://context:password@localhost:5432/context_test
        REDIS_URL: redis://localhost:6379/0
        QDRANT_HOST: localhost
        QDRANT_PORT: 6333

    - name: Run performance tests
      run: |
        pytest tests/performance/ -v -m "not slow"

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
```

---

## Deployment Strategy

### Development Deployment

**Local Development Environment**
```yaml
# deployment/docker/docker-compose.dev.yml
version: '3.8'
services:
  context-server:
    build:
      context: ../../
      dockerfile: deployment/docker/Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
      - ./docs:/app/docs
    environment:
      - PYTHONPATH=/app
      - DATABASE_URL=postgresql://context:password@postgres:5432/context_dev
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    depends_on:
      - postgres
      - redis
      - qdrant
    command: uvicorn src.mcp_server.server:app --reload --host 0.0.0.0 --port 8000

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: context_dev
      POSTGRES_USER: context
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
      - ./scripts/init_dev_db.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_dev_data:/data

  qdrant:
    image: qdrant/qdrant:v1.7.0
    ports:
      - "6333:6333"
    volumes:
      - qdrant_dev_data:/qdrant/storage

volumes:
  postgres_dev_data:
  redis_dev_data:
  qdrant_dev_data:
```

**Development Dockerfile**
```dockerfile
# deployment/docker/Dockerfile.dev
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/dev.txt .
RUN pip install --no-cache-dir -r dev.txt

# Copy source code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "src.mcp_server.server:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Deployment

**Kubernetes Deployment**
```yaml
# deployment/kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: context
  labels:
    name: context
---
# deployment/kubernetes/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: context-config
  namespace: context
data:
  DATABASE_URL: "postgresql://context:password@postgres:5432/context"
  REDIS_URL: "redis://redis:6379/0"
  QDRANT_HOST: "qdrant"
  QDRANT_PORT: "6333"
  OLLAMA_BASE_URL: "http://ollama:11434"
  LOG_LEVEL: "INFO"
  MAX_SEARCH_RESULTS: "50"
  CACHE_TTL_SECONDS: "1800"
---
# deployment/kubernetes/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: context-secrets
  namespace: context
type: Opaque
data:
  database-password: <base64-encoded-password>
  jwt-secret: <base64-encoded-jwt-secret>
---
# deployment/kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: context-server
  namespace: context
  labels:
    app: context-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: context-server
  template:
    metadata:
      labels:
        app: context-server
    spec:
      containers:
      - name: context-server
        image: context:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: context-config
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: context-config
              key: REDIS_URL
        - name: QDRANT_HOST
          valueFrom:
            configMapKeyRef:
              name: context-config
              key: QDRANT_HOST
        - name: QDRANT_PORT
          valueFrom:
            configMapKeyRef:
              name: context-config
              key: QDRANT_PORT
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: context-secrets
              key: database-password
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
# deployment/kubernetes/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: context-server
  namespace: context
spec:
  selector:
    app: context-server
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
---
# deployment/kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: context-ingress
  namespace: context
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - context.example.com
    secretName: context-tls
  rules:
  - host: context.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: context-server
            port:
              number: 80
```

**Production Dockerfile**
```dockerfile
# deployment/docker/Dockerfile.prod
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/prod.txt .
RUN pip install --no-cache-dir -r prod.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY pyproject.toml .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run with gunicorn for production
CMD ["gunicorn", "src.mcp_server.server:app", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker"]
```

### Database Migration Strategy

**Migration Scripts**
```python
# scripts/migrate.py
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from alembic.config import Config
from alembic import command
from src.config.settings import settings

async def run_migrations():
    """Run database migrations"""
    alembic_cfg = Config("alembic.ini")

    # Update database URL from settings
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    try:
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_migrations())
```

**Database Backup Strategy**
```bash
#!/bin/bash
# scripts/backup_database.sh

set -e

# Configuration
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="context"
DB_USER="context"
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/context_backup_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create database backup
echo "Creating database backup..."
PGPASSWORD="$DATABASE_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    --verbose \
    > "$BACKUP_FILE"

# Compress backup
echo "Compressing backup..."
gzip "$BACKUP_FILE"

# Remove old backups (keep last 7 days)
find "$BACKUP_DIR" -name "context_backup_*.sql.gz" -mtime +7 -delete

echo "✅ Backup completed: ${BACKUP_FILE}.gz"
```

### Monitoring and Observability

**Prometheus Metrics Configuration**
```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
import functools

# Define metrics
search_requests_total = Counter(
    'context_search_requests_total',
    'Total number of search requests',
    ['method', 'endpoint']
)

search_request_duration = Histogram(
    'context_search_request_duration_seconds',
    'Search request duration in seconds',
    ['method', 'endpoint']
)

active_searches = Gauge(
    'context_active_searches',
    'Number of currently active searches'
)

indexing_operations_total = Counter(
    'context_indexing_operations_total',
    'Total number of indexing operations',
    ['operation_type']
)

cache_hit_ratio = Gauge(
    'context_cache_hit_ratio',
    'Cache hit ratio',
    ['cache_type']
)

# Metrics decorator
def track_search_performance(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        active_searches.inc()
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            search_requests_total.labels(method='semantic', endpoint='search').inc()
            return result
        finally:
            duration = time.time() - start_time
            search_request_duration.labels(method='semantic', endpoint='search').observe(duration)
            active_searches.dec()

    return wrapper

# Metrics endpoint
from fastapi import Response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Grafana Dashboard Configuration**
```json
{
  "dashboard": {
    "title": "Context Monitoring",
    "panels": [
      {
        "title": "Search Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(context_search_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Search Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(context_search_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(context_search_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Active Searches",
        "type": "singlestat",
        "targets": [
          {
            "expr": "context_active_searches",
            "legendFormat": "Active Searches"
          }
        ]
      },
      {
        "title": "Cache Hit Ratio",
        "type": "graph",
        "targets": [
          {
            "expr": "context_cache_hit_ratio",
            "legendFormat": "{{cache_type}}"
          }
        ]
      }
    ]
  }
}
```

### Security Configuration

**Security Hardening**
```yaml
# deployment/kubernetes/security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: context-psp
  namespace: context
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
---
# Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: context-netpol
  namespace: context
spec:
  podSelector:
    matchLabels:
      app: context-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app: qdrant
    ports:
    - protocol: TCP
      port: 6333
```

### Deployment Automation

**CI/CD Pipeline**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run tests
      run: |
        docker-compose -f docker-compose.test.yml up --abort-on-container-exit
        docker-compose -f docker-compose.test.yml down

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./deployment/docker/Dockerfile.prod
        push: true
        tags: |
          ghcr.io/${{ github.repository }}:latest
          ghcr.io/${{ github.repository }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    environment: production
    steps:
    - uses: actions/checkout@v4

    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.28.0'

    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig

    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/context-server context-server=ghcr.io/${{ github.repository }}:${{ github.sha }} -n context
        kubectl rollout status deployment/context-server -n context
        kubectl get pods -n context
```

### Scaling Strategy

**Horizontal Pod Autoscaler**
```yaml
# deployment/kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: context-server-hpa
  namespace: context
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: context-server
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

---

_**Technical Specification Complete! Implementation Roadmap Ready**_

_**Status:** Ready for Sprint Planning and Story Development_