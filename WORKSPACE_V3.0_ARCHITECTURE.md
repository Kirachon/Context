# Context Workspace v3.0 - Technical Architecture

**Version:** 3.0.0
**Date:** 2025-11-11
**Status:** Design
**Foundation:** Built on v2.5 architecture

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │   CLI    │  │ REST API │  │MCP Tools │  │  IDE Extensions      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘  │
└───────┼─────────────┼─────────────┼───────────────────┼───────────────┘
        │             │             │                   │
┌───────▼─────────────▼─────────────▼───────────────────▼───────────────┐
│                    CONTEXT-AWARE PROMPT ENGINE (NEW v3.0)             │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────┐   │
│  │ Prompt         │  │ Context        │  │ Context Ranking      │   │
│  │ Analyzer       │──▶│ Gatherer       │──▶│ & Selection          │   │
│  └────────────────┘  └────────────────┘  └──────────┬───────────┘   │
│                                                       │               │
│  ┌────────────────┐  ┌────────────────┐             │               │
│  │ Prompt         │◀─│ Hierarchical   │◀────────────┘               │
│  │ Composer       │  │ Summarizer     │                             │
│  └────────┬───────┘  └────────────────┘                             │
└───────────┼──────────────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                    AUTONOMOUS AGENTS LAYER (NEW v3.0)                │
│  ┌─────────┐  ┌────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐   │
│  │Planning │→ │Coding  │→ │Testing  │→ │Review  │→ │PR Agent  │   │
│  │ Agent   │  │ Agent  │  │ Agent   │  │ Agent  │  │          │   │
│  └─────────┘  └────────┘  └─────────┘  └────────┘  └──────────┘   │
└───────────┼──────────────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                      MEMORY SYSTEM (NEW v3.0)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │Conversation  │  │Pattern       │  │Solution & Preference     │  │
│  │Memory        │  │Memory        │  │Memory                    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└───────────┼──────────────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│              INTELLIGENCE LAYER (v2.5 - Enhanced)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Intelligent  │  │ Smart Caching│  │ Auto-Discovery           │  │
│  │ Search       │  │ (3-layer)    │  │ Engine                   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└───────────┼──────────────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                    INDEXING & STORAGE LAYER (v2.0+)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │Qdrant Vector │  │PostgreSQL    │  │Redis Cache               │  │
│  │Database      │  │(Structured)  │  │(L2)                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────────────┐
│                     EXTERNAL INTEGRATIONS (v3.0)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │GitHub API│  │Jira API  │  │LLM APIs  │  │Confluence/Notion │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Context-Aware Prompt Enhancement Architecture

### 2.1 Prompt Analysis Engine

**Location:** `src/prompt/analyzer.py`

**Components:**

```python
class PromptAnalyzer:
    """
    Analyzes user prompts to determine intent, entities, and context requirements
    """
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.token_estimator = TokenBudgetEstimator()
        self.context_selector = ContextTypeSelector()

    async def analyze(self, prompt: str, user_context: UserContext) -> PromptIntent:
        """
        Main analysis pipeline

        Returns:
            PromptIntent with classified intent, extracted entities, token budget, context types
        """
        # Step 1: Classify intent (parallel with entity extraction)
        intent, entities = await asyncio.gather(
            self.intent_classifier.classify(prompt),
            self.entity_extractor.extract(prompt, user_context)
        )

        # Step 2: Estimate token budget based on intent complexity
        token_budget = self.token_estimator.estimate(intent, entities)

        # Step 3: Select which context types to gather
        context_types = self.context_selector.select(intent, entities)

        return PromptIntent(
            intent=intent,
            entities=entities,
            token_budget=token_budget,
            context_types=context_types,
            confidence=self._calculate_confidence(intent, entities)
        )
```

#### 2.1.1 Intent Classifier

**Approach:** Rule-based (fast, accurate for common patterns) + ML fallback

**Intent Types:**
- `fix` - Bug fixing
- `explain` - Code explanation
- `implement` - New feature implementation
- `refactor` - Code refactoring
- `debug` - Debugging investigation
- `test` - Testing
- `document` - Documentation

