# Intelligent Search Engine

Natural language search with context-aware ranking for Context Workspace v2.5.

## Overview

The Intelligent Search Engine understands developer intent and ranks results based on user context, including:
- Current file/project being edited
- Recently accessed files
- Frequently accessed files
- Team usage patterns
- Project dependencies

## Components

### 1. Query Parser (`query_parser.py`)

NLP-based query parser that:
- Uses spaCy for entity extraction (optional)
- Detects intent (find, list, show, search)
- Expands queries with synonyms
- Handles code-specific language

**Example:**
```python
from src.search.intelligent import QueryParser

parser = QueryParser(use_spacy=True)
parsed = parser.parse("find user authentication logic")

print(f"Intent: {parsed.intent}")  # Intent.FIND
print(f"Keywords: {parsed.keywords}")  # ['user', 'authentication', 'logic']
print(f"Expanded: {parsed.expanded_terms}")  # ['auth', 'login', 'oauth', ...]
```

### 2. Query Expander (`query_expander.py`)

Expands queries with:
- Synonyms (auth → authentication, login, oauth)
- Acronyms (API → Application Programming Interface)
- Related concepts (authentication → session, token, password)
- Word2Vec embeddings (optional)
- CodeBERT embeddings (optional)

**Example:**
```python
from src.search.intelligent import QueryExpander

expander = QueryExpander()
expansion = expander.expand("API endpoint")

for term in expansion.expanded_terms:
    print(f"{term.expanded} (score: {term.relevance_score})")
# Output:
# endpoint (score: 0.9)
# route (score: 0.9)
# handler (score: 0.9)
# Application Programming Interface (score: 1.0)
```

### 3. Context Collector (`context_collector.py`)

Tracks user context:
- Current file/project
- Recent files (last hour)
- Frequent files (top 20)
- Recent queries (last 10)
- Team usage patterns

**Example:**
```python
from src.search.intelligent import ContextCollector

collector = ContextCollector()

# Track user activity
collector.set_current_file("user1", "frontend/App.tsx")
collector.track_file_access("user1", "frontend/hooks/useAuth.ts")
collector.track_query("user1", "authentication logic")

# Get context
context = collector.collect("user1")
print(f"Current: {context.current_file}")
print(f"Recent: {context.recent_files}")
```

### 4. Context Ranker (`context_ranker.py`)

Multi-factor ranking with boosts:

```
final_score = base_score * 1.0 +
              current_file_boost * 2.0 +
              recent_files_boost * 1.5 +
              frequent_files_boost * 1.3 +
              team_patterns_boost * 1.2 +
              relationship_boost * 1.5 +
              recency_boost * 0.5 +
              exact_match_boost * 0.8
```

**Example:**
```python
from src.search.intelligent import ContextRanker, SearchContext

ranker = ContextRanker()

# Mock results
results = [
    {"file_path": "backend/auth.py", "similarity_score": 0.95},
    {"file_path": "frontend/useAuth.ts", "similarity_score": 0.88},
]

# User context (in frontend)
context = SearchContext(
    user_id="user1",
    current_project="frontend",
    recent_files=["frontend/useAuth.ts"]
)

# Rank with context
ranked = ranker.rank(results, context)

# frontend/useAuth.ts will rank higher due to context!
for result in ranked:
    print(f"{result.file_path}: {result.final_score:.3f}")
    print(result.explain_ranking())
```

### 5. Search Templates (`templates.py`)

Pre-built templates for common patterns:

| Template | Description |
|----------|-------------|
| `api_endpoints` | Find all API endpoints and route handlers |
| `authentication` | Find authentication and authorization logic |
| `database_models` | Find database models and schemas |
| `error_handling` | Find error handling and exception code |
| `configuration` | Find configuration files and settings |
| `tests` | Find test files and test cases |
| `components` | Find React/Vue components |
| `types` | Find type definitions and interfaces |
| ... | 18 total built-in templates |

**Example:**
```python
from src.search.intelligent import SearchTemplateManager

manager = SearchTemplateManager()

# List templates
for template in manager.list_templates():
    print(f"{template.name}: {template.description}")

# Apply template
query = manager.apply_template("api_endpoints")
# Returns: "route handler endpoint api controller"

# Suggest templates
suggestions = manager.suggest_templates("find login logic")
# Returns: [authentication, validation, security]
```

## End-to-End Usage

