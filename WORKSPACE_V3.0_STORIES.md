# Context Workspace v3.0 - Implementation Stories & Epics

**Version:** 3.0.0
**Date:** 2025-11-11
**Timeline:** 24 weeks
**Focus:** Tier 1 (Context-Aware Prompt Enhancement) - Weeks 1-6

---

## Epic 1: Prompt Analysis Engine (Week 1-2)

**Goal:** Analyze user prompts to determine intent, entities, and context requirements
**Effort:** 80 hours
**Priority:** P0

### Story 1.1: Intent Classifier Implementation

**Description:** Implement rule-based + ML fallback intent classifier to categorize user prompts.

**Acceptance Criteria:**
- AC1: Given prompt "Fix the authentication bug", classifier returns intent='fix' with confidence>0.9
- AC2: Given prompt "How does caching work?", classifier returns intent='explain'
- AC3: Classification completes in <100ms for 95% of requests
- AC4: Test coverage >80%

**Technical Tasks:**
1. Create `src/prompt/analyzer.py` module
2. Implement `IntentClassifier` class with rule-based patterns
3. Add ML model integration (optional, graceful fallback)
4. Create intent enum (fix, explain, implement, refactor, debug, test, document)
5. Add unit tests for all intent types
6. Add benchmarking tests for latency
7. Integrate with Prometheus metrics

**Dependencies:** None

**Estimated Effort:** 16 hours

---

### Story 1.2: Entity Extractor with spaCy

**Description:** Extract entities (files, functions, errors) from prompts using spaCy NLP.

**Acceptance Criteria:**
- AC1: Given prompt with file path "backend/auth.py", extracts FILE entity
- AC2: Given prompt with function name "process_payment", extracts IDENTIFIER entity
- AC3: Given prompt with TypeError message, extracts ERROR entity
- AC4: Extraction completes in <200ms
- AC5: Test coverage >80%

**Technical Tasks:**
1. Install spaCy and download en_core_web_sm model
2. Create `EntityExtractor` class in `src/prompt/analyzer.py`
3. Implement file path extraction (regex-based)
4. Implement code identifier extraction (match against codebase index)
5. Implement error message extraction
6. Add validation to check entities exist in codebase
7. Add unit tests
8. Document entity types and examples

**Dependencies:** spaCy package

**Estimated Effort:** 20 hours

---

### Story 1.3: Token Budget Estimator

**Description:** Estimate optimal token budget based on intent and entity complexity.

**Acceptance Criteria:**
- AC1: Simple explain query (1-2 entities) → 50k budget
- AC2: Complex implement query (6+ entities) → 150k-400k budget
- AC3: Budget never exceeds 400k tokens
- AC4: Estimation completes in <10ms

**Technical Tasks:**
1. Create `TokenBudgetEstimator` class
2. Define base budgets for each intent type
3. Implement entity-based multiplier logic
4. Add configurability for max budget
5. Add unit tests
6. Document budget ranges

**Dependencies:** Story 1.1, 1.2

**Estimated Effort:** 12 hours

---

### Story 1.4: Context Type Selector

**Description:** Select which context types to gather based on intent.

**Acceptance Criteria:**
- AC1: Fix intent → selects code, history, errors
- AC2: Explain intent → selects code, architecture, docs
- AC3: Implement intent → selects patterns, examples, architecture
- AC4: Selection is configurable per project

**Technical Tasks:**
1. Create `ContextTypeSelector` class
2. Define default context types for each intent
3. Add configuration support (.context-workspace.json)
4. Add unit tests
5. Document context type mappings

**Dependencies:** Story 1.1

**Estimated Effort:** 10 hours

---

### Story 1.5: Prompt Analyzer Integration & Testing

**Description:** Integrate all components into `PromptAnalyzer` and add comprehensive tests.

**Acceptance Criteria:**
- AC1: Full analysis completes in <300ms
- AC2: Returns PromptIntent with all fields populated
- AC3: Integration tests cover 10+ real-world scenarios
- AC4: Performance benchmarks documented

**Technical Tasks:**
1. Create `PromptAnalyzer` orchestrator class
2. Integrate intent classifier, entity extractor, budget estimator, type selector
3. Add async support for parallel processing
4. Create integration tests
5. Add performance benchmarks
6. Document API usage

**Dependencies:** Stories 1.1-1.4

**Estimated Effort:** 22 hours

---

## Epic 2: Context Gathering Engine (Week 3-4)

**Goal:** Gather context from 6 sources in parallel
**Effort:** 120 hours
**Priority:** P0

### Story 2.1: Current Context Gatherer

**Description:** Gather context about what user is currently working on.

