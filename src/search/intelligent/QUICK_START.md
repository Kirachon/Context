# Intelligent Search - Quick Start Guide

## 5-Minute Integration

### 1. Basic Usage

```python
from src.search.intelligent import IntelligentSearchEngine

# Initialize
engine = IntelligentSearchEngine()

# Search (mock backend for now)
class MockBackend:
    def search(self, query, limit=50):
        return [{"file_path": "...", "similarity_score": 0.9}]

results = engine.search(
    query="find authentication",
    user_id="user123",
    search_backend=MockBackend()
)

for result in results:
    print(f"{result.file_path}: {result.final_score}")
```

### 2. Track User Context

```python
# Set current file
engine.set_current_file("user123", "frontend/App.tsx")

# Track file access
engine.track_file_access("user123", "frontend/hooks/useAuth.ts")

# Search with context
results = engine.search("authentication", "user123", backend)
# Results now ranked by context!
```

### 3. Use Templates

```python
# List templates
templates = engine.template_manager.list_templates()
print([t.name for t in templates[:5]])
# ['api_endpoints', 'authentication', 'database_models', ...]

# Search with template
results = engine.search_with_template(
    template_name="api_endpoints",
    user_id="user123",
    search_backend=backend
)
```

### 4. Parse Queries

```python
# Understand queries
parsed = engine.parse_query("find user authentication logic")
print(f"Intent: {parsed.intent}")  # FIND
print(f"Keywords: {parsed.keywords}")  # ['user', 'authentication', 'logic']
print(f"Expanded: {parsed.expanded_terms}")  # ['auth', 'login', 'oauth', ...]
```

## Key Features

- **No setup required** - Works immediately
- **Context-aware** - Ranks by user behavior
- **18 templates** - Common patterns pre-built
- **Fast** - <100ms overhead
- **Smart** - Understands developer intent

## Common Use Cases

### Find Authentication Code
```python
results = engine.search("authentication logic", user_id, backend)
```

### List All API Endpoints
```python
results = engine.search_with_template("api_endpoints", user_id, backend)
```

### Find Files in Current Project
```python
engine.set_current_file(user_id, "frontend/App.tsx")
results = engine.search("components", user_id, backend)
# Frontend components ranked higher!
```

## Dependencies

- **None required** - Works in fallback mode
- **Optional:** `spacy` for better NLP
- **Optional:** `gensim` for Word2Vec
- **Optional:** `transformers` for CodeBERT

Install enhanced features:
```bash
pip install spacy
python -m spacy download en_core_web_sm
```

## Examples

Run the examples:
```bash
python -m src.search.intelligent.example_usage
```

Run tests:
```bash
python -m pytest tests/test_intelligent_search.py -v
```

## Documentation

- **Full docs:** `src/search/intelligent/README.md`
- **Implementation:** `INTELLIGENT_SEARCH_IMPLEMENTATION.md`
- **Examples:** `src/search/intelligent/example_usage.py`