```python
from src.search.intelligent import IntelligentSearchEngine

# Initialize engine
engine = IntelligentSearchEngine(use_spacy=True)

# Setup user context
user_id = "developer1"
engine.set_current_file(user_id, "frontend/App.tsx")

# Perform intelligent search
results = engine.search(
    query="authentication logic",
    user_id=user_id,
    search_backend=your_search_backend
)

# Results are ranked with context!
for result in results:
    print(f"{result.file_path}: {result.final_score:.3f}")
    print(result.explain_ranking())
    print(f"Context relevance: {result.context_relevance:.3f}")
```

## Ranking Example

**Query:** "authentication logic"
**Current file:** `frontend/App.tsx`

**Before ranking:**
1. `backend/auth/jwt.py` - Similarity: 0.95
2. `frontend/hooks/useAuth.ts` - Similarity: 0.88
3. `shared/types/auth.ts` - Similarity: 0.82

**After context ranking:**
1. `frontend/hooks/useAuth.ts` - **Final: 4.955** ⬆️ (current project boost!)
2. `backend/auth/jwt.py` - Final: 0.95
3. `shared/types/auth.ts` - Final: 0.82

## Performance

- **Query parsing:** <10ms (without spaCy), <50ms (with spaCy)
- **Query expansion:** <5ms
- **Context collection:** <5ms
- **Ranking:** <10ms for 50 results
- **Total overhead:** **<100ms** for p95

## Dependencies

### Required
- None (fallback mode works without any external dependencies)

### Optional (Enhanced Features)
- `spacy` + `en_core_web_sm`: Better NLP parsing
- `gensim`: Word2Vec embeddings
- `transformers`: CodeBERT embeddings

### Installation

```bash
# Basic (no dependencies)
# Works out of the box with fallback implementations

# Enhanced NLP
pip install spacy
python -m spacy download en_core_web_sm

# Word2Vec (optional)
pip install gensim

# CodeBERT (optional)
pip install transformers
```

## Data Models

### ParsedQuery
```python
@dataclass
class ParsedQuery:
    original: str
    entities: List[Entity]
    intent: Intent
    expanded_terms: List[str]
    confidence: float
    keywords: List[str]
```

### SearchContext
```python
@dataclass
class SearchContext:
    user_id: str
    current_file: Optional[str]
    current_project: Optional[str]
    recent_files: List[str]
    frequent_files: List[str]
    team_patterns: Dict[str, float]
```

### EnhancedSearchResult
```python
@dataclass
class EnhancedSearchResult:
    file_path: str
    base_score: float
    final_score: float
    boost_breakdown: BoostFactors
    context_relevance: float
    query_understanding: ParsedQuery
```

## Testing

Run the example file:
```bash
python -m src.search.intelligent.example_usage
```

This demonstrates:
1. Query parsing
2. Query expansion
3. Context collection
4. Context-aware ranking
5. Search templates
6. End-to-end search

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 IntelligentSearchEngine                  │
└────────────┬────────────────────────────────────────────┘
             │
    ┌────────┼───────────────────────────────────────┐
    │        │                                       │
┌───▼────┐ ┌─▼──────┐ ┌──────────┐ ┌────────────┐ ┌──▼──────┐
│ Query  │ │ Query  │ │ Context  │ │ Context    │ │Template │
│ Parser │ │Expander│ │Collector │ │  Ranker    │ │ Manager │
└────────┘ └────────┘ └──────────┘ └────────────┘ └─────────┘
```

## NLP Techniques Used

1. **Tokenization:** Breaking queries into words
2. **Stop word removal:** Removing common words (the, a, is)
3. **Lemmatization:** Converting words to base form (spaCy)
4. **Named Entity Recognition:** Extracting file names, functions (spaCy)
5. **Part-of-Speech tagging:** Identifying verbs for intent (spaCy)
6. **Pattern matching:** Regex for code-specific entities
7. **Synonym expansion:** Mapping related terms
8. **Acronym expansion:** API → Application Programming Interface
9. **Query understanding:** Detecting intent from keywords

## Future Enhancements

- [ ] Machine learning-based ranking
- [ ] Query refinement suggestions
- [ ] Semantic caching (cache similar queries)
- [ ] Cross-repository search
- [ ] Voice search integration
- [ ] Historical query analysis
- [ ] Personalized ranking weights
- [ ] A/B testing framework

## License

Part of Context Workspace v2.5
