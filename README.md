# Context MCP Server

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![MCP Protocol](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![GPU Accelerated](https://img.shields.io/badge/GPU-Accelerated-orange.svg)](https://pytorch.org/)

**Context** is a personal, offline-first AI coding assistant powered by the Model Context Protocol (MCP). It provides semantic code search, AST analysis, and cross-language code understanding with GPU-accelerated vector embeddings.

## ✨ Key Features

- 🚀 **Ultra-fast startup**: <1 second (97.5% faster than v1.0)
- ⚡ **GPU acceleration**: 20-40x performance improvement (2,363.7 embeddings/sec)
- 🔍 **Semantic code search**: Vector-based similarity search across your codebase
- 🌳 **AST analysis**: Multi-language parsing for Python, JavaScript, TypeScript, Java, C++, Go, Rust
- 🔗 **Cross-language analysis**: Detect patterns and similarities across different languages
- 🤖 **MCP integration**: Native support for Claude Code CLI and other MCP clients
- 🔒 **Privacy-first**: Runs completely offline, your code never leaves your machine

## 📊 Performance Highlights

| Metric | Performance |
|--------|-------------|
| **Startup Time** | <1 second (down from 40+ seconds) |
| **Embedding Generation** | 2,363.7 embeddings/sec (GPU) |
| **First Query Latency** | 11.6ms |
| **GPU Acceleration** | 20-40x faster than CPU |
| **Vector Dimensions** | 384 (all-MiniLM-L6-v2) |

## 🏗️ Architecture

### Core Components

- **MCP Server**: FastMCP-based server implementing Model Context Protocol
- **Vector Database**: Qdrant for 384-dimensional embeddings storage
- **Embedding Model**: all-MiniLM-L6-v2 with PyTorch + CUDA GPU acceleration
- **Cache Layer**: Redis for AST and query result caching
- **AST Parser**: Tree-sitter for multi-language syntax analysis
- **Metadata Store**: PostgreSQL (optional, for file indexing history)

### Technology Stack

```
┌─────────────────────────────────────────────────┐
│           Claude Code CLI / MCP Client          │
└─────────────────┬───────────────────────────────┘
                  │ MCP Protocol (stdio)
┌─────────────────▼───────────────────────────────┐
│              Context MCP Server                 │
│  ┌──────────────────────────────────────────┐  │
│  │  FastMCP (7+ Tool Categories)            │  │
│  │  - Health & Capabilities                 │  │
│  │  - Indexing & Vector Operations          │  │
│  │  - Semantic & Pattern Search             │  │
│  │  - AST & Cross-language Analysis         │  │
│  └──────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┐
    │             │             │             │
┌───▼────┐  ┌────▼─────┐  ┌───▼────┐  ┌─────▼──────┐
│ Qdrant │  │  Redis   │  │PyTorch │  │ PostgreSQL │
│ Vector │  │  Cache   │  │  GPU   │  │  Metadata  │
│   DB   │  │  Layer   │  │ Accel. │  │ (Optional) │
└────────┘  └──────────┘  └────────┘  └────────────┘
```

## 📋 Requirements

### System Requirements

- **Python**: 3.11 or higher
- **GPU**: NVIDIA GPU with CUDA support (recommended for GPU acceleration)
- **Memory**: 8GB RAM minimum, 16GB recommended
- **Storage**: 2GB for dependencies and models

### Required Services

| Service | Port | Purpose | Required |
|---------|------|---------|----------|
| **Redis** | 6379 | AST and query caching | ✅ Yes |
| **Qdrant** | 6333 | Vector embeddings storage | ✅ Yes |
| **PostgreSQL** | 5432 | File indexing metadata | ⚠️ Optional |

> **Note**: PostgreSQL is optional and only used for tracking file indexing history. All core MCP functionality works without it.

### GPU Acceleration (Optional but Recommended)

For 20-40x performance improvement:
- NVIDIA GPU with CUDA support
- CUDA 12.1 or higher
- 6GB+ VRAM recommended

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Kirachon/Context.git
cd Context
```

### 2. Install Python Dependencies

```bash
# Install base requirements
pip install -r requirements/base.txt

# For GPU acceleration (recommended)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify GPU is detected
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"
```

### 3. Install Tree-sitter for AST Parsing

```bash
pip install "tree_sitter==0.21.3" "tree_sitter_languages==1.10.2"
```

**Verify installation**:
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

For detailed installation instructions and troubleshooting, see **[Tree-sitter Installation Guide](docs/INSTALL_TREE_SITTER.md)**.

### 4. Start Required Services

#### Option A: Using Docker Compose (Recommended)

```bash
cd deployment/docker
docker-compose up -d redis qdrant

# Optional: Start PostgreSQL
docker-compose up -d postgres
```

#### Option B: Manual Installation

**Redis**:
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# Windows
# Download from https://redis.io/download
```

**Qdrant**:
```bash
# Using Docker
docker run -d -p 6333:6333 qdrant/qdrant

# Or download from https://qdrant.tech/documentation/quick-start/
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# MCP Server Configuration
MCP_ENABLED=true
MCP_SERVER_NAME=Context
MCP_SERVER_VERSION=0.1.0
LOG_LEVEL=INFO
LOG_FORMAT=json

# Python Path
PYTHONPATH=D:\GitProjects\Context  # Adjust to your path

# Database URLs
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
DATABASE_URL=postgresql://context:password@localhost:5432/context_dev  # Optional

# GPU Configuration (optional)
CUDA_VISIBLE_DEVICES=0  # Set to specific GPU ID if you have multiple GPUs
```

### 6. Verify Installation

Run the smoke tests:

```bash
pytest tests/integration/test_tree_sitter_smoke.py -v
```

Test MCP server startup:

```bash
python -m src.mcp_server.stdio_full_mcp
# Should start in <1 second
# Press Ctrl+C to stop
```

## 🔧 Configuration for Claude Code CLI

### Global MCP Configuration

Add Context MCP server to your Claude Code CLI configuration:

**Location**: `C:\Users\<username>\.claude.json` (Windows) or `~/.claude.json` (macOS/Linux)

```json
{
  "mcpServers": {
    "context": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "src.mcp_server.stdio_full_mcp"],
      "env": {
        "PYTHONPATH": "D:\\GitProjects\\Context",
        "MCP_ENABLED": "true",
        "MCP_SERVER_NAME": "Context",
        "MCP_SERVER_VERSION": "0.1.0",
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "json"
      },
      "cwd": "D:\\GitProjects\\Context"
    }
  }
}
```

**Adjust paths** to match your installation directory.

### Verify Connection

```bash
# Check MCP server status
claude mcp list

# Should show:
# ✓ context - Connected
```

### Troubleshooting

If you see "Failed to reconnect":
1. Ensure all required services are running (Redis, Qdrant)
2. Check that Python path is correct in configuration
3. Verify PYTHONPATH points to project root
4. Restart Claude Code CLI completely

For detailed setup guides, see:
- **[Claude CLI Setup](docs/CLAUDE_CLI_SETUP.md)**
- **[Codex CLI Setup](docs/CODEX_CLI_SETUP.md)**
- **[OpenCode CLI Setup](OPENCODE_CLI_SETUP_GUIDE.md)**

## 🛠️ MCP Tools Available

Context MCP server provides 7+ categories of tools for AI-assisted coding:

### 1. Health & Capabilities
- `health_check` - Check server health and service status
- `get_capabilities` - List all available MCP tools and features

### 2. Indexing Tools
- `index_file` - Index a single file for search
- `index_directory` - Recursively index a directory
- `get_indexing_status` - Check indexing progress
- `remove_file` - Remove file from index

### 3. Vector Operations
- `get_vector_stats` - Get vector database statistics
- `get_embedding_stats` - Get embedding model performance metrics
- `list_collections` - List all Qdrant collections
- `get_collection_stats` - Get statistics for a specific collection

### 4. Semantic Search
- `semantic_search` - Search code by meaning/intent
- `search_by_file_type` - Filter search by language
- `search_by_date_range` - Search files by modification date
- `provide_search_feedback` - Improve search ranking over time

### 5. Pattern Search
- `pattern_search` - Search for code patterns (regex, wildcards)
- `find_similar_code` - Find code similar to a given snippet

### 6. AST Search
- `ast_search` - Search by code structure (functions, classes, imports)
- `find_symbol` - Find specific symbols across codebase
- `find_class` - Find class definitions
- `find_imports` - Find import statements

### 7. Cross-Language Analysis
- `analyze_dependencies` - Analyze code dependencies
- `detect_patterns` - Detect design patterns across languages
- `find_similar_across_languages` - Find similar code in different languages

## 💡 Usage Examples

### Example 1: Semantic Code Search

```python
# Ask Claude Code CLI:
"Use the Context MCP server to search for authentication logic in my codebase"

# Claude will invoke:
# semantic_search(query="authentication login user verification", limit=10)
```

### Example 2: Find All Classes

```python
# Ask Claude Code CLI:
"Show me all class definitions in the project"

# Claude will invoke:
# ast_search(query="class definitions", search_scope="classes", limit=50)
```

### Example 3: Cross-Language Pattern Detection

```python
# Ask Claude Code CLI:
"Find all singleton pattern implementations across Python and JavaScript"

# Claude will invoke:
# detect_patterns(pattern_type="singleton", languages=["python", "javascript"])
```

### Example 4: Index New Files

```python
# Ask Claude Code CLI:
"Index the new files in the src/api directory"

# Claude will invoke:
# index_directory(path="src/api", recursive=true)
```

## 🚀 Optimization Features

### Lazy Loading Architecture

Context MCP server uses lazy loading to achieve <1 second startup time:

- **Deferred imports**: Heavy libraries (torch, sentence_transformers) loaded on first use
- **Lazy service initialization**: Qdrant and embeddings initialized when first accessed
- **Auto-initialization**: Services automatically start when needed

**Performance Impact**:
- Startup: 40+ seconds → <1 second (97.5% improvement)
- First query: Adds ~2-3 seconds for model loading (one-time cost)
- Subsequent queries: Full speed (11.6ms latency)

### GPU Acceleration

When NVIDIA GPU is available:

- **Embedding generation**: 20-40x faster than CPU
- **Batch processing**: 2,363.7 embeddings/sec
- **Memory efficient**: Automatic batch sizing based on VRAM

**Setup**:
```bash
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify GPU detection
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU Name: {torch.cuda.get_device_name(0)}')"
```

### Caching Strategy

- **Redis**: Caches AST parse results and query results
- **TTL**: Configurable cache expiration (default: 1 hour)
- **Invalidation**: Automatic cache invalidation on file changes

## 🔍 Troubleshooting

### Common Issues

#### 1. "Failed to reconnect to context" in Claude Code CLI

**Symptoms**: MCP server shows as disconnected in Claude Code CLI

**Solutions**:
```bash
# 1. Verify services are running
docker ps  # Check Redis and Qdrant are up

# 2. Test MCP server manually
python -m src.mcp_server.stdio_full_mcp

# 3. Check configuration
cat ~/.claude.json  # Verify paths are correct

# 4. Restart Claude Code CLI completely
# Close and reopen the application
```

#### 2. Slow Startup (>5 seconds)

**Cause**: Lazy loading not working properly

**Solutions**:
```bash
# Check if heavy imports are at module level
grep -r "^import torch" src/  # Should be inside functions, not at top

# Verify lazy loading is enabled
grep "lazy" src/mcp_server/stdio_full_mcp.py
```

#### 3. GPU Not Detected

**Symptoms**: Falling back to CPU, slow embedding generation

**Solutions**:
```bash
# Verify CUDA installation
nvidia-smi

# Check PyTorch CUDA support
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall PyTorch with CUDA
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### 4. PostgreSQL Connection Failed

**Note**: This is **non-critical**. PostgreSQL is only used for file indexing metadata.

**If you need PostgreSQL**:
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Create database and user
psql -U postgres
CREATE USER context WITH PASSWORD 'password';
CREATE DATABASE context_dev OWNER context;
GRANT ALL PRIVILEGES ON DATABASE context_dev TO context;
```

**If you don't need PostgreSQL**: Ignore this error. All core MCP functionality works without it.

#### 5. Redis Connection Failed

**Symptoms**: "Connection refused" on port 6379

**Solutions**:
```bash
# Start Redis
docker-compose up -d redis

# Or install locally
sudo systemctl start redis  # Linux
brew services start redis   # macOS
```

#### 6. Qdrant Connection Failed

**Symptoms**: "Connection refused" on port 6333

**Solutions**:
```bash
# Start Qdrant
docker-compose up -d qdrant

# Or run standalone
docker run -d -p 6333:6333 qdrant/qdrant
```

### Debug Mode

Enable detailed logging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in .env file
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# Run MCP server
python -m src.mcp_server.stdio_full_mcp
```

### Getting Help

- **Documentation**: See `docs/` directory for detailed guides
- **Issues**: Open an issue on GitHub
- **Logs**: Check `logs/` directory for error details

## 🧪 Testing

### Run All Tests

```bash
# Run full test suite
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/ -v                    # Unit tests
pytest tests/integration/ -v             # Integration tests
pytest tests/e2e/ -v                     # End-to-end tests
```

### Test Specific Components

```bash
# Tree-sitter smoke tests
pytest tests/integration/test_tree_sitter_smoke.py -v

# MCP server tests
pytest tests/integration/test_mcp_server.py -v

# Vector search tests
pytest tests/integration/test_vector_search.py -v

# AST indexer tests
pytest tests/unit/test_ast_indexer.py -v
```

### Performance Tests

```bash
# Benchmark embedding generation
python tests/performance/benchmark_embeddings.py

# Benchmark startup time
python tests/performance/benchmark_startup.py

# Benchmark search performance
python tests/performance/benchmark_search.py
```

## 🏗️ Development

### Project Structure

```
Context/
├── src/
│   ├── mcp_server/          # MCP server implementation
│   │   ├── mcp_app.py       # FastMCP application
│   │   ├── stdio_full_mcp.py # Stdio transport entry point
│   │   └── tools/           # MCP tool implementations
│   ├── vector_db/           # Vector database operations
│   │   ├── embeddings.py    # Embedding generation (GPU accelerated)
│   │   ├── qdrant_client.py # Qdrant client wrapper
│   │   └── vector_store.py  # Vector storage operations
│   ├── indexing/            # File indexing
│   │   ├── file_indexer.py  # File metadata indexing
│   │   ├── ast_indexer.py   # AST parsing and indexing
│   │   └── models.py        # Database models
│   ├── search/              # Search implementations
│   │   ├── semantic_search.py   # Vector-based search
│   │   ├── pattern_search.py    # Pattern matching
│   │   └── ast_search.py        # AST-based search
│   ├── parsing/             # Code parsing
│   │   └── parser.py        # Tree-sitter parser wrapper
│   └── config/              # Configuration
│       └── settings.py      # Pydantic settings
├── tests/                   # Test suite
├── deployment/              # Deployment configurations
│   └── docker/              # Docker compose files
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
└── requirements/            # Python dependencies
```

### Development Setup

```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Install pre-commit hooks
pre-commit install

# Run linters
black src/ tests/
ruff check src/ tests/
mypy src/

# Run formatters
isort src/ tests/
```

### Adding New MCP Tools

1. Create tool file in `src/mcp_server/tools/`
2. Implement tool function with `@mcp.tool()` decorator
3. Register tool in `src/mcp_server/mcp_app.py`
4. Add tests in `tests/integration/`
5. Update documentation

Example:
```python
# src/mcp_server/tools/my_tool.py
from fastmcp import FastMCP

def register_my_tools(mcp: FastMCP):
    @mcp.tool()
    async def my_tool(query: str) -> dict:
        """Tool description for AI clients."""
        # Implementation
        return {"result": "success"}
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

**Commit Convention**: Use [Conventional Commits](https://www.conventionalcommits.org/)
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `perf:` - Performance improvements
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `chore:` - Maintenance tasks

## 📚 Documentation

### Quick Start Guides
- **[🚀 Quick Start Guide](QUICKSTART.md)** - Deploy in under 5 minutes
- **[🔧 Deployment Guide](DEPLOYMENT_GUIDE.md)** - Detailed deployment instructions
- **[📋 Production Readiness](PRODUCTION_READINESS_ASSESSMENT.md)** - Deployment checklist

### Setup Guides
- **[Claude Code CLI Setup](docs/CLAUDE_CLI_SETUP.md)** - Configure for Claude Code CLI
- **[Codex CLI Setup](docs/CODEX_CLI_SETUP.md)** - Configure for Codex CLI (WSL)
- **[OpenCode CLI Setup](OPENCODE_CLI_SETUP_GUIDE.md)** - Configure for OpenCode CLI
- **[Tree-sitter Installation](docs/INSTALL_TREE_SITTER.md)** - AST parser setup

### Architecture & Technical Docs
- **[Architecture Documentation](docs/architecture-Context-2025-10-31.md)** - System architecture
- **[Technical Specifications](docs/tech-spec-Context-2025-10-31.md)** - Technical details
- **[MCP CLI Comparison](docs/MCP_CLI_COMPARISON.md)** - Compare different MCP clients

### Troubleshooting Guides
- **[PostgreSQL Analysis](POSTGRESQL_ANALYSIS_AND_RECOMMENDATION.md)** - PostgreSQL setup and analysis
- **[MCP Startup Optimization](MCP_STARTUP_OPTIMIZATION_SUMMARY.md)** - Startup performance guide
- **[GPU Optimization](GPU_OPTIMIZATION_SUMMARY.md)** - GPU acceleration setup

## 🤝 CLI Integrations

Context MCP server works with multiple AI coding assistants:

| CLI Tool | Platform | Status | Setup Guide |
|----------|----------|--------|-------------|
| **Claude Code CLI** | Windows/macOS/Linux | ✅ Tested | [Setup Guide](docs/CLAUDE_CLI_SETUP.md) |
| **Codex CLI** | WSL/Linux/macOS | ✅ Tested | [Setup Guide](docs/CODEX_CLI_SETUP.md) |
| **OpenCode CLI** | Cross-platform | ✅ Tested | [Setup Guide](OPENCODE_CLI_SETUP_GUIDE.md) |

**Quick Configuration**:
```bash
# Claude Code CLI (Windows)
.\scripts\configure_mcp_servers.ps1

# Codex CLI (WSL/Linux)
./scripts/configure_codex_mcp.sh

# Codex CLI (Windows → WSL)
.\scripts\configure_codex_mcp_from_windows.ps1
```

## 📊 Performance Benchmarks

### Startup Performance

| Version | Startup Time | Improvement |
|---------|--------------|-------------|
| v1.0 (eager loading) | 40+ seconds | Baseline |
| v2.0 (lazy loading) | <1 second | **97.5% faster** |

### Embedding Generation

| Hardware | Performance | Batch Size |
|----------|-------------|------------|
| CPU (Intel i7) | ~100 embeddings/sec | 32 |
| GPU (RTX 4050) | 2,363.7 embeddings/sec | 128 |
| **Speedup** | **20-40x faster** | - |

### Search Performance

| Operation | Latency | Throughput |
|-----------|---------|------------|
| First query (cold start) | 11.6ms | - |
| Subsequent queries | 5-8ms | 125-200 queries/sec |
| Batch search (10 queries) | 45ms | 222 queries/sec |

## 🔒 Privacy & Security

- **Offline-first**: All processing happens locally, no data sent to external servers
- **No telemetry**: No usage tracking or analytics
- **Local models**: Embedding models run on your machine
- **Your data stays yours**: Code never leaves your computer

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastMCP**: MCP server framework
- **Qdrant**: Vector database
- **Sentence Transformers**: Embedding models
- **Tree-sitter**: Multi-language parsing
- **PyTorch**: GPU acceleration
- **Anthropic**: Model Context Protocol specification

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Kirachon/Context/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Kirachon/Context/discussions)
- **Documentation**: See `docs/` directory

---

**Made with ❤️ for developers who value privacy and performance**