# Context

Advanced code analysis and semantic search system with multi-language AST parsing.

## Features

- **Multi-language AST parsing** for Python, JavaScript, TypeScript, Java, C++, Go, and Rust
- **Semantic code search** with vector embeddings and advanced filtering
- **Design pattern recognition** across programming languages
- **Cross-language similarity detection** and architectural analysis
- **MCP protocol integration** for Claude Code CLI compatibility

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

## License

MIT License - see LICENSE file for details.