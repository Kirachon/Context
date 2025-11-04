# Complete MCP Server Diagnosis & Solution

## 🎯 Executive Summary

**Status**: Multiple issues identified and partially resolved

### Issues Found:

1. ✅ **FIXED**: MCP server configuration missing from `.claude.json`
2. ✅ **FIXED**: MCP stdio server not initializing Qdrant/embedding services  
3. ❌ **NEW ISSUE**: SSL/Network error downloading embedding model from HuggingFace

---

## 📊 Current System Status

### ✅ Working Components
- Docker infrastructure (all containers running and healthy)
- Qdrant vector database (accessible at localhost:6333)
- PostgreSQL, Redis, Ollama (all healthy)
- HTTP server (running on port 8000)
- Qdrant client connection (successfully connects)
- MCP server configuration (added to `.claude.json`)
- Service initialization code (added to `stdio_full_mcp.py`)

### ❌ Critical Issue Remaining
**Embedding Model Download Failure**
- **Error**: SSL/Network error when downloading from HuggingFace
- **Impact**: Cannot generate embeddings, search functionality non-operational
- **Root Cause**: Network connectivity or SSL certificate issues

---

## 🔍 Detailed Issue Analysis

### Issue #1: Missing MCP Configuration ✅ FIXED

**Problem**: `.claude.json` had NO `mcpServers` property

**Solution Applied**:
```powershell
.\scripts\configure_mcp_servers.ps1
```

**Result**: Context MCP server now configured with:
- Type: stdio
- Command: docker exec
- Timeout: 30000ms
- Status: Enabled

---

### Issue #2: Service Initialization Missing ✅ FIXED

**Problem**: `stdio_full_mcp.py` didn't initialize Qdrant or embeddings

**Solution Applied**: Modified `src/mcp_server/stdio_full_mcp.py` to add:
```python
async def initialize_services():
    """Initialize Qdrant and embedding services"""
    from src.vector_db.qdrant_client import connect_qdrant
    from src.vector_db.embeddings import initialize_embeddings
    
    await connect_qdrant()  # ✅ Works
    await initialize_embeddings()  # ❌ Fails due to SSL error
```

**Result**: 
- ✅ Qdrant connection successful
- ❌ Embedding initialization fails

---

### Issue #3: Embedding Model Download Failure ❌ ACTIVE

**Error Message**:
```
SSLError: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol
HTTPSConnectionPool(host='huggingface.co', port=443): Max retries exceeded
```

**Root Causes** (one or more):
1. **Network connectivity issues** to huggingface.co
2. **Firewall/proxy blocking** HTTPS connections
3. **SSL certificate problems** in Docker container
4. **Model not cached** - trying to download on every restart

**Impact**:
- Cannot load sentence-transformers model
- Cannot generate embeddings
- Search functionality completely non-operational
- MCP tools will fail when called

---

## 🎯 Solutions

### Solution 1: Pre-download Model (Recommended)

**Download model outside Docker and mount it:**

```powershell
# 1. Create model cache directory
mkdir -p D:\GitProjects\Context\models\sentence-transformers

# 2. Download model manually (using Python on host)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', cache_folder='D:/GitProjects/Context/models')"

# 3. Mount in docker-compose.yml
# Add to context-server service:
volumes:
  - ./models:/root/.cache/huggingface

# 4. Restart container
docker-compose -f deployment/docker/docker-compose.yml restart context-server
```

### Solution 2: Use Offline Mode

**Configure to use local model only:**

```python
# In src/vector_db/embeddings.py
self.model = SentenceTransformer(
    self.model_name,
    cache_folder="/app/models",  # Local cache
    local_files_only=True  # Don't download
)
```

### Solution 3: Fix Network/SSL Issues

**Option A: Configure proxy (if behind corporate firewall)**
```dockerfile
# In Dockerfile
ENV HTTP_PROXY=http://proxy.company.com:8080
ENV HTTPS_PROXY=http://proxy.company.com:8080
ENV NO_PROXY=localhost,127.0.0.1
```

