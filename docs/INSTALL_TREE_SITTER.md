# Tree-sitter Installation Guide

This guide covers installing and configuring Tree-sitter for multi-language AST parsing in the Context project.

## Overview

Context uses Tree-sitter for parsing 7 programming languages:
- Python
- JavaScript  
- TypeScript
- Java
- C++
- Go
- Rust

## Pinned Versions

**Required versions for reproducible builds:**
- `tree_sitter==0.21.3`
- `tree_sitter_languages==1.10.2`

## Installation Methods

### Method 1: Prebuilt Language Pack (Recommended)

The easiest installation method uses prebuilt language grammars:

```bash
# Upgrade pip first
pip install --upgrade pip

# Install pinned versions
pip install "tree_sitter==0.21.3" "tree_sitter_languages==1.10.2"
```

**Poetry users:**
```bash
poetry add "tree_sitter==0.21.3" "tree_sitter_languages==1.10.2"
```

### Method 2: Build from Source (Fallback)

If prebuilt wheels are unavailable, build from source:

#### Prerequisites by OS

**Windows:**
- Install Visual Studio Build Tools 2022 with "Desktop development with C++" workload
- OR use Windows Subsystem for Linux (WSL) with Ubuntu

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake
```

**macOS:**
```bash
xcode-select --install
```

#### Build Process

1. **Install Tree-sitter CLI (optional):**
```bash
npm install -g tree-sitter-cli@0.22.5
```

2. **Clone language grammars:**
```bash
git submodule add https://github.com/tree-sitter/tree-sitter-python vendor/tree-sitter-python
git submodule add https://github.com/tree-sitter/tree-sitter-javascript vendor/tree-sitter-javascript
git submodule add https://github.com/tree-sitter/tree-sitter-typescript vendor/tree-sitter-typescript
git submodule add https://github.com/tree-sitter/tree-sitter-java vendor/tree-sitter-java
git submodule add https://github.com/tree-sitter/tree-sitter-cpp vendor/tree-sitter-cpp
git submodule add https://github.com/tree-sitter/tree-sitter-go vendor/tree-sitter-go
git submodule add https://github.com/tree-sitter/tree-sitter-rust vendor/tree-sitter-rust
```

3. **Build combined language library:**
```bash
python -c "
from tree_sitter import Language
Language.build_library(
    'src/parsing/_build/my-languages',
    [
        'vendor/tree-sitter-python',
        'vendor/tree-sitter-javascript', 
        'vendor/tree-sitter-typescript/tsx',
        'vendor/tree-sitter-typescript/typescript',
        'vendor/tree-sitter-java',
        'vendor/tree-sitter-cpp',
        'vendor/tree-sitter-go',
        'vendor/tree-sitter-rust'
    ]
)
"
```

This creates `src/parsing/_build/my-languages.dll` (Windows), `.so` (Linux), or `.dylib` (macOS).

## Verification

### Quick Test

```bash
python3 -c "
import tree_sitter
import tree_sitter_languages
from tree_sitter_languages import get_language

# Test all 7 languages
languages = ['python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'rust']
for lang in languages:
    try:
        lang_obj = get_language(lang)
        print(f'✓ {lang}: OK')
    except Exception as e:
        print(f'✗ {lang}: {e}')
"
```

### Full Integration Test

Run the smoke tests to verify parsing works:

```bash
# Run Tree-sitter smoke tests
pytest tests/integration/test_tree_sitter_smoke.py -v

# Run all parsing integration tests  
pytest tests/integration/test_parsing_integration.py -v
```

Expected output:
```
✓ All 7 languages parse successfully
✓ Non-empty ASTs generated
✓ Symbol extraction working
✓ No parsing errors or skipped tests
```

## Troubleshooting

### Common Issues

**1. "No module named 'tree_sitter'"**
- Solution: Install tree_sitter package: `pip install tree_sitter==0.21.3`

**2. "No module named 'tree_sitter_languages'"**  
- Solution: Install language pack: `pip install tree_sitter_languages==1.10.2`

**3. "externally-managed-environment" error**
- Solution: Use `--break-system-packages` flag or create virtual environment
- Development: `pip install --break-system-packages "tree_sitter==0.21.3"`

**4. Windows build failures**
- Solution A: Use WSL with Ubuntu for development
- Solution B: Install Visual Studio Build Tools 2022
- Solution C: Use prebuilt wheels if available

**5. "Language not found" errors**
- Check language name spelling (lowercase: python, javascript, etc.)
- Verify installation: `python -c "from tree_sitter_languages import get_language; get_language('python')"`

**6. Performance issues**
- Tree-sitter parsers are cached after first use
- Large files may take time on first parse
- Consider file size limits for production use

### Platform-Specific Notes

**Windows:**
- Prebuilt wheels work best on Windows 10/11
- MSVC Build Tools required for source builds
- WSL recommended for development consistency

**macOS:**
- Prebuilt wheels available for Intel and Apple Silicon
- Xcode command line tools sufficient for source builds
- No additional configuration needed

**Linux:**
- Manylinux wheels work on most distributions
- Build tools (gcc, cmake) required for source builds
- Tested on Ubuntu 20.04+ and CentOS 7+

## Integration Details

### Runtime Loading

Context uses a fallback loader (`src/parsing/ts_loader.py`) that:

1. **First**: Tries prebuilt languages from `tree_sitter_languages`
2. **Fallback**: Uses compiled library from `src/parsing/_build/`
3. **Error**: Raises exception if neither available

### Parser Caching

- Parsers are cached globally to avoid recreation overhead
- Cache cleared automatically on language loader reset
- Memory usage scales with number of languages used

### Performance Characteristics

- **First parse**: ~10-50ms (includes parser creation)
- **Subsequent parses**: ~1-10ms (cached parser)
- **Memory**: ~5-10MB per language parser
- **Concurrency**: Thread-safe after initial loading

## Version History

- **v1.0**: Initial Tree-sitter integration
- **v1.1**: Added prebuilt language pack support
- **v1.2**: Improved Windows compatibility and fallback loading

## Support

For issues with Tree-sitter installation:

1. Check this troubleshooting guide
2. Verify system prerequisites are installed
3. Test with minimal reproduction case
4. Check Tree-sitter project documentation: https://tree-sitter.github.io/

## License Compatibility

All Tree-sitter components use MIT License:
- `tree_sitter`: MIT
- `tree_sitter_languages`: MIT  
- Individual language grammars: MIT

Compatible with Context project licensing requirements.
