# Technical Architecture Document
## Context Workspace v2.5 - Augmented Intelligence Platform

**Version:** 1.0
**Date:** 2025-11-11
**Status:** Design Phase
**Related:** WORKSPACE_V2.5_PRD.md

---

## 1. Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ CLI          │  │ REST API     │  │ WebSocket    │  │ Dashboard UI │   │
│  │ (Click)      │  │ (FastAPI)    │  │ (Socket.IO)  │  │ (React)      │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
└─────────┼──────────────────┼──────────────────┼──────────────────┼───────────┘
          │                  │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────────▼───────────┐
│                       AI INTELLIGENCE LAYER                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ Auto-Discovery   │  │ Query Parser     │  │ Context Ranker           │  │
│  │ Engine           │  │ (NLP + Semantic) │  │ (ML-based Boosting)      │  │
│  │                  │  │                  │  │                          │  │
│  │ - Project Scanner│  │ - Entity Extract │  │ - Current File Boost     │  │
│  │ - Type Classifier│  │ - Query Expansion│  │ - Recent Files Boost     │  │
│  │ - Dep Analyzer   │  │ - Intent Detection│  │ - Team Pattern Boost     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────────┐
│                       WORKSPACE ORCHESTRATION LAYER                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ Workspace Manager│  │ Search Engine    │  │ Analytics Collector      │  │
│  │ (v2.5 Enhanced)  │  │ (Multi-Modal)    │  │ (Real-Time Metrics)      │  │
│  │                  │  │                  │  │                          │  │
│  │ - Project Mgmt   │  │ - Semantic       │  │ - Performance Metrics    │  │
│  │ - Relationship   │  │ - Keyword (BM25) │  │ - Usage Metrics          │  │
│  │ - Lifecycle      │  │ - AST Search     │  │ - Code Health Metrics    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────────┐
│                          CACHING & OPTIMIZATION LAYER                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ Redis Cache      │  │ Query Cache      │  │ Predictive Pre-fetcher   │  │
│  │ (Search Results) │  │ (LRU + TTL)      │  │ (Usage Pattern Analysis) │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────────┐
│                          STORAGE & PERSISTENCE LAYER                          │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐ ┌──────────────┐  │
│  │ Qdrant       │  │ PostgreSQL    │  │ TimescaleDB    │ │ Redis        │  │
│  │ (Vectors)    │  │ (Metadata)    │  │ (Time-Series)  │ │ (Cache/Pub)  │  │
│  └──────────────┘  └───────────────┘  └────────────────┘ └──────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Layer | Components | Responsibilities |
|-------|-----------|------------------|
| **Client** | CLI, REST API, WebSocket, Dashboard | User interaction, API gateway |
| **AI Intelligence** | Auto-Discovery, Query Parser, Context Ranker | Smart automation, NLP, ML |
| **Orchestration** | Workspace Manager, Search Engine, Analytics | Business logic, coordination |
| **Caching** | Redis, Query Cache, Pre-fetcher | Performance optimization |
| **Storage** | Qdrant, PostgreSQL, TimescaleDB, Redis | Data persistence |

---

## 2. Component Deep Dive

### 2.1 Auto-Discovery Engine

**Purpose:** Automatically detect and configure projects with zero manual setup

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Auto-Discovery Engine                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Project Scanner                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ File Walker│─>│ Marker     │─>│ Project        │  │  │
│  │  │ (os.walk)  │  │ Detector   │  │ Aggregator     │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Type Classifier                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Heuristic  │  │ Framework  │  │ Confidence     │  │  │
│  │  │ Rules      │─>│ Detector   │─>│ Scorer         │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │            Dependency Analyzer                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Package    │  │ Import     │  │ Graph          │  │  │
│  │  │ Parser     │─>│ Analyzer   │─>│ Builder        │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### Data Flow