**Implementation:**

```python
class IntentClassifier:
    """
    Classify user intent from prompt
    """
    # Rule-based patterns (fast path)
    INTENT_PATTERNS = {
        'fix': [r'\bfix\b', r'\bbug\b', r'\berror\b', r'\bissue\b', r'\bproblem\b'],
        'explain': [r'\bhow does\b', r'\bwhat is\b', r'\bexplain\b', r'\bunderstand\b'],
        'implement': [r'\badd\b', r'\bcreate\b', r'\bimplement\b', r'\bbuild\b'],
        'refactor': [r'\brefactor\b', r'\bimprove\b', r'\boptimize\b', r'\bclean\b'],
        'debug': [r'\bwhy\b', r'\bdebug\b', r'\binvestigate\b', r'\btrace\b'],
        'test': [r'\btest\b', r'\bunit test\b', r'\bintegration test\b'],
        'document': [r'\bdocument\b', r'\bdocs\b', r'\bcomment\b', r'\bdocstring\b'],
    }

    async def classify(self, prompt: str) -> Intent:
        # Try rule-based first (fast)
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, prompt, re.IGNORECASE):
                    return Intent(type=intent_type, confidence=0.9, method='rule-based')

        # Fallback to ML if no rules matched (slower but more flexible)
        if self.ml_model:
            return await self._ml_classify(prompt)

        # Default to 'explain' if uncertain
        return Intent(type='explain', confidence=0.5, method='default')
```

#### 2.1.2 Entity Extractor

**Technology:** spaCy NLP

**Entities to Extract:**
- File paths
- Function names
- Class names
- Variable names
- Error messages
- Concepts/keywords

**Implementation:**

```python
import spacy

class EntityExtractor:
    """
    Extract entities from prompt using spaCy NLP
    """
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.file_pattern = re.compile(r'[\w/.-]+\.[\w]+')  # file.ext or path/to/file.ext

    async def extract(self, prompt: str, user_context: UserContext) -> List[Entity]:
        entities = []

        # Parse with spaCy
        doc = self.nlp(prompt)

        # Extract named entities (PERSON, ORG, PRODUCT, etc.)
        for ent in doc.ents:
            entities.append(Entity(
                text=ent.text,
                type=ent.label_,
                confidence=0.8,
                source='spacy'
            ))

        # Extract file paths (regex-based)
        for match in self.file_pattern.finditer(prompt):
            file_path = match.group(0)
            # Validate file exists in workspace
            if self._file_exists(file_path, user_context.workspace):
                entities.append(Entity(
                    text=file_path,
                    type='FILE',
                    confidence=0.95,
                    source='regex'
                ))

        # Extract code identifiers (functions, classes)
        entities.extend(self._extract_code_identifiers(prompt, user_context))

        # Extract error messages
        entities.extend(self._extract_errors(prompt))

        return entities

    def _extract_code_identifiers(self, prompt: str, context: UserContext) -> List[Entity]:
        """
        Extract potential function/class names by matching against codebase index
        """
        entities = []

        # Get all tokens that look like identifiers
        identifier_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
        potential_identifiers = re.findall(identifier_pattern, prompt)

        # Check which ones exist in codebase
        for identifier in potential_identifiers:
            # Search in indexed codebase (using v2.5 intelligent search)
            if self._exists_in_codebase(identifier, context):
                entities.append(Entity(
                    text=identifier,
                    type='IDENTIFIER',
                    confidence=0.7,
                    source='codebase_match'
                ))

        return entities
```

#### 2.1.3 Token Budget Estimator

**Algorithm:** Estimate based on intent complexity and entity count

**Token Budget Ranges:**
- Simple query (1-2 entities): 10k-50k tokens
- Medium query (3-5 entities): 50k-150k tokens
- Complex query (6+ entities): 150k-400k tokens

**Implementation:**

