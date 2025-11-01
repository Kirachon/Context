"""
Intelligent Response Generation (Story 3-4)

Generates responses using Ollama with enhanced prompts and context.
"""

import logging
from typing import Dict, Any, Optional

from .ollama_client import get_ollama_client

logger = logging.getLogger(__name__)


class ResponseGenerator:
    def __init__(self):
        self.client = get_ollama_client()

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        logger.debug("Generating response via Ollama")
        return await self.client.generate_response(prompt, model=model, context=context)


# Singleton
_response_generator: Optional[ResponseGenerator] = None


def get_response_generator() -> ResponseGenerator:
    global _response_generator
    if _response_generator is None:
        _response_generator = ResponseGenerator()
    return _response_generator