```python
# Input
discovery_request = {
    "path": "/home/user/projects",
    "max_depth": 10,
    "ignore_patterns": ["node_modules", "venv"]
}

# Step 1: Scan
projects = project_scanner.scan(discovery_request.path)
# Output: [
#   {"path": "/home/user/projects/frontend", "markers": ["package.json"]},
#   {"path": "/home/user/projects/backend", "markers": ["setup.py"]},
# ]

# Step 2: Classify
typed_projects = type_classifier.classify(projects)
# Output: [
#   {"path": "...", "type": "web_frontend", "confidence": 0.95, "framework": "next.js"},
#   {"path": "...", "type": "api_server", "confidence": 0.88, "framework": "fastapi"},
# ]

# Step 3: Analyze Dependencies
analyzed_projects = dependency_analyzer.analyze(typed_projects)
# Output: [
#   {"path": "...", "type": "...", "dependencies": ["backend", "shared"], ...},
#   {"path": "...", "type": "...", "dependencies": ["shared"], ...},
# ]

# Step 4: Generate Config
workspace_config = config_generator.generate(analyzed_projects)
# Output: WorkspaceConfig object ready to save
```

#### Implementation Classes

```python
# src/workspace/auto_discovery/scanner.py
class ProjectScanner:
    """Scans directory tree and detects projects"""

    MARKERS = {
        "package.json": "nodejs",
        "setup.py": "python",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "pom.xml": "java",
    }

    def scan(self, root_path: str, max_depth: int = 10) -> List[DiscoveredProject]:
        """Scan directory tree for projects"""

    def _is_project_root(self, path: str) -> bool:
        """Check if path contains project markers"""

    def _detect_language(self, markers: List[str]) -> List[str]:
        """Detect programming languages from markers"""


# src/workspace/auto_discovery/classifier.py
class TypeClassifier:
    """Classifies project types using heuristics"""

    FRAMEWORK_PATTERNS = {
        "next.js": ["next.config.js", "pages/", "app/"],
        "fastapi": ["from fastapi", "FastAPI()"],
        "django": ["manage.py", "settings.py"],
    }

    def classify(self, projects: List[Dict]) -> List[TypedProject]:
        """Classify project types"""

    def _detect_framework(self, path: str, language: str) -> Optional[str]:
        """Detect framework by scanning key files"""

    def _compute_confidence(self, signals: List[Signal]) -> float:
        """Compute confidence score from multiple signals"""


# src/workspace/auto_discovery/dependency_analyzer.py
class DependencyAnalyzer:
    """Analyzes dependencies between projects"""

    def analyze(self, projects: List[TypedProject]) -> List[AnalyzedProject]:
        """Analyze dependencies and build graph"""

    def _parse_package_file(self, project: TypedProject) -> List[str]:
        """Parse package.json, requirements.txt, etc."""

    def _analyze_imports(self, project: TypedProject) -> List[ImportRelationship]:
        """Analyze import statements using AST"""

    def _detect_api_calls(self, project: TypedProject) -> List[APIRelationship]:
        """Detect HTTP client usage patterns"""
```

#### Performance Optimization

- **Parallel Scanning**: Use ThreadPoolExecutor for concurrent directory scanning
- **Early Termination**: Stop scanning when max_depth reached
- **Ignore Patterns**: Skip node_modules, venv, .git immediately
- **Memoization**: Cache framework detection results

---

### 2.2 Intelligent Search Engine

**Purpose:** Understand natural language queries and rank results by context

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Intelligent Search Engine                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Query Parser (NLP)                       │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Tokenizer  │─>│ Entity     │─>│ Query          │  │  │
│  │  │ (spaCy)    │  │ Extractor  │  │ Expander       │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Context Collector                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Current    │  │ Recent     │  │ Team           │  │  │
│  │  │ File       │─>│ Files      │─>│ Patterns       │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │            Multi-Modal Search                         │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Semantic   │  │ Keyword    │  │ AST            │  │  │
│  │  │ (Vector)   │  │ (BM25)     │  │ (Structure)    │  │  │
│  │  └─────┬──────┘  └─────┬──────┘  └────────┬───────┘  │  │
│  │        └─────────────────┴──────────────────┘          │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Context Ranker                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Boost      │  │ Score      │  │ Result         │  │  │
│  │  │ Calculator │─>│ Merger     │─>│ Ranker         │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### Ranking Formula

