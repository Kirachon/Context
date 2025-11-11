# Memory System

**Context Workspace v3.0 - Persistent Learning Through Memory**

The Memory System provides persistent storage and learning from user interactions, code patterns, solutions, and preferences. It enables Context to learn from past experiences and provide increasingly intelligent assistance over time.

## Architecture

The Memory System consists of four integrated subsystems:

### 1. **Conversation Memory** (Epic 5)
Store and retrieve conversation history with semantic search capabilities.

- **Storage**: PostgreSQL + Qdrant vector indexing
- **Features**:
  - Full conversation storage (prompt, enhanced context, response)
  - Semantic similarity search using sentence embeddings
  - Feedback tracking and resolution metrics
  - User-specific conversation history
  - Analytics and statistics

### 2. **Pattern Memory** (Epic 6)
Extract and store code patterns from codebase analysis.

- **Storage**: PostgreSQL
- **Features**:
  - Automatic pattern extraction from Python code
  - Pattern categorization (API design, error handling, testing, etc.)
  - Usage tracking across files
  - Pattern prevalence scoring
  - Project-specific pattern libraries

### 3. **Solution Memory** (Epic 7)
Store problem-solution pairs with intelligent clustering.

- **Storage**: PostgreSQL with DBSCAN clustering
- **Features**:
  - Problem-solution pair storage
  - Semantic similarity search for solutions
  - Automatic clustering of similar problems
  - Success rate tracking
  - Resolution time metrics

### 4. **Preference Memory** (Epic 8)
Learn user coding preferences from git history and feedback.

- **Storage**: PostgreSQL
- **Features**:
  - Git history analysis for coding style
  - Naming convention detection
  - Library preference tracking
  - Testing approach identification
  - Project-specific overrides

## Quick Start

### Installation

```bash
# Install dependencies
pip install sqlalchemy alembic psycopg2-binary sentence-transformers scikit-learn

# Initialize database
python -c "from src.memory.database import init_database; init_database()"

# Or via CLI
context memory init
```

### Basic Usage

#### Python API

```python
from src.memory import (
    ConversationStore,
    PatternStore,
    SolutionStore,
    PreferenceStore
)

# Conversation Memory
conv_store = ConversationStore()
conv_id = conv_store.store_conversation(
    user_id="user@example.com",
    prompt="How to fix authentication?",
    enhanced_prompt="...",  # With context
    response="...",
    intent="fix",
)

# Search similar conversations
results = conv_store.get_similar_conversations(
    query="authentication issues",
    limit=5
)

# Pattern Memory
pattern_store = PatternStore()
pattern_id = pattern_store.store_pattern(
    pattern_type="error_handling",
    name="retry_pattern",
    example_code="...",
)

# Extract patterns from directory
counts = pattern_store.extract_patterns_from_directory(
    directory="./src",
    project_id="my_project"
)

# Solution Memory
solution_store = SolutionStore()
solution_id = solution_store.store_solution(
    problem_description="Database connection fails",
    solution_code="...",
    success_rate=0.95,
)

# Find similar solutions
solutions = solution_store.get_similar_solutions(
    problem="connection timeout",
    limit=3
)

# Preference Memory
pref_store = PreferenceStore()
result = pref_store.learn_from_git_history(
    user_id="user@example.com",
    repo_path="/path/to/repo",
    max_commits=100,
)

prefs = pref_store.get_user_preferences("user@example.com")
```

#### CLI Usage

```bash
# Conversation Memory
context memory conversations search --query "authentication" --limit 5
context memory conversations stats --user-id user@example.com

# Pattern Memory
context memory patterns list --type error_handling
context memory patterns extract ./src --project my_project
context memory patterns stats

# Solution Memory
context memory solutions search --problem "connection timeout"
context memory solutions stats
context memory solutions recluster

# Preference Memory
context memory preferences show user@example.com
context memory preferences learn user@example.com /path/to/repo
```

## Database Schema

