"""
Ollama Client (Epic 3)

Minimal async HTTP client for local Ollama server.
"""

try:
    import aiohttp  # type: ignore
except Exception:  # pragma: no cover
    aiohttp = None  # defer hard dependency to runtime
import asyncio
import logging
from typing import Optional, Dict, Any

from src.config.settings import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Async client for Ollama HTTP API"""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None, max_retries: Optional[int] = None):
        self.base_url = base_url or settings.ollama_base_url
        self.timeout = timeout or settings.ollama_timeout
        self.max_retries = max_retries or getattr(settings, "ollama_max_retries", 3)

    async def generate_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> str:
        """Generate text response from Ollama with retry/backoff and metrics"""
        from src.monitoring.metrics import metrics
        url = f"{self.base_url}/api/generate"
        model_name = model or settings.ollama_default_model
        payload = {
            "model": model_name,
            "prompt": self._build_prompt(prompt, context),
            "stream": stream,
        }

        logger.debug(f"Ollama request -> {url} model={model_name}")

        if aiohttp is None:
            raise RuntimeError("aiohttp not installed; cannot call Ollama HTTP API")

        # Metrics
        c_ok = metrics.counter("ollama_requests_total", "Ollama requests", ("model", "status"))
        h_latency = metrics.histogram("ollama_request_seconds", "Ollama request latency")

        # Retry loop
        attempt = 0
        backoff = 0.5
        last_exc: Optional[Exception] = None
        while attempt < self.max_retries:
            attempt += 1
            start = asyncio.get_event_loop().time()
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=payload) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        dur = asyncio.get_event_loop().time() - start
                        try:
                            h_latency.labels().observe(dur)
                            c_ok.labels(model_name, "ok").inc()
                        except Exception:
                            pass
                        return data.get("response", "")
            except Exception as e:  # network or HTTP error
                last_exc = e
                dur = asyncio.get_event_loop().time() - start
                try:
                    h_latency.labels().observe(dur)
                    c_ok.labels(model_name, "error").inc()
                except Exception:
                    pass
                logger.warning(f"Ollama request failed (attempt {attempt}/{self.max_retries}): {e}")
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 8.0)

        # If we get here, all retries failed
        raise RuntimeError(f"Ollama request failed after {self.max_retries} attempts: {last_exc}")

    def _build_prompt(self, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        if not context:
            return prompt
        import json
        return (
            "You are a coding assistant. Use the following context if helpful.\n"
            + "Context:\n"
            + json.dumps(context, indent=2)
            + "\n\nRequest: "
            + prompt
        )


# Singleton accessor
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client

