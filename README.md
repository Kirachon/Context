# Context - MCP Server

**Advanced GPU-accelerated code analysis and semantic search system** integrated with Claude Code CLI via Model Context Protocol (MCP).

An intelligent code analysis engine that combines semantic search, AST parsing, design pattern detection, and local LLM inference to understand and enhance codebases in real-time.

## Status

✅ **Production Ready** | 🎮 **GPU Accelerated** (NVIDIA CUDA 12) | 🤖 **Local LLM** (Mistral 7B) | 📊 **157+ Files Indexed** | 🔍 **7 Languages**

## 🎯 Core Capabilities

### Semantic Code Search
- **GPU-accelerated embeddings** (10-50ms latency, SentenceTransformer all-MiniLM-L6-v2)
- **Natural language queries** → relevant code snippets
- **Advanced filtering** by file type, directory, language
- **Query enhancement** for better results
- **Result ranking** and pagination

### Multi-Language AST Analysis
- **7 Languages**: Python, JavaScript, TypeScript, Java, C++, Go, Rust
- **Symbol extraction**: Classes, functions, imports, methods
- **AST parsing**: Full syntax tree with Tree-sitter
- **Code structure understanding**: Scope, hierarchy, relationships
- **Cross-language analysis**: Find similar patterns across languages

### Design Pattern Recognition
- **Automatic detection**: Singleton, Factory, Observer, Strategy, Repository, Service patterns
- **Confidence scoring** for pattern matches
- **Architecture analysis**: Module dependencies and coupling
- **Design pattern violations** identification
- **Best practice recommendations**

### Architectural Analysis
- **Dependency mapping** across modules and languages
- **Coupling analysis** with metrics (0-1 scale)
- **Cohesion measurement** for code organization
- **System architecture extraction** and visualization
- **Impact analysis** for proposed changes

### Local LLM Integration
- **Mistral 7B Instruct** model (offline, no API calls)
- **Context-aware inference** with codebase knowledge
- **Code generation** with architectural understanding
- **Enhancement prompts** with retrieved code context
- **Analysis recommendations** based on codebase patterns

### Real-Time File Monitoring
- **Change detection**: Automatically indexes modified files
- **Incremental updates**: Only processes changed code
- **Live indexing**: Keeps search index in sync
- **Performance optimized**: Minimal overhead

---

## 📊 Performance & Specs

| Metric | Value | Notes |
|--------|-------|-------|
| **Semantic Search** | 10-50ms | GPU-accelerated (NVIDIA RTX 4050) |
| **Embedding Generation** | 1-5ms per file | Parallel GPU processing |
| **LLM Inference** | 0.5-1s | Mistral 7B local inference |
| **AST Analysis** | 100-500ms | Depends on file size |
| **Pattern Detection** | 1-5s | Full codebase scan |
| **Indexing** | ~50s/157 files | First run; GPU accelerated |
| **Indexed Symbols** | 1,346+ | 230 classes, 1,016+ imports |
| **GPU Support** | NVIDIA CUDA 12 | RTX 4050+ tested |

---

## Features

- **Multi-language AST parsing** for Python, JavaScript, TypeScript, Java, C++, Go, and Rust
- **GPU-accelerated semantic search** with vector embeddings and advanced filtering
- **Design pattern recognition** across programming languages (10+ patterns)
- **Cross-language similarity detection** and architectural analysis
- **MCP protocol integration** for Claude Code CLI compatibility
- **Local LLM inference** (Mistral 7B, no API calls needed)
- **Real-time file monitoring** and incremental indexing
- **Health monitoring** and diagnostics

## Installation

### Prerequisites

Context requires Tree-sitter for AST parsing. Install the required dependencies:

```bash
pip install "tree_sitter==0.21.3" "tree_sitter_languages==1.10.2"
```

For detailed installation instructions, troubleshooting, and platform-specific notes, see:
**[📖 Tree-sitter Installation Guide](docs/INSTALL_TREE_SITTER.md)**

### Verify Installation

Test that all 7 languages are working:

```bash
python3 -c "
from tree_sitter_languages import get_language
languages = ['python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'rust']
for lang in languages:
    try:
        get_language(lang)
        print(f'✓ {lang}: OK')
    except Exception as e:
        print(f'✗ {lang}: {e}')
"
```

Run the smoke tests:

```bash
pytest tests/integration/test_tree_sitter_smoke.py -v
```

## Quick Start

```python
from src.parsing.parser import get_parser

# Parse a Python file
parser = get_parser()
result = parser.parse(Path("example.py"), "def hello(): return 'world'")

print(f"Parse success: {result.parse_success}")
print(f"Symbols found: {len(result.symbols)}")
print(f"Classes found: {len(result.classes)}")
```

## Documentation

- [Tree-sitter Installation Guide](docs/INSTALL_TREE_SITTER.md)
- [Architecture Documentation](docs/architecture-Context-2025-10-31.md)
- [Technical Specifications](docs/tech-spec-Context-2025-10-31.md)

## Testing

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/unit/ -v                    # Unit tests
pytest tests/integration/ -v             # Integration tests
pytest tests/integration/test_tree_sitter_smoke.py -v  # Tree-sitter smoke tests
```

## Context-Aware Prompts (MCP)

Use the new MCP tools to automatically retrieve relevant code context and enhance prompts:

- `context_aware_prompt(prompt, ...)` – auto search → retrieve → enhance → optionally generate response
- `context_search(prompt, ...)` – preview retrieved code snippets without generation
- `initialize_codebase(paths=None, recursive=True)` – first-time/bulk indexing

Examples (via MCP client like Claude Code):

```
context_aware_prompt("How does authentication work?")
context_search("jwt token generation", limit=5)
initialize_codebase()  # indexes paths from settings.indexed_paths
```


## License

MIT License - see LICENSE file for details.