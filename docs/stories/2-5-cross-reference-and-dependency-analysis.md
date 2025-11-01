# Story 2.5: Cross-Reference and Dependency Analysis

Status: ready-for-dev

## Story

As a developer understanding code relationships,
I want Context to identify function calls, imports, and dependencies,
So that I can understand how code components interact and depend on each other.

## Acceptance Criteria

1. Dependency mapping identifies function calls, imports, inheritance, and implementation relationships
2. Cross-reference analysis shows where functions/classes are defined and used
3. Impact analysis predicts effects of code changes (transitive dependents)
4. Circular dependency detection prevents infinite loops in analysis
5. Visualization-ready outputs (graph structures) for future tools (text/JSON)

## Tasks / Subtasks

- Build dependency analyzer service (graph construction, refs, impact, cycles)
- Reuse CrossLanguageAnalyzer where possible; avoid duplication
- Add MCP tools for dependency queries (follow-up)
- Write unit tests for graph building, cycles, and impact analysis
- Documentation and examples

## Integration Points

- src/analysis/cross_language.py (patterns + basic deps)
- src/parsing/models.py (ParseResult, SymbolInfo, ClassInfo, ImportInfo)
- src/vector_db/ast_store.py (future: reading stored AST metadata)

## Deliverables

- Dependency analyzer module
- Unit tests covering acceptance criteria
- Story documentation/context

