"""
Unit tests for Response Generator (Story 3-4)
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.ai_processing.response_generator import get_response_generator


@pytest.mark.asyncio
async def test_response_generator_calls_client():
    gen = get_response_generator()
    with patch(
        "src.ai_processing.ollama_client.OllamaClient.generate_response",
        new=AsyncMock(return_value="ok"),
    ) as mock_gen:
        text = await gen.generate("hello", model="llama3")
        assert text == "ok"
        mock_gen.assert_called()