**Acceptance Criteria:**
- AC1: Returns current file content with priority=10.0
- AC2: Returns selected region if available
- AC3: Returns all open files in IDE
- AC4: Gathering completes in <100ms

**Technical Tasks:**
1. Create `src/prompt/context_gatherer.py` module
2. Implement `CurrentContextGatherer` class
3. Add file reading with error handling
4. Add selection region support
5. Add open files tracking (via user context)
6. Add unit tests
7. Add file read caching

**Dependencies:** None

**Estimated Effort:** 16 hours

---

### Story 2.2: Code Context Gatherer (Integrate v2.5 Search)

**Description:** Gather related code using v2.5 intelligent search engine.

**Acceptance Criteria:**
- AC1: For FILE entity, returns dependencies (imports)
- AC2: For FILE entity, returns reverse dependencies (importers)
- AC3: For FILE entity, returns test files
- AC4: For IDENTIFIER entity, returns search results from v2.5 search
- AC5: Gathering completes in <1 second

**Technical Tasks:**
1. Create `CodeContextGatherer` class
2. Integrate with v2.5 `IntelligentSearch`
3. Implement dependency detection (parse imports)
4. Implement reverse dependency detection (search for imports)
5. Implement test file discovery (naming conventions)
6. Add caching for dependencies
7. Add unit tests
8. Add integration tests with v2.5 search

**Dependencies:** v2.5 intelligent search, Story 2.1

**Estimated Effort:** 24 hours

---

### Story 2.3: Architectural Context Gatherer

**Description:** Gather architectural context (schemas, configs, dependencies).

**Acceptance Criteria:**
- AC1: Returns project dependency graph
- AC2: Returns API schemas (OpenAPI, GraphQL)
- AC3: Returns database schemas
- AC4: Returns relevant config files

**Technical Tasks:**
1. Create `ArchitecturalContextGatherer` class
2. Implement dependency graph extraction (from package files)
3. Implement API schema detection and parsing
4. Implement database schema detection
5. Implement config file discovery
6. Add caching
7. Add unit tests

**Dependencies:** Story 2.1

**Estimated Effort:** 20 hours

---

### Story 2.4: Historical Context Gatherer (Git Integration)

**Description:** Gather historical context from git.

**Acceptance Criteria:**
- AC1: Returns commits from last 24 hours
- AC2: For FILE entity, returns git blame
- AC3: Returns commits that touched related files
- AC4: Gathering completes in <500ms

**Technical Tasks:**
1. Create `HistoricalContextGatherer` class
2. Implement git log parsing (recent commits)
3. Implement git blame parsing
4. Implement related commit detection
5. Add subprocess pooling for git commands
6. Add error handling for non-git repositories
7. Add unit tests
8. Add performance optimization (caching)

**Dependencies:** git installed

**Estimated Effort:** 20 hours

---

### Story 2.5: Team Context Gatherer

**Description:** Gather team context (code owners, experts, patterns).

**Acceptance Criteria:**
- AC1: Returns code owners from CODEOWNERS file
- AC2: Returns expert developers (by commit frequency)
- AC3: Returns team coding patterns (from pattern memory - stub for now)

**Technical Tasks:**
1. Create `TeamContextGatherer` class
2. Implement CODEOWNERS parsing
3. Implement expert detection (git log analysis)
4. Add pattern memory integration (stub for Epic 6)
5. Add unit tests

**Dependencies:** Story 2.4

**Estimated Effort:** 16 hours

---

### Story 2.6: External Context Gatherer (Optional)

**Description:** Gather context from external APIs (GitHub, Jira - optional, can be disabled).

**Acceptance Criteria:**
- AC1: If enabled, fetches GitHub issues mentioning files
- AC2: Gracefully handles API failures (return empty, log warning)
- AC3: Respects rate limits
- AC4: Can be disabled via config

**Technical Tasks:**
1. Create `ExternalContextGatherer` class
2. Implement GitHub API integration (issues, PRs)
3. Implement Jira API integration (tickets)
4. Add rate limiting
5. Add error handling and fallback
6. Add configuration support
7. Add unit tests

**Dependencies:** GitHub API token, Jira API token (optional)

**Estimated Effort:** 16 hours

---

### Story 2.7: Parallel Context Gathering Orchestration

**Description:** Orchestrate parallel gathering from all sources with timeout.

**Acceptance Criteria:**
- AC1: All gatherers run in parallel (asyncio.gather)
- AC2: Total gathering time <1.5 seconds (p95)
- AC3: Timeout after 2 seconds, return partial results
- AC4: Failed gatherers don't block others

