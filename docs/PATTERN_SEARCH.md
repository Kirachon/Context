## Pattern Search (Production)

Production-grade Tree-sitter pattern search with multi-language support and caching.

### Supported Languages
- Python, JavaScript, TypeScript, Java, C++, Go, Rust

### Key Patterns (examples)
- Python: decorator_patterns, repository_crud, factory_methods
- JavaScript: async_functions (try + await), factory_classes (method returns new instance), promise_chains
- TypeScript: interface_implementations, generic_functions
- Java: repository_pattern, singleton_pattern (getInstance)
- C++: raii_pattern
- Go: error_handling
- Rust: result_patterns, trait_implementations

### Usage via MCP Tools
- pattern_search_directory
  - params: directory_path, patterns?, languages?, include_globs?, exclude_globs?, max_files?
- pattern_search_code
  - params: language, code, patterns?

### Examples
- Search directory for Python repo CRUD:
  - pattern_search_directory(directory_path="src", patterns=["repository_crud"], languages=["python"])

- Search a snippet for JS factory methods:
  - pattern_search_code(language="javascript", code="class A { create(){ return new B(); } }", patterns=["factory_classes"])

### Notes
- Queries avoid invalid node types (async/static). Async detection is proxied by finding `await` inside try-block for JS and try-block for Python.
- Engine caches compiled queries and results for performance.



### Embedding Provider (Feature Flag)
- settings.embeddings_provider: 'sentence-transformers' (default) or 'unixcoder'
- settings.unixcoder_enabled: false by default; set true to enable
- The embedding service will fall back to sentence-transformers unless UniXcoder is explicitly enabled.
