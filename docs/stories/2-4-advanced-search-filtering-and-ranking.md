# Story 2.4: Advanced Search Filtering and Ranking

Status: ready-for-dev

Note: In epics.md this appears as Story 2.3. We follow the BMAD execution sequence where 2.3 (Enhanced Embeddings) is complete and this story proceeds as 2.4.

## Story

As a developer refining search results,
I want sophisticated filtering and ranking options,
So that I can quickly find the most relevant code patterns and examples.

## Acceptance Criteria

1. Advanced filtering by file type, directory, author, and modification date
2. Semantic similarity ranking with configurable relevance weights
3. Hybrid search combining semantic and keyword matching
4. Result diversity to avoid returning similar code from same files
5. User feedback integration improves ranking quality over time

## Tasks / Subtasks

- Extend SearchRequest and SearchFilters to support authors and date-range filters
- Implement author and modification date filtering
- Add keyword matching and combine with semantic scores (hybrid)
- Enhance RankingService with configurable weights (similarity, keyword, size, type, freshness)
- Add simple feedback system to adjust ranking over time
- Update MCP search tools to expose new options and ranking controls
- Write unit and integration tests (target 15–20 tests)

## Integration Points

- Story 2.1 (AST analysis): Optional metadata enrichment if needed
- Story 2.2 (Real-time): Ensure filtering & ranking work with incremental updates
- Story 2.3 (Embeddings): Leverage enriched embeddings; hybrid ranking must remain backward compatible

## Performance Targets

- End-to-end search remains < 400ms average on 10k files (local vector store)
- Ranking computation adds < 10ms per 100 results
- Filtering is linear in result count with negligible overhead

## Deliverables

- Advanced filtering service updates
- Ranking engine with configurable weights and feedback integration
- Hybrid search enhancements
- MCP tools for search configuration and feedback
- Comprehensive tests and documentation

