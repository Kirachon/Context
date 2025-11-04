# Embedding Service Initialization Fix

## Problem Summary

The indexing system was reporting "Model not loaded" for the Google embeddings provider (text-embedding-004), even though the service was successfully initializing. This prevented 8 queued indexing tasks from being processed.

## Root Cause Analysis

### Issue 1: Incorrect Status Reporting
The `get_stats()` method in `src/vector_db/embeddings.py` was checking `self.model is not None` to determine if the service was loaded. However, for Google embeddings, the provider is stored in `self.google_provider`, not `self.model`. This caused the status endpoint to incorrectly report "Model not loaded".

**Before:**
```python
def get_stats(self) -> Dict[str, Any]:
    return {
        "model_name": self.model_name,
        "embedding_dim": self.embedding_dim,
        "model_loaded": self.model is not None,  # ❌ Wrong for Google provider
    }
```

**After:**
```python
def get_stats(self) -> Dict[str, Any]:
    is_loaded = self.model is not None or self.google_provider is not None
    return {
        "provider": self.provider,
        "model_name": self.model_name,
        "embedding_dim": self.embedding_dim,
        "model_loaded": is_loaded,  # ✅ Checks both providers
    }
```

### Issue 2: Batch Embeddings Not Supporting Google Provider
The `generate_batch_embeddings()` method was checking `if not self.model:` which would fail for Google embeddings. This prevented the indexing queue from processing files.

**Before:**
```python
async def generate_batch_embeddings(self, texts: List[str]):
    if not self.model:  # ❌ Fails for Google provider
        logger.error("Embedding model not initialized")
        return [None] * len(texts)
```

**After:**
```python
async def generate_batch_embeddings(self, texts: List[str]):
    if not self.model and not self.google_provider:  # ✅ Checks both
        logger.error("Embedding model not initialized")
        return [None] * len(texts)
    
    if self.provider == "google":
        embeddings = await self.google_provider.generate_embeddings(valid_texts)
    else:
        embeddings = await loop.run_in_executor(None, lambda: self.model.encode(valid_texts))
```

### Issue 3: No Retry Logic for Initialization Failures
The initialization method had no retry logic, so transient network issues or API rate limits could cause permanent failures.

## Solution Implemented

### 1. Added `is_initialized()` Helper Method
```python
def is_initialized(self) -> bool:
    """Check if embedding service is initialized and ready to use"""
    return self.model is not None or self.google_provider is not None
```

### 2. Enhanced Initialization with Retry Logic
- Added retry logic with exponential backoff (3 attempts by default)
- Improved logging to show initialization progress
- Better error messages for troubleshooting

### 3. Fixed Batch Embeddings for Google Provider
- Added proper check for both `self.model` and `self.google_provider`
- Added Google-specific batch embedding path using `google_provider.generate_embeddings()`

### 4. Added Queue Processing Guard
- Queue now checks if embedding service is initialized before processing
- Automatically retries after 5 seconds if service not ready
- Prevents "model not loaded" errors during startup

### 5. Improved Status Reporting
- `get_stats()` now correctly reports status for all providers
- Added `provider` field to status output for clarity

## Files Modified

1. **src/vector_db/embeddings.py**
   - Added `is_initialized()` method
   - Enhanced `initialize()` with retry logic and better logging
   - Fixed `generate_batch_embeddings()` to support Google provider
   - Fixed `get_stats()` to check both model types

2. **src/indexing/queue.py**
   - Added embedding service readiness check before processing
   - Added `_retry_processing_after_delay()` helper method
   - Prevents processing when service not ready

## Testing the Fix

### 1. Check Container Logs
```bash
docker logs context-server --tail 50
```

Look for these success messages:
```
✅ Google embeddings initialized successfully (dim=768)
✅ Embedding service initialized successfully (provider=google, dim=768)
Embedding service initialized successfully
```

### 2. Verify Status Endpoint
The status should now correctly show `model_loaded: true` for Google embeddings.

### 3. Test Indexing
Queued tasks should now process successfully once the embedding service is initialized.

## Prevention Measures

### 1. Always Use `is_initialized()` Method
When checking if the embedding service is ready, use the `is_initialized()` method instead of checking `self.model` directly.

### 2. Handle Both Provider Types
When adding new features that use embeddings, always handle both:
- Local models (`self.model` for sentence-transformers/UniXcoder)
- API providers (`self.google_provider` for Google embeddings)

### 3. Add Retry Logic for External Services
Any code that depends on external services (APIs, databases) should include retry logic with exponential backoff.

### 4. Improve Logging
Always log initialization progress and failures with clear, actionable messages.

## Monitoring

### Key Metrics to Watch
1. **Embedding Service Status**: Check `/health` endpoint regularly
2. **Queue Processing**: Monitor `pending_count` and `total_processed` stats
3. **Initialization Time**: Track how long embedding service takes to initialize
4. **API Errors**: Monitor Google API errors and rate limits

### Health Check
The health check endpoint now correctly reports embedding service status:
```json
{
  "overall_status": "healthy",
  "checks": {
    "embedding_service": {
      "status": "healthy",
      "details": {
        "provider": "google",
        "model_name": "text-embedding-004",
        "model_loaded": true,
        "embedding_dim": 768
      }
    }
  }
}
```

## Future Improvements

1. **Add Startup Probe**: Implement Kubernetes-style startup probe to delay traffic until service is ready
2. **Add Circuit Breaker**: Implement circuit breaker pattern for Google API calls
3. **Add Metrics**: Track initialization success/failure rates and retry counts
4. **Add Alerts**: Alert on repeated initialization failures
5. **Add Tests**: Add integration tests for Google embeddings provider