```
final_score = (
    base_score * 1.0 +                          # Semantic/keyword match
    current_file_boost * 2.0 +                  # Current project/file
    recent_files_boost * 1.5 +                  # Recently accessed
    frequent_files_boost * 1.3 +                # User's frequent files
    team_patterns_boost * 1.2 +                 # Team usage patterns
    relationship_boost * 1.5 +                  # Project dependencies
    recency_boost * 0.5 +                       # Recently modified
    exact_match_boost * 0.8                     # Keyword exact match
)
```

#### Implementation Classes

```python
# src/search/intelligent/query_parser.py
class QueryParser:
    """Parses natural language queries"""

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.expander = QueryExpander()

    def parse(self, query: str) -> ParsedQuery:
        """Parse query into structured format"""
        doc = self.nlp(query)

        entities = self._extract_entities(doc)
        intent = self._detect_intent(doc)
        expanded = self.expander.expand(query, entities)

        return ParsedQuery(
            original=query,
            entities=entities,
            intent=intent,
            expanded_terms=expanded
        )

    def _extract_entities(self, doc) -> List[Entity]:
        """Extract entities (file names, functions, concepts)"""

    def _detect_intent(self, doc) -> Intent:
        """Detect intent (find, list, show, etc.)"""


# src/search/intelligent/context_collector.py
class ContextCollector:
    """Collects search context from user behavior"""

    def collect(self, user_id: str) -> SearchContext:
        """Collect all context for ranking boost"""

        current_file = self._get_current_file(user_id)
        recent_files = self._get_recent_files(user_id, hours=1)
        frequent_files = self._get_frequent_files(user_id, limit=20)
        team_patterns = self._get_team_patterns(user_id)

        return SearchContext(
            current_file=current_file,
            recent_files=recent_files,
            frequent_files=frequent_files,
            team_patterns=team_patterns
        )

    def _get_current_file(self, user_id: str) -> Optional[str]:
        """Get currently open file from IDE/editor"""

    def _get_team_patterns(self, user_id: str) -> Dict[str, float]:
        """Get team's file access patterns from analytics"""


# src/search/intelligent/context_ranker.py
class ContextRanker:
    """Re-ranks results based on context"""

    def rank(self, results: List[SearchResult], context: SearchContext) -> List[SearchResult]:
        """Apply context-based boosting"""

        for result in results:
            boosts = self._calculate_boosts(result, context)
            result.final_score = result.base_score + sum(boosts.values())
            result.boost_breakdown = boosts

        return sorted(results, key=lambda r: r.final_score, reverse=True)

    def _calculate_boosts(self, result: SearchResult, context: SearchContext) -> Dict[str, float]:
        """Calculate all boost factors"""
        return {
            "current_file": self._current_file_boost(result, context),
            "recent_files": self._recent_files_boost(result, context),
            "frequent_files": self._frequent_files_boost(result, context),
            "team_patterns": self._team_patterns_boost(result, context),
        }
```

---

### 2.3 Smart Caching System

**Purpose:** Achieve sub-100ms search latency through aggressive caching

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Smart Caching System                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Query Result Cache (Redis)               │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ LRU        │  │ TTL        │  │ Invalidation   │  │  │
│  │  │ Eviction   │  │ Expiration │  │ (File Changes) │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Embedding Cache                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Pre-compute│  │ Warm       │  │ Background     │  │  │
│  │  │ (Common)   │  │ Cache      │  │ Refresh        │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Predictive Pre-fetcher                      │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Pattern    │  │ Next Query │  │ Warm           │  │  │
│  │  │ Analyzer   │─>│ Predictor  │─>│ Related Data   │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### Cache Layers