```python
class TokenBudgetEstimator:
    """
    Estimate optimal token budget for enhanced prompt
    """
    BASE_BUDGETS = {
        'explain': 50000,      # Explanation needs moderate context
        'fix': 100000,         # Bug fixes need more context (history, related code)
        'implement': 150000,   # Implementation needs extensive context (patterns, examples)
        'refactor': 120000,    # Refactoring needs architecture context
        'debug': 120000,       # Debugging needs error traces, logs
        'test': 80000,         # Testing needs code + examples
        'document': 60000,     # Documentation needs code + existing docs
    }

    def estimate(self, intent: Intent, entities: List[Entity]) -> int:
        # Start with base budget for intent type
        base = self.BASE_BUDGETS.get(intent.type, 100000)

        # Adjust based on entity count
        entity_multiplier = 1.0 + (len(entities) * 0.1)  # +10% per entity

        # Cap at max budget
        budget = min(int(base * entity_multiplier), 400000)

        return budget
```

### 2.2 Context Gathering Engine

**Location:** `src/prompt/context_gatherer.py`

**Architecture:** Parallel gathering from 6 sources

**Implementation:**

```python
class ContextGatherer:
    """
    Gather context from multiple sources in parallel
    """
    def __init__(self):
        self.current_gatherer = CurrentContextGatherer()
        self.code_gatherer = CodeContextGatherer()  # Uses v2.5 intelligent search
        self.arch_gatherer = ArchitecturalContextGatherer()
        self.history_gatherer = HistoricalContextGatherer()  # Git integration
        self.team_gatherer = TeamContextGatherer()
        self.external_gatherer = ExternalContextGatherer()  # Optional
        self.cache = ContextCache(ttl=300)  # 5 min cache

    async def gather(self, intent: PromptIntent, user_context: UserContext) -> RawContext:
        """
        Gather context from all relevant sources in parallel
        """
        # Check cache first
        cache_key = self._make_cache_key(intent, user_context)
        cached = await self.cache.get(cache_key)
        if cached:
            metrics.context_cache_hit.inc()
            return cached

        # Determine which gatherers to use based on intent
        tasks = []

        # Always gather current context
        tasks.append(self.current_gatherer.gather(user_context))

        # Gather based on context types
        if 'code' in intent.context_types:
            tasks.append(self.code_gatherer.gather(intent.entities, user_context))

        if 'architecture' in intent.context_types:
            tasks.append(self.arch_gatherer.gather(intent.entities, user_context))

        if 'history' in intent.context_types:
            tasks.append(self.history_gatherer.gather(intent.entities, user_context))

        if 'team' in intent.context_types:
            tasks.append(self.team_gatherer.gather(intent.entities, user_context))

        if 'external' in intent.context_types and self.config.external_enabled:
            tasks.append(self.external_gatherer.gather(intent.entities, user_context))

        # Gather all in parallel with timeout
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results
        raw_context = RawContext()
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Context gathering failed: {result}")
                continue
            raw_context.merge(result)

        # Cache result
        await self.cache.set(cache_key, raw_context)

        return raw_context
```

#### 2.2.1 Current Context Gatherer

```python
class CurrentContextGatherer:
    """
    Gather context about what user is currently working on
    """
    async def gather(self, user_context: UserContext) -> ContextChunk:
        context = ContextChunk(source='current')

        # Current file
        if user_context.current_file:
            file_content = await self._read_file(user_context.current_file)
            context.add(
                type='file',
                path=user_context.current_file,
                content=file_content,
                priority=10.0  # HIGHEST priority
            )

        # Selected region
        if user_context.selected_region:
            context.add(
                type='selection',
                content=user_context.selected_region.text,
                lines=user_context.selected_region.lines,
                priority=10.0
            )

        # Open files in IDE
        for open_file in user_context.open_files:
            context.add(
                type='open_file',
                path=open_file,
                content=await self._read_file(open_file),
                priority=5.0  # HIGH priority
            )

        return context
```

#### 2.2.2 Code Context Gatherer

**Integration:** Uses v2.5 Intelligent Search Engine