**Option B: Disable SSL verification (NOT RECOMMENDED for production)**
```python
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

**Option C: Update CA certificates in container**
```dockerfile
RUN apt-get update && apt-get install -y ca-certificates
RUN update-ca-certificates
```

### Solution 4: Use Alternative Embedding Provider

**Switch to a simpler embedding method:**

```python
# Use basic TF-IDF or word2vec instead of sentence-transformers
# Modify src/vector_db/embeddings.py to use sklearn TfidfVectorizer
```

---

## 📋 Immediate Action Plan

### Step 1: Download Model on Host Machine (5 minutes)

```powershell
# Install sentence-transformers on host
pip install sentence-transformers

# Download model
python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('all-MiniLM-L6-v2'); print('Model downloaded to:', model._model_card_vars['model_path'])"
```

### Step 2: Copy Model to Docker Volume (2 minutes)

```powershell
# Find where model was downloaded (usually ~/.cache/huggingface or ~/.cache/torch)
# Copy to project directory
cp -r "C:\Users\preda\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2" "D:\GitProjects\Context\models\"
```

### Step 3: Update Docker Compose (2 minutes)

Edit `deployment/docker/docker-compose.yml`:
```yaml
context-server:
  volumes:
    - ./models:/root/.cache/huggingface:ro  # Mount model cache
```

### Step 4: Restart and Test (2 minutes)

```powershell
docker-compose -f deployment/docker/docker-compose.yml restart context-server
Start-Sleep -Seconds 30
docker logs context-server --tail 50 | Select-String "embedding"
```

---

## ✅ Verification Steps

### 1. Check Model Loaded
```powershell
docker logs context-server 2>&1 | Select-String "Embedding service initialized"
```

**Expected**: `✅ Embedding service initialized successfully`

### 2. Test Embedding Generation
```powershell
docker exec -i context-server python -c "from src.vector_db.embeddings import generate_embedding; import asyncio; print(asyncio.run(generate_embedding('test')))"
```

**Expected**: Array of 384 floats

### 3. Test MCP Connection
```
# In Claude Code CLI
/mcp
```

**Expected**: Context server shows "Connected ✅"

### 4. Test Search Functionality
```
# In Claude Code CLI
Use the Context MCP server to search for "FastMCP" in the codebase
```

**Expected**: Search results returned

---

## 📈 Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| MCP Configuration | ✅ Done | ✅ Done |
| Service Initialization | ✅ Done | ✅ Done |
| Qdrant Connection | ✅ Connected | ✅ Connected |
| Embedding Model | ❌ Failed | ✅ Loaded |
| Search Functionality | ❌ Non-functional | ✅ Operational |
| MCP Connection | ⚠️ Configured | ✅ Connected |

---

## 🎓 Root Cause Summary

1. **Configuration Issue**: `.claude.json` was missing `mcpServers` property
   - **Fix**: Added configuration via script

2. **Architecture Issue**: stdio MCP server didn't initialize services
   - **Fix**: Added `initialize_services()` function

3. **Network Issue**: Cannot download embedding model from HuggingFace
   - **Fix**: Need to pre-download model or fix network/SSL

---

## 💡 Key Learnings

1. **Two separate servers**: HTTP (FastAPI) and MCP (stdio) need separate initialization
2. **Model caching critical**: Don't rely on runtime downloads in production
3. **Network dependencies**: Embedding models require internet or local cache
4. **SSL in Docker**: Container SSL certificates may differ from host

---

## 📞 Next Steps

**Immediate** (Required to make system functional):
1. Download embedding model on host machine
2. Mount model cache in Docker container
3. Restart container and verify

**Short-term** (Improve reliability):
1. Add model to Docker image build process
2. Implement health checks for embedding service
3. Add fallback embedding methods

**Long-term** (Production readiness):
1. Optimize model loading time
2. Implement model versioning
3. Add monitoring for embedding generation
4. Consider using smaller/faster models

---

**Status**: Partially resolved - awaiting model download solution  
**Blocking Issue**: SSL/Network error downloading embedding model  
**Recommended Action**: Pre-download model and mount in container  
**ETA to Full Resolution**: 10-15 minutes

