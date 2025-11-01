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

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = base_url or settings.ollama_base_url
        self.timeout = timeout or settings.ollama_timeout

    async def generate_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> str:
        """Generate text response from Ollama"""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model or settings.ollama_default_model,
            "prompt": self._build_prompt(prompt, context),
            "stream": stream,
        }

        logger.debug(f"Ollama request -> {url} model={payload['model']}")

        if aiohttp is None:
            raise RuntimeError("aiohttp not installed; cannot call Ollama HTTP API")
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("response", "")

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