**Technical Tasks:**
1. Create `ContextGatherer` orchestrator class
2. Implement parallel gathering with asyncio
3. Add timeout handling
4. Add exception handling (return_exceptions=True)
5. Add result merging logic
6. Add metrics (latency per source)
7. Add integration tests

**Dependencies:** Stories 2.1-2.6

**Estimated Effort:** 16 hours

---

### Story 2.8: Context Caching Layer

**Description:** Cache gathered context for 5 minutes to reduce latency.

**Acceptance Criteria:**
- AC1: Cache hit returns in <50ms
- AC2: Cache key includes prompt hash + user context
- AC3: TTL = 5 minutes
- AC4: Cache hit rate >30% in normal usage

**Technical Tasks:**
1. Create `ContextCache` class (in-memory LRU)
2. Implement cache key generation
3. Implement TTL expiration
4. Add cache metrics (hit/miss rates)
5. Add unit tests

**Dependencies:** Story 2.7

**Estimated Effort:** 12 hours

---

## Epic 3: Context Ranking & Selection (Week 5)

**Goal:** Rank and summarize context to fit token budget
**Effort:** 80 hours
**Priority:** P0

### Story 3.1: 10-Factor Relevance Scorer

**Description:** Implement 10-factor scoring formula for context ranking.

**Acceptance Criteria:**
- AC1: All 10 factors computed correctly
- AC2: Weighted sum produces 0-10 score range
- AC3: Ranking completes in <300ms for 100 chunks
- AC4: Test coverage >80%

**Technical Tasks:**
1. Create `src/prompt/ranker.py` module
2. Implement `ContextRanker` class
3. Implement each of 10 scoring factors:
   - semantic_similarity (using sentence-transformers)
   - recency_score (time-based decay)
   - proximity_score (file distance)
   - dependency_score (dependency graph)
   - usage_frequency (file access patterns)
   - error_correlation (error message matching)
   - team_signal (expert author)
   - historical_success (from memory - stub)
   - architectural_importance (dependency count)
   - user_preference (explicit references)
4. Implement weighted scoring formula
5. Add normalization (0-1 range)
6. Add configurable weights
7. Add unit tests for each factor
8. Add integration tests

**Dependencies:** sentence-transformers package

**Estimated Effort:** 32 hours

---

### Story 3.2: Hierarchical Summarization (Extractive for Code)

**Description:** Implement extractive summarization for code (keep important lines).

**Acceptance Criteria:**
- AC1: Tier 1 (top 20%) - no compression
- AC2: Tier 2 (20-50%) - compress to 33% of original
- AC3: Tier 3 (50-80%) - one-line summary
- AC4: Tier 4 (bottom 20%) - dropped
- AC5: Summarization respects token budget

**Technical Tasks:**
1. Create `src/prompt/summarizer.py` module
2. Implement `HierarchicalSummarizer` class
3. Implement `ExtractiveSummarizer` for code
4. Implement tier-based compression logic
5. Add token counting (tiktoken)
6. Add budget enforcement
7. Add unit tests
8. Add quality tests (ensure summary is valid code)

**Dependencies:** tiktoken package

**Estimated Effort:** 24 hours

---

### Story 3.3: Hierarchical Summarization (Abstractive for Docs)

**Description:** Implement abstractive summarization for documentation using LLM.

**Acceptance Criteria:**
- AC1: Uses LLM (GPT/Claude) for summarization
- AC2: Compresses docs to target length
- AC3: Fallback to extractive if LLM unavailable
- AC4: Caches summaries to reduce LLM calls

**Technical Tasks:**
1. Implement `AbstractiveSummarizer` class
2. Integrate with OpenAI or Anthropic API
3. Add prompt template for summarization
4. Add caching for summaries
5. Add fallback to extractive
6. Add error handling
7. Add unit tests
8. Add cost monitoring (API usage)

**Dependencies:** OpenAI or Anthropic API key, Story 3.2

**Estimated Effort:** 24 hours

---

## Epic 4: Prompt Composer (Week 6)

**Goal:** Compose final enhanced prompt from summarized context
**Effort:** 40 hours
**Priority:** P0

### Story 4.1: Template Engine Integration (Jinja2)

**Description:** Create Jinja2 template for structured prompt composition.

**Acceptance Criteria:**
- AC1: Template renders all context sections
- AC2: Output is well-formatted markdown
- AC3: Metadata included (file paths, scores, timestamps)
- AC4: Template is customizable

**Technical Tasks:**
1. Create `src/prompt/composer.py` module
2. Implement `PromptComposer` class
3. Create default Jinja2 template
4. Add context grouping by type
5. Add metadata formatting
6. Add template customization support
7. Add unit tests
8. Document template variables

**Dependencies:** Jinja2 package