```python
class CodeContextGatherer:
    """
    Gather related code context using v2.5 intelligent search
    """
    def __init__(self):
        # Reuse v2.5 intelligent search
        from search.intelligent import IntelligentSearch
        self.search = IntelligentSearch()

    async def gather(self, entities: List[Entity], user_context: UserContext) -> ContextChunk:
        context = ContextChunk(source='code')

        # For each entity, find related code
        for entity in entities:
            if entity.type == 'FILE':
                # Get file content
                content = await self._read_file(entity.text)
                context.add(
                    type='file',
                    path=entity.text,
                    content=content,
                    priority=8.0
                )

                # Get dependencies (imports)
                dependencies = await self._get_dependencies(entity.text)
                for dep in dependencies:
                    context.add(
                        type='dependency',
                        path=dep,
                        content=await self._read_file(dep),
                        priority=6.0
                    )

                # Get reverse dependencies (who imports this file)
                reverse_deps = await self._get_reverse_dependencies(entity.text)
                for dep in reverse_deps[:5]:  # Top 5 only
                    context.add(
                        type='reverse_dependency',
                        path=dep,
                        content=await self._read_file(dep),
                        priority=5.0
                    )

                # Get test files
                test_files = await self._find_test_files(entity.text)
                for test_file in test_files:
                    context.add(
                        type='test',
                        path=test_file,
                        content=await self._read_file(test_file),
                        priority=7.0
                    )

            elif entity.type == 'IDENTIFIER':
                # Search for this identifier using v2.5 intelligent search
                search_results = await self.search.search(
                    query=entity.text,
                    user_context=user_context,
                    limit=10
                )

                for result in search_results:
                    context.add(
                        type='search_result',
                        path=result.file_path,
                        content=result.snippet,
                        priority=result.score * 10  # Convert 0-1 score to 0-10
                    )

        return context
```

#### 2.2.3 Historical Context Gatherer

**Integration:** Git history analysis

```python
import subprocess

class HistoricalContextGatherer:
    """
    Gather historical context from git
    """
    async def gather(self, entities: List[Entity], user_context: UserContext) -> ContextChunk:
        context = ContextChunk(source='history')

        # Get recent commits (last 24 hours)
        recent_commits = await self._get_recent_commits(hours=24)
        for commit in recent_commits[:10]:  # Top 10
            context.add(
                type='recent_commit',
                commit_hash=commit.hash,
                author=commit.author,
                message=commit.message,
                files=commit.files_changed,
                priority=6.0
            )

        # For each file entity, get git blame
        for entity in entities:
            if entity.type == 'FILE':
                blame = await self._get_git_blame(entity.text)
                context.add(
                    type='git_blame',
                    path=entity.text,
                    blame=blame,
                    priority=5.0
                )

        # Get commits that touched same files
        related_commits = await self._get_related_commits(entities)
        for commit in related_commits[:5]:
            context.add(
                type='related_commit',
                commit_hash=commit.hash,
                author=commit.author,
                message=commit.message,
                priority=5.0
            )

        return context

    async def _get_recent_commits(self, hours: int = 24) -> List[Commit]:
        """Get commits from last N hours"""
        since = datetime.now() - timedelta(hours=hours)
        cmd = [
            'git', 'log',
            f'--since={since.isoformat()}',
            '--pretty=format:%H|%an|%ae|%s',
            '--name-only'
        ]
        output = await self._run_git_command(cmd)
        return self._parse_git_log(output)
```

### 2.3 Context Ranking Engine

**Location:** `src/prompt/ranker.py`

**10-Factor Scoring Formula:**

