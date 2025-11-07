# Quick Start: Google Embeddings Setup

## 🚀 5-Minute Setup

### Prerequisites
- ✅ Docker containers running (Qdrant, context-server)
- ✅ Google API key for Gemini API

### Get Your API Key
1. Visit: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key (starts with `AIza...`)

### Run Setup Script
```powershell
.\scripts\setup_google_embeddings.ps1
```

**That's it!** The script will:
1. Configure your API key
2. Update embeddings provider to Google
3. Recreate Qdrant collection (768 dimensions)
4. Restart the container
5. Verify everything works

### Verify Setup
```powershell
# Check health
curl http://localhost:8000/health | ConvertFrom-Json

# Check logs
docker logs context-server --tail 50 | Select-String "Google"
```

Expected output:
```
✅ Google embeddings initialized (dim=768)
```

### Test in Claude Code CLI
1. Restart Claude Code CLI
2. Run: `/mcp`
3. Should see: "Context: Connected ✅"
4. Test search functionality

---

## 🎯 Why Google Embeddings?

### Problem We're Solving
The local model download was failing with SSL errors:
```
SSLEOFError: EOF occurred in violation of protocol
HTTPSConnectionPool(host='huggingface.co', port=443): Max retries exceeded
```

### Benefits of Google Embeddings
- ✅ **No downloads** - No local model needed
- ✅ **No SSL issues** - Direct API calls
- ✅ **Better quality** - Google's latest embedding model
- ✅ **Faster startup** - No 12-second model loading
- ✅ **Less memory** - No 500MB model in RAM
- ✅ **768 dimensions** - More detailed embeddings (vs 384)

---

## 📋 What Changed

### Configuration
```bash
# Before
EMBEDDINGS_PROVIDER=sentence-transformers
QDRANT_VECTOR_SIZE=384

# After
EMBEDDINGS_PROVIDER=google
GOOGLE_API_KEY=AIza...
QDRANT_VECTOR_SIZE=768
```

### Architecture
```
Before: Container → Download Model → Load Model → Generate Embeddings
After:  Container → Google API → Generate Embeddings
```

---

## 🔧 Manual Setup (If Script Fails)

### 1. Edit `.env` file
```bash
# Edit: deployment/docker/.env
EMBEDDINGS_PROVIDER=google
GOOGLE_API_KEY=AIza_your_key_here
GOOGLE_EMBEDDING_MODEL=text-embedding-004
QDRANT_VECTOR_SIZE=768
```

### 2. Recreate Qdrant Collection
```powershell
# Delete old collection
Invoke-RestMethod -Uri "http://localhost:6333/collections/context_vectors" -Method Delete

# Create new collection (768 dimensions)
$body = @{
    vectors = @{
        size = 768
        distance = "Cosine"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:6333/collections/context_vectors" -Method Put -Body $body -ContentType "application/json"
```

### 3. Restart Container
```powershell
docker-compose -f deployment/docker/docker-compose.yml restart context-server
```

---

## 🐛 Troubleshooting

### "GOOGLE_API_KEY environment variable required"
**Fix**: Make sure API key is in `.env` and container is restarted

### "Dimension mismatch" error
**Fix**: Recreate Qdrant collection with 768 dimensions (run setup script)

### "Invalid API key"
**Fix**: Verify key at https://makersuite.google.com/app/apikey

### Still seeing SSL errors
**Fix**: Make sure `EMBEDDINGS_PROVIDER=google` in `.env` file

---

## 📊 Cost & Limits

### Google Gemini API - Free Tier
- **Rate Limit**: 1,500 requests per day
- **Cost**: Free for moderate use
- **Upgrade**: Available if needed

### Typical Usage
- **Initial indexing**: ~100-500 requests (one-time)
- **Daily searches**: ~10-50 requests
- **Well within free tier** for most projects

---

## 🔄 Switching Back to Local Models

If you need to switch back:

```powershell
# Edit .env
EMBEDDINGS_PROVIDER=sentence-transformers
QDRANT_VECTOR_SIZE=384

# Recreate collection (384 dimensions)
# Delete and recreate as shown above

# Restart container
docker-compose -f deployment/docker/docker-compose.yml restart context-server
```

---

## ✅ Success Checklist

- [ ] Got Google API key from https://makersuite.google.com/app/apikey
- [ ] Ran `.\scripts\setup_google_embeddings.ps1`
- [ ] Health endpoint shows `"provider": "google"`
- [ ] Logs show "✅ Google embeddings initialized"
- [ ] Restarted Claude Code CLI
- [ ] `/mcp` shows "Context: Connected ✅"
- [ ] Search functionality works

---

## 📚 More Information

- **Full Documentation**: `GOOGLE_EMBEDDINGS_SOLUTION.md`
- **API Reference**: https://ai.google.dev/api/embeddings
- **Get API Key**: https://makersuite.google.com/app/apikey

---

**Ready to start?** Run: `.\scripts\setup_google_embeddings.ps1`