### Conversations Table

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    prompt TEXT NOT NULL,
    enhanced_prompt TEXT,
    response TEXT,
    intent VARCHAR(50),
    entities JSONB,
    feedback JSONB,
    resolution BOOLEAN,
    helpful_score FLOAT,
    token_count INTEGER,
    latency_ms INTEGER,
    context_sources JSONB
);
```

### Code Patterns Table

```sql
CREATE TABLE code_patterns (
    id UUID PRIMARY KEY,
    pattern_type VARCHAR(100) NOT NULL,
    name VARCHAR(255),
    description TEXT,
    example_code TEXT,
    signature VARCHAR(500),
    language VARCHAR(50),
    usage_count INTEGER DEFAULT 0,
    files_using JSONB,
    user_preference_score FLOAT DEFAULT 0.0,
    project_id VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Solutions Table

```sql
CREATE TABLE solutions (
    id UUID PRIMARY KEY,
    problem_description TEXT NOT NULL,
    problem_type VARCHAR(100),
    error_message TEXT,
    solution_code TEXT,
    solution_description TEXT,
    files_affected JSONB,
    success_rate FLOAT DEFAULT 0.0,
    usage_count INTEGER DEFAULT 0,
    avg_resolution_time_sec INTEGER,
    similar_problems JSONB,
    cluster_id VARCHAR(100),
    user_id VARCHAR(255),
    project_id VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### User Preferences Table

```sql
CREATE TABLE user_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    code_style JSONB,
    preferred_libraries JSONB,
    testing_approach VARCHAR(50),
    documentation_level VARCHAR(50),
    language_preferences JSONB,
    project_preferences JSONB,
    confidence_score FLOAT DEFAULT 0.0,
    sample_size INTEGER DEFAULT 0,
    updated_at TIMESTAMP
);
```

## Performance

### Benchmarks

- **Conversation storage**: < 50ms (p95)
- **Semantic search**: < 100ms (p95)
- **Pattern extraction**: ~1000 files/second
- **Solution clustering**: < 500ms for 100 solutions
- **Preference learning**: ~100 commits/second

### Optimization

The Memory System includes several optimizations:

- **Database indexing**: All frequently queried fields are indexed
- **Vector caching**: Qdrant provides fast vector similarity search
- **Batch processing**: Pattern extraction processes files in batches
- **Connection pooling**: Reuses database connections efficiently

## Integration with Context v3.0

The Memory System integrates with other Context components:

### 1. **Prompt Enhancement Engine** (Feature 1)
- Queries conversation memory for similar past interactions
- Retrieves relevant patterns for context
- Searches solutions for similar problems
- Applies user preferences to prompt composition

### 2. **Autonomous Agents** (Feature 3)
- Agents learn from past successful solutions
- Pattern memory guides code generation
- Preference memory ensures consistent style

### 3. **Analytics System** (v2.5)
- Memory statistics exported to Prometheus
- Grafana dashboards for memory metrics
- Performance monitoring and alerts

## Configuration

### Environment Variables

```bash
# Database connection
export DATABASE_URL="postgresql://user:password@localhost:5432/context"

# Qdrant connection
export QDRANT_HOST="localhost"
export QDRANT_PORT=6333

# Memory system settings
export MEMORY_RETENTION_DAYS=90
export MEMORY_CACHE_SIZE_MB=100
```

### Workspace Configuration

Add to `.context-workspace.json`:

```json
{
  "memory": {
    "enabled": true,
    "conversations": {
      "enabled": true,
      "retention_days": 90,
      "semantic_search": true
    },
    "patterns": {
      "enabled": true,
      "auto_extract": true,
      "min_usage_threshold": 2
    },
    "solutions": {
      "enabled": true,
      "clustering": true,
      "min_success_rate": 0.5
    },
    "preferences": {
      "enabled": true,
      "auto_learn": true,
      "git_analysis": true
    }
  }
}
```

## API Reference

See individual module documentation:
- [`conversation.py`](./conversation.py) - Conversation Memory API
- [`patterns.py`](./patterns.py) - Pattern Memory API
- [`solutions.py`](./solutions.py) - Solution Memory API
- [`preferences.py`](./preferences.py) - Preference Memory API

## Testing

Run tests with pytest:

```bash
# Run all memory tests
pytest tests/test_memory_system.py -v

# Run specific test class
pytest tests/test_memory_system.py::TestConversationMemory -v

# Run with coverage
pytest tests/test_memory_system.py --cov=src/memory
```

## Migrations

### Creating Migrations

```bash
# Create new migration
alembic revision -m "Add new field to conversations"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Initial Setup

```bash
# Initialize database with all tables
alembic upgrade head
```

## Troubleshooting

### Database Connection Issues

```python
# Check database connection
from src.memory.database import get_db_manager

db = get_db_manager()
with db.get_session() as session:
    print("Database connected!")
```

### Qdrant Connection Issues

```python
# Check Qdrant connection
from src.vector_db.qdrant_client import get_client

client = get_client()
collections = client.get_collections()
print(f"Collections: {collections}")
```

### Performance Issues

1. **Slow searches**: Check Qdrant indexing and database indexes
2. **High memory usage**: Reduce cache size or implement pagination
3. **Slow pattern extraction**: Use parallel processing or limit file count

## Examples

See [`examples/memory_examples.py`](../../examples/memory_examples.py) for comprehensive usage examples.

## Contributing

To add new memory types or features:

1. Update `models.py` with new SQLAlchemy models
2. Create Alembic migration for schema changes
3. Implement store class with CRUD operations
4. Add CLI commands in `cli/memory.py`
5. Add comprehensive tests
6. Update documentation

## License

Part of Context Workspace v3.0 - See main LICENSE file.

## Support

- **Issues**: Report bugs via GitHub Issues
- **Documentation**: See WORKSPACE_V3.0_ARCHITECTURE.md
- **Examples**: See examples/memory_examples.py