```python
class ContextRanker:
    """
    Rank context chunks by relevance using 10-factor scoring
    """
    DEFAULT_WEIGHTS = {
        'relevance_score': 3.0,           # Semantic similarity (HIGHEST)
        'recency_score': 2.0,             # How recent
        'proximity_score': 2.0,           # Distance from current file
        'dependency_score': 1.5,          # Direct dependency?
        'usage_frequency': 1.0,           # How often used
        'error_correlation': 2.0,         # Related to errors?
        'team_signal': 1.0,               # Expert's code?
        'historical_success': 1.5,        # Solved similar issues?
        'architectural_importance': 1.0,  # Core component?
        'user_preference': 0.5,           # User referenced?
    }

    def __init__(self, weights: dict = None):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    async def rank(self,
                  raw_context: RawContext,
                  intent: PromptIntent,
                  user_context: UserContext) -> RankedContext:
        """
        Rank all context chunks by relevance
        """
        # Compute embedding for prompt
        prompt_embedding = self.embedding_model.encode(intent.original_prompt)

        scored_chunks = []
        for chunk in raw_context.chunks:
            # Compute all 10 factors
            factors = {
                'relevance_score': self._semantic_similarity(
                    prompt_embedding,
                    chunk
                ),
                'recency_score': self._recency_score(chunk),
                'proximity_score': self._proximity_score(chunk, user_context),
                'dependency_score': self._dependency_score(chunk, user_context),
                'usage_frequency': self._usage_frequency(chunk),
                'error_correlation': self._error_correlation(chunk, intent),
                'team_signal': self._team_signal(chunk, user_context),
                'historical_success': self._historical_success(chunk),
                'architectural_importance': self._architectural_importance(chunk),
                'user_preference': self._user_preference(chunk, intent),
            }

            # Compute weighted score
            total_score = sum(
                factors[name] * weight
                for name, weight in self.weights.items()
            )

            scored_chunks.append(ScoredChunk(
                chunk=chunk,
                score=total_score,
                factors=factors
            ))

        # Sort by score (descending)
        scored_chunks.sort(key=lambda x: x.score, reverse=True)

        return RankedContext(chunks=scored_chunks)

    def _semantic_similarity(self, prompt_embedding: np.ndarray, chunk: ContextChunk) -> float:
        """
        Compute cosine similarity between prompt and context
        Returns: 0.0 - 1.0
        """
        chunk_embedding = self.embedding_model.encode(chunk.content)
        similarity = cosine_similarity([prompt_embedding], [chunk_embedding])[0][0]
        return max(0.0, min(1.0, similarity))

    def _recency_score(self, chunk: ContextChunk) -> float:
        """
        Score based on how recent this context is
        Returns: 0.0 - 1.0
        """
        if not chunk.timestamp:
            return 0.5  # Unknown age

        age_hours = (datetime.now() - chunk.timestamp).total_seconds() / 3600

        # Exponential decay: recent = 1.0, 1 week old = 0.1
        score = math.exp(-age_hours / 168)  # 168 hours = 1 week
        return max(0.0, min(1.0, score))

    def _proximity_score(self, chunk: ContextChunk, user_context: UserContext) -> float:
        """
        Score based on distance from current file
        Returns: 0.0 - 1.0
        """
        if not user_context.current_file or not chunk.file_path:
            return 0.5

        # Same file = 1.0
        if chunk.file_path == user_context.current_file:
            return 1.0

        # Same directory = 0.8
        if os.path.dirname(chunk.file_path) == os.path.dirname(user_context.current_file):
            return 0.8

        # Same module (top-level dir) = 0.6
        if chunk.file_path.split('/')[0] == user_context.current_file.split('/')[0]:
            return 0.6

        # Different module = 0.3
        return 0.3
```

### 2.4 Hierarchical Summarization

**Location:** `src/prompt/summarizer.py`

**Strategy:** 4-tier compression based on relevance score