| Layer | Technology | TTL | Size Limit | Purpose |
|-------|-----------|-----|------------|---------|
| **L1: In-Memory** | Python dict | 5 min | 100 MB | Hot queries |
| **L2: Redis** | Redis 7.x | 1 hour | 1 GB | Warm queries |
| **L3: Pre-computed** | Redis | 24 hours | 5 GB | Common queries |

#### Implementation

```python
# src/caching/query_cache.py
class QueryCache:
    """Multi-layer query result cache"""

    def __init__(self):
        self.l1_cache = {}  # In-memory LRU
        self.l2_cache = Redis()  # Redis
        self.stats = CacheStats()

    async def get(self, query_key: str) -> Optional[List[SearchResult]]:
        """Get cached results (L1 → L2 → Miss)"""

        # L1: In-memory
        if query_key in self.l1_cache:
            self.stats.record_hit("l1")
            return self.l1_cache[query_key]

        # L2: Redis
        cached = await self.l2_cache.get(query_key)
        if cached:
            self.stats.record_hit("l2")
            self.l1_cache[query_key] = cached  # Promote to L1
            return cached

        self.stats.record_miss()
        return None

    async def set(self, query_key: str, results: List[SearchResult], ttl: int = 3600):
        """Set cache (L1 + L2)"""
        self.l1_cache[query_key] = results
        await self.l2_cache.setex(query_key, ttl, results)

    async def invalidate(self, file_path: str):
        """Invalidate cache when file changes"""
        # Find all queries that touched this file
        affected_queries = self._find_affected_queries(file_path)
        for query_key in affected_queries:
            self.l1_cache.pop(query_key, None)
            await self.l2_cache.delete(query_key)


# src/caching/predictive_prefetcher.py
class PredictivePrefetcher:
    """Predicts and pre-fetches likely next queries"""

    def __init__(self):
        self.pattern_analyzer = PatternAnalyzer()
        self.predictor = NextQueryPredictor()

    async def prefetch(self, current_query: str, user_context: SearchContext):
        """Predict and warm cache for likely next queries"""

        # Analyze patterns
        patterns = self.pattern_analyzer.analyze(user_context.recent_queries)

        # Predict next queries
        next_queries = self.predictor.predict(current_query, patterns, top_k=5)

        # Pre-fetch in background
        for query in next_queries:
            asyncio.create_task(self._warm_cache(query, user_context))

    async def _warm_cache(self, query: str, context: SearchContext):
        """Execute query and cache results"""
        # Execute search
        # Store in cache
        # Don't return (background task)
```

---

### 2.4 Real-Time Analytics System

**Purpose:** Provide real-time visibility into performance and usage

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Real-Time Analytics System                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Metrics Collector (Prometheus)             │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Search     │  │ Index      │  │ System         │  │  │
│  │  │ Metrics    │  │ Metrics    │  │ Metrics        │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │          Time-Series Storage (TimescaleDB)            │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Hypertables│  │ Continuous │  │ Retention      │  │  │
│  │  │ (Auto Part)│  │ Aggregates │  │ Policies       │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │          Dashboard & Visualization (Grafana)          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ Real-Time  │  │ Alerts     │  │ Custom         │  │  │
│  │  │ Panels     │  │ & Notifs   │  │ Dashboards     │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### Metrics Collected

| Category | Metrics | Update Frequency |
|----------|---------|------------------|
| **Search Performance** | Latency (p50, p95, p99), Throughput (qps), Cache hit rate | Real-time |
| **Index Performance** | Files/sec, Queue size, Error rate | Every 5s |
| **Usage** | Active users, Searches/user, Top queries | Every 1min |
| **Code Health** | Dead code %, Hot spots, Coverage % | Hourly |
| **System** | CPU, Memory, Disk I/O, Network | Every 10s |

#### Implementation

