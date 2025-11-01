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
        # Circuit breaker
        self.cb_enabled = getattr(settings, "ollama_cb_enabled", True)
        self.cb_threshold = getattr(settings, "ollama_cb_threshold", 5)
        self.cb_window = getattr(settings, "ollama_cb_window_seconds", 30)
        self.cb_cooldown = getattr(settings, "ollama_cb_cooldown_seconds", 20)
        self._cb_state = "closed"
        self._cb_failures: list[float] = []
        self._cb_opened_at: float = 0.0

    def _cb_now(self) -> float:
        return asyncio.get_event_loop().time()

    def _cb_allow(self) -> bool:
        if not self.cb_enabled:
            return True
        now = self._cb_now()
        if self._cb_state == "open":
            # Check cooldown
            if now - self._cb_opened_at >= self.cb_cooldown:
                self._cb_state = "half_open"
                return True
            return False
        return True

    def _cb_record_failure(self):
        if not self.cb_enabled:
            return
        now = self._cb_now()
        # drop old failures outside window
        self._cb_failures = [t for t in self._cb_failures if now - t <= self.cb_window]
        self._cb_failures.append(now)
        if self._cb_state in ("closed", "half_open") and len(self._cb_failures) >= self.cb_threshold:
            self._cb_state = "open"
            self._cb_opened_at = now
            try:
                from src.monitoring.metrics import metrics
                metrics.counter("ollama_circuit_transitions_total", "Circuit transitions", ("to_state",)).labels("open").inc()
            except Exception:
                pass

    def _cb_record_success(self):
        if not self.cb_enabled:
            return
        self._cb_failures.clear()
        if self._cb_state in ("open", "half_open"):
            self._cb_state = "closed"
            try:
                from src.monitoring.metrics import metrics
                metrics.counter("ollama_circuit_transitions_total", "Circuit transitions", ("to_state",)).labels("closed").inc()
            except Exception:
                pass

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

        # Circuit breaker check
        if not self._cb_allow():
            logger.warning("Ollama circuit open; request short-circuited")
            try:
                c_ok.labels(model_name, "circuit_open").inc()
            except Exception:
                pass
            raise RuntimeError("Ollama circuit is open")

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
                        self._cb_record_success()
                        return data.get("response", "")
            except Exception as e:  # network or HTTP error
                last_exc = e
                dur = asyncio.get_event_loop().time() - start
                try:
                    h_latency.labels().observe(dur)
                    c_ok.labels(model_name, "error").inc()
                except Exception:
                    pass
                self._cb_record_failure()
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