```python
class HierarchicalSummarizer:
    """
    Apply hierarchical summarization to fit token budget
    """
    def __init__(self):
        self.extractive_summarizer = ExtractiveSummarizer()
        self.abstractive_summarizer = AbstractiveSummarizer()  # Uses LLM
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def summarize(self,
                       ranked_context: RankedContext,
                       token_budget: int) -> SummarizedContext:
        """
        Apply tiered summarization to fit token budget

        Tier 1 (Top 20%): Include verbatim
        Tier 2 (20-50%): Summarize to 33%
        Tier 3 (50-80%): One-line summary (10%)
        Tier 4 (Bottom 20%): Drop
        """
        total_chunks = len(ranked_context.chunks)
        tier1_count = int(total_chunks * 0.2)
        tier2_count = int(total_chunks * 0.3)
        tier3_count = int(total_chunks * 0.3)

        summarized = SummarizedContext()
        current_tokens = 0

        # Tier 1: Critical context (verbatim)
        for chunk in ranked_context.chunks[:tier1_count]:
            tokens = self._count_tokens(chunk.content)
            if current_tokens + tokens > token_budget:
                break
            summarized.add(chunk, compression='none')
            current_tokens += tokens

        # Tier 2: Important context (summarized to 33%)
        for chunk in ranked_context.chunks[tier1_count:tier1_count+tier2_count]:
            if chunk.is_code:
                summary = await self.extractive_summarizer.summarize(
                    chunk.content,
                    ratio=0.33
                )
            else:
                summary = await self.abstractive_summarizer.summarize(
                    chunk.content,
                    max_length=len(chunk.content) // 3
                )

            tokens = self._count_tokens(summary)
            if current_tokens + tokens > token_budget:
                break
            summarized.add(chunk, compression='medium', summary=summary)
            current_tokens += tokens

        # Tier 3: Supporting context (one-line)
        for chunk in ranked_context.chunks[tier1_count+tier2_count:tier1_count+tier2_count+tier3_count]:
            one_liner = await self._generate_one_liner(chunk)
            tokens = self._count_tokens(one_liner)
            if current_tokens + tokens > token_budget:
                break
            summarized.add(chunk, compression='high', summary=one_liner)
            current_tokens += tokens

        # Tier 4: Drop
        # (not included)

        return summarized

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        return len(self.tokenizer.encode(text))
```

### 2.5 Prompt Composer

**Location:** `src/prompt/composer.py`

```python
from jinja2 import Template

class PromptComposer:
    """
    Compose final enhanced prompt from summarized context
    """
    def __init__(self):
        self.template = self._load_template()

    def compose(self,
               original_prompt: str,
               summarized_context: SummarizedContext,
               intent: PromptIntent) -> EnhancedPrompt:
        """
        Compose structured enhanced prompt
        """
        # Group context by type
        current_context = summarized_context.get_by_type('current')
        code_context = summarized_context.get_by_type('code')
        arch_context = summarized_context.get_by_type('architecture')
        history_context = summarized_context.get_by_type('history')
        team_context = summarized_context.get_by_type('team')

        # Render template
        enhanced_prompt = self.template.render(
            original_prompt=original_prompt,
            intent=intent.type,
            current_context=current_context,
            code_context=code_context,
            arch_context=arch_context,
            history_context=history_context,
            team_context=team_context,
        )

        return EnhancedPrompt(
            original=original_prompt,
            enhanced=enhanced_prompt,
            token_count=self._count_tokens(enhanced_prompt),
            metadata=self._extract_metadata(summarized_context)
        )

    def _load_template(self) -> Template:
        """Load Jinja2 template"""
        template_str = """
# USER REQUEST
{{ original_prompt }}

{% if current_context %}
# CURRENT CONTEXT
{% for chunk in current_context %}
{{ chunk.format() }}
{% endfor %}
{% endif %}

{% if code_context %}
# RELATED CODE
{% for chunk in code_context|sort(attribute='score', reverse=True) %}
## {{ chunk.path }} (Relevance: {{ "%.2f"|format(chunk.score) }})
{{ chunk.content }}
{% endfor %}
{% endif %}

{% if arch_context %}
# ARCHITECTURE
{% for chunk in arch_context %}
{{ chunk.format() }}
{% endfor %}
{% endif %}

{% if history_context %}
# RECENT CHANGES
{% for chunk in history_context %}
- {{ chunk.format() }}
{% endfor %}
{% endif %}

{% if team_context %}
# TEAM KNOWLEDGE
{% for chunk in team_context %}
{{ chunk.format() }}
{% endfor %}
{% endif %}
        """.strip()

        return Template(template_str)
```