```python
# src/analytics/collector.py
class MetricsCollector:
    """Collects and exports metrics to Prometheus"""

    def __init__(self):
        # Prometheus metrics
        self.search_latency = Histogram(
            "search_latency_seconds",
            "Search query latency",
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )
        self.search_requests = Counter("search_requests_total", "Total search requests")
        self.cache_hits = Counter("cache_hits_total", "Cache hits", ["layer"])

    def record_search(self, latency: float, cache_hit: bool, layer: Optional[str] = None):
        """Record search metrics"""
        self.search_latency.observe(latency)
        self.search_requests.inc()
        if cache_hit:
            self.cache_hits.labels(layer=layer).inc()

    def record_index(self, files_indexed: int, errors: int, duration: float):
        """Record indexing metrics"""
        # Similar pattern


# src/analytics/dashboard.py
class DashboardAPI:
    """API for dashboard data"""

    async def get_search_performance(self, timerange: str = "1h") -> Dict:
        """Get search performance metrics"""
        query = f"""
        SELECT
            percentile_cont(0.5) WITHIN GROUP (ORDER BY latency) as p50,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY latency) as p95,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY latency) as p99
        FROM search_metrics
        WHERE timestamp > NOW() - INTERVAL '{timerange}'
        """
        return await self.db.execute(query)

    async def get_usage_metrics(self, timerange: str = "24h") -> Dict:
        """Get usage metrics"""
        # Most searched files
        # Top queries
        # Active users
```

---

## 3. Data Models

### Enhanced Models

```python
# src/workspace/auto_discovery/models.py
@dataclass
class DiscoveredProject:
    """Auto-discovered project"""
    path: str
    type: ProjectType
    confidence: float  # 0.0 - 1.0
    detected_languages: List[str]
    detected_dependencies: List[str]  # Project names or package names
    suggested_excludes: List[str]
    framework: Optional[str]
    framework_version: Optional[str]
    metadata: Dict[str, Any]
    discovery_timestamp: datetime


# src/search/intelligent/models.py
@dataclass
class ParsedQuery:
    """Parsed natural language query"""
    original: str
    entities: List[Entity]  # File names, functions, concepts
    intent: Intent  # find, list, show, search
    expanded_terms: List[str]  # Synonyms, related concepts
    confidence: float


@dataclass
class SearchContext:
    """User context for ranking"""
    user_id: str
    current_file: Optional[str]
    current_project: Optional[str]
    recent_files: List[str]  # Last hour
    frequent_files: List[str]  # Top 20
    recent_queries: List[str]  # Last 10
    team_patterns: Dict[str, float]  # File → access frequency


@dataclass
class EnhancedSearchResult(SearchResult):
    """Search result with boost breakdown"""
    base_score: float  # Original similarity score
    final_score: float  # After boosting
    boost_breakdown: Dict[str, float]  # Which boosts applied
    context_relevance: float  # How relevant to current context
    query_understanding: ParsedQuery  # How query was interpreted


# src/analytics/models.py
@dataclass
class Metric:
    """Time-series metric"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str]  # project_id, user_id, etc.
    aggregation: Optional[str]  # sum, avg, p95, etc.
```

---

## 4. API Specifications

### REST API

```yaml
openapi: 3.0.0
info:
  title: Context Workspace v2.5 API
  version: 2.5.0

paths:
  /api/v1/workspace/discover:
    post:
      summary: Auto-discover projects
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                path:
                  type: string
                max_depth:
                  type: integer
                  default: 10
                ignore_patterns:
                  type: array
                  items:
                    type: string
      responses:
        '200':
          description: Discovered projects
          content:
            application/json:
              schema:
                type: object
                properties:
                  discovered_projects:
                    type: array
                    items:
                      $ref: '#/components/schemas/DiscoveredProject'
                  suggested_workspace:
                    $ref: '#/components/schemas/WorkspaceConfig'
                  confidence_score:
                    type: number

  /api/v1/search/intelligent:
    post:
      summary: Intelligent search with NLP
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                query:
                  type: string
                context:
                  $ref: '#/components/schemas/SearchContext'
                options:
                  type: object
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema:
                type: object
                properties:
                  results:
                    type: array
                    items:
                      $ref: '#/components/schemas/EnhancedSearchResult'
                  query_understanding:
                    $ref: '#/components/schemas/ParsedQuery'
                  ranking_factors:
                    type: object

  /api/v1/analytics/metrics:
    get:
      summary: Get time-series metrics
      parameters:
        - name: metric
          in: query
          schema:
            type: string
        - name: timerange
          in: query
          schema:
            type: string
        - name: aggregation
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Metric data
          content:
            application/json:
              schema:
                type: object
                properties:
                  metric:
                    type: string
                  datapoints:
                    type: array
                    items:
                      type: object
                  summary:
                    type: object
```