**Estimated Effort:** 16 hours

---

### Story 4.2: CLI Command Integration

**Description:** Add `context enhance-prompt` CLI command.

**Acceptance Criteria:**
- AC1: Command accepts prompt as argument
- AC2: Outputs enhanced prompt to stdout
- AC3: Supports --budget, --format options
- AC4: Displays latency metrics

**Technical Tasks:**
1. Add command to `src/cli/prompt.py`
2. Integrate full prompt enhancement pipeline
3. Add option parsing
4. Add output formatting (markdown, JSON)
5. Add progress indicators (Rich)
6. Add error handling
7. Add integration tests

**Dependencies:** Stories 1.5, 2.8, 3.3, 4.1

**Estimated Effort:** 12 hours

---

### Story 4.3: MCP Tool Integration

**Description:** Add MCP tool for IDE integration.

**Acceptance Criteria:**
- AC1: MCP tool `enhance_prompt` available
- AC2: Accepts prompt + user context
- AC3: Returns EnhancedPrompt object
- AC4: Integrated with existing MCP server

**Technical Tasks:**
1. Add tool to MCP server configuration
2. Implement enhance_prompt MCP handler
3. Add request/response schemas
4. Add error handling
5. Add integration tests
6. Document MCP tool usage

**Dependencies:** Story 4.2

**Estimated Effort:** 12 hours

---

## Epic 5: Conversation Memory (Week 7)

**Goal:** Store and retrieve conversation history
**Effort:** 40 hours
**Priority:** P0

### Story 5.1: PostgreSQL Schema & Storage

**Description:** Create database schema and storage layer for conversations.

**Acceptance Criteria:**
- AC1: Conversations table created with all fields
- AC2: Conversations stored on each enhancement
- AC3: Retrieval by user_id, timestamp, intent
- AC4: Storage latency <50ms

**Technical Tasks:**
1. Create Alembic migration for conversations table
2. Create `src/memory/conversation.py` module
3. Implement `ConversationStore` class
4. Add create/read/update/delete operations
5. Add indexing for performance
6. Add unit tests
7. Add integration tests

**Dependencies:** PostgreSQL, alembic

**Estimated Effort:** 16 hours

---

### Story 5.2: Qdrant Vector Indexing

**Description:** Index conversations in Qdrant for semantic search.

**Acceptance Criteria:**
- AC1: Conversations indexed on storage
- AC2: Semantic search returns similar conversations
- AC3: Search latency <100ms

**Technical Tasks:**
1. Create Qdrant collection for conversations
2. Implement conversation embedding (sentence-transformers)
3. Add indexing on storage
4. Implement semantic search
5. Add unit tests

**Dependencies:** Qdrant, Story 5.1

**Estimated Effort:** 12 hours

---

### Story 5.3: Conversation Retrieval API

**Description:** Add API to retrieve similar conversations.

**Acceptance Criteria:**
- AC1: REST endpoint GET /api/v1/memory/conversations
- AC2: CLI command `context memory conversations`
- AC3: Returns top-k similar conversations
- AC4: Includes metadata (timestamp, resolution, feedback)

**Technical Tasks:**
1. Add REST endpoint
2. Add CLI command
3. Add MCP tool
4. Add pagination support
5. Add filtering (by user, timeframe)
6. Add unit tests

**Dependencies:** Stories 5.1, 5.2

**Estimated Effort:** 12 hours

---

## Epic 6-8: Pattern, Solution, Preference Memory (Week 8-10)

Similar structure to Epic 5, covering:
- **Epic 6:** Pattern Memory (code patterns extraction and storage)
- **Epic 7:** Solution Memory (problem-solution pairs)
- **Epic 8:** User Preference Learning (coding style, library preferences)

---

## Epic 9-12: Autonomous Agents (Week 11-16)

Covering:
- **Epic 9:** Planning Agent (task decomposition)
- **Epic 10:** Coding Agent (LLM integration, code generation)
- **Epic 11:** Testing Agent (test generation and execution)
- **Epic 12:** Review & PR Agents (code review, PR creation)

---

## Epic 13-14: Multi-File Editing & Scale (Week 17-20)

Covering:
- **Epic 13:** Multi-File Editing (atomic changes, conflict detection)
- **Epic 14:** Scale Validation (test with 100k, 500k files)

---

## Summary

**Total Epics:** 14
**Total Stories:** 60+
**Total Effort:** ~300 engineer-hours (for Tier 1 epics 1-4)
**Timeline:** 6 weeks for Tier 1 (Context-Aware Prompt Enhancement)

---

**Status:** ✅ Stories Complete (Tier 1 detailed)
**Next:** Launch parallel agents for implementation