---

## 3. Memory System Architecture

### 3.1 Storage Layer

**PostgreSQL Schema:**

```sql
-- Conversation Memory
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    prompt TEXT NOT NULL,
    enhanced_prompt TEXT,
    response TEXT,
    intent VARCHAR(50),
    entities JSONB,
    feedback JSONB,
    resolution BOOLEAN,
    INDEX idx_user_timestamp (user_id, timestamp DESC),
    INDEX idx_intent (intent)
);

-- Pattern Memory
CREATE TABLE code_patterns (
    id UUID PRIMARY KEY,
    pattern_type VARCHAR(100) NOT NULL,
    name VARCHAR(255),
    example_code TEXT,
    description TEXT,
    usage_count INT DEFAULT 0,
    files_using JSONB,
    user_preference_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_pattern_type (pattern_type)
);

-- Solution Memory
CREATE TABLE solutions (
    id UUID PRIMARY KEY,
    problem_description TEXT NOT NULL,
    solution_code TEXT,
    files_affected JSONB,
    success_rate FLOAT DEFAULT 0.0,
    usage_count INT DEFAULT 0,
    similar_problems JSONB,  -- Array of UUIDs
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_success_rate (success_rate DESC)
);

-- User Preference Memory
CREATE TABLE user_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    code_style JSONB,  -- indentation, naming, etc.
    preferred_libraries JSONB,
    testing_approach VARCHAR(50),
    documentation_level VARCHAR(50),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Qdrant Collections:**

```python
# Conversation embeddings
conversation_collection = {
    "name": "conversations",
    "vector_size": 384,  # all-MiniLM-L6-v2
    "distance": "Cosine"
}

# Pattern embeddings
pattern_collection = {
    "name": "code_patterns",
    "vector_size": 384,
    "distance": "Cosine"
}

# Solution embeddings
solution_collection = {
    "name": "solutions",
    "vector_size": 384,
    "distance": "Cosine"
}
```

---

## 4. API Design

### 4.1 REST API Endpoints

```python
# Prompt Enhancement
POST /api/v1/prompts/enhance
Request:
{
    "prompt": "Fix authentication bug",
    "user_context": {
        "current_file": "backend/auth/jwt.py",
        "workspace_id": "uuid"
    },
    "options": {
        "token_budget": 200000,
        "include_external": false
    }
}
Response:
{
    "enhanced_prompt": "...",
    "token_count": 150234,
    "latency_ms": 1523,
    "metadata": {...}
}

# Memory Query
GET /api/v1/memory/conversations?query=authentication&limit=5
GET /api/v1/memory/patterns?type=api_design
POST /api/v1/memory/feedback
{
    "conversation_id": "uuid",
    "helpful": true,
    "corrections": "..."
}
```

### 4.2 CLI Commands

```bash
# Enhance prompt
context enhance-prompt "Fix authentication bug"
context enhance-prompt "Fix authentication bug" --budget 300000 --format json

# Query memory
context memory conversations --query "authentication"
context memory patterns --type error_handling

# Configure
context config set prompt_enhancement.token_budget 300000
context config set prompt_enhancement.excluded_sources external
```

---

## 5. Performance Optimization

### 5.1 Caching Strategy

- **Context cache**: 5-minute TTL, LRU eviction
- **Embedding cache**: Permanent, invalidated on code changes
- **Memory cache**: Redis for fast lookups

### 5.2 Parallel Processing

- Context gathering: 6 parallel tasks
- Context ranking: Batch processing
- Summarization: Async LLM calls

### 5.3 Resource Pooling

- Database connection pool
- LLM API connection pool
- Git subprocess pool

---

## 6. Deployment

```yaml
# docker-compose.yml additions
services:
  context-api:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - qdrant
      - redis
```

---

**Status:** ✅ Architecture Design Complete
**Next:** Create implementation stories