---

## 5. Deployment Architecture

### Docker Compose

```yaml
version: '3.8'

services:
  context-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
      - TIMESCALE_URL=postgresql://timescale:5432/context
    depends_on:
      - redis
      - qdrant
      - timescale
      - prometheus

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru

  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"

  timescale:
    image: timescale/timescaledb:latest-pg14
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: context
      POSTGRES_USER: context
      POSTGRES_PASSWORD: password

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
```

---

## 6. Performance Optimization Strategies

### 1. Caching Strategy
- **L1 In-Memory:** 100 MB, 5 min TTL, hot queries
- **L2 Redis:** 1 GB, 1 hour TTL, warm queries
- **L3 Pre-computed:** 5 GB, 24 hour TTL, common queries

### 2. Indexing Optimization
- **Incremental:** Only index changed files
- **Batching:** Group updates (every 5s)
- **Prioritization:** Critical files first
- **Parallel:** Use all CPU cores

### 3. Search Optimization
- **Early Termination:** Stop when enough high-scoring results
- **Result Streaming:** Don't wait for all results
- **Approximate Search:** Use HNSW for speed
- **Query Optimization:** Rewrite complex queries

### 4. Database Optimization
- **TimescaleDB:** Continuous aggregates, auto-compression
- **Qdrant:** HNSW indexing, quantization
- **PostgreSQL:** Proper indexes, query optimization
- **Redis:** Pipelining, connection pooling

---

## 7. Security Considerations

- **Input Validation:** Sanitize all user inputs (paths, queries)
- **Path Traversal:** Prevent `../` attacks in file paths
- **Rate Limiting:** Limit API requests (100 req/min per user)
- **Authentication:** API keys for external access
- **Authorization:** Project-level permissions (future)
- **Audit Logging:** Track all operations

---

## 8. Monitoring & Observability

### Metrics
- **Search:** Latency, throughput, cache hit rate
- **Index:** Files/sec, queue size, error rate
- **System:** CPU, memory, disk, network

### Logs
- **Structured:** JSON format
- **Levels:** DEBUG, INFO, WARN, ERROR
- **Context:** User ID, project ID, operation

### Alerts
- **Latency:** p95 > 500ms
- **Errors:** Error rate > 5%
- **Queue:** Queue size > 10000

---

## 9. Testing Strategy

### Unit Tests
- Each component tested in isolation
- Mock external dependencies
- Coverage > 90%

### Integration Tests
- Test component interactions
- Use test databases
- End-to-end flows

### Performance Tests
- Load testing (1000+ qps)
- Stress testing (10x normal load)
- Endurance testing (24 hours)

### Acceptance Tests
- User stories validated
- Real-world scenarios
- Cross-browser/platform

---

## 10. Migration Plan (v2.0 → v2.5)

### Phase 1: Foundation (Week 1)
- Install new dependencies (spaCy, TimescaleDB)
- Update database schemas
- Deploy new Docker services

### Phase 2: Feature Rollout (Week 2-3)
- Deploy auto-discovery (beta)
- Deploy intelligent search (beta)
- Deploy analytics dashboard

### Phase 3: Optimization (Week 3-4)
- Enable caching
- Tune performance
- Monitor and adjust

### Phase 4: GA (Week 4)
- Remove beta flags
- Full documentation
- Announce release

---

**End of Architecture Document**
