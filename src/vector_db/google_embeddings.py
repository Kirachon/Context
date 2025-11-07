"""
Google Embeddings Provider

Generates vector embeddings using Google's Gemini API or Vertex AI.
"""

import logging
import os
from typing import List, Optional
import asyncio
import httpx

logger = logging.getLogger(__name__)


class GoogleEmbeddingsProvider:
    """
    Google Embeddings Provider
    
    Supports:
    - Gemini API (text-embedding-004)
    - Vertex AI (textembedding-gecko)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-004",
        embedding_dim: int = 768,
    ):
        """
        Initialize Google embeddings provider
        
        Args:
            api_key: Google API key (or set GOOGLE_API_KEY env var)
            model: Model name (text-embedding-004, textembedding-gecko, etc.)
            embedding_dim: Expected embedding dimension
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter"
            )
        
        self.model = model
        self.embedding_dim = embedding_dim
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        # Determine API endpoint based on model
        if "gecko" in model.lower():
            # Vertex AI endpoint
            self.api_type = "vertex"
            logger.info("Using Vertex AI embeddings")
        else:
            # Gemini API endpoint
            self.api_type = "gemini"
            logger.info("Using Gemini API embeddings")
        
        logger.info(
            f"GoogleEmbeddingsProvider initialized model={model} dim={embedding_dim}"
        )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else []
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        if not texts:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if self.api_type == "gemini":
                    return await self._generate_gemini_embeddings(client, texts)
                else:
                    return await self._generate_vertex_embeddings(client, texts)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}", exc_info=True)
            raise
    
    async def _generate_gemini_embeddings(
        self, client: httpx.AsyncClient, texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings using Gemini API"""
        url = f"{self.base_url}/models/{self.model}:batchEmbedContents"
        
        # Prepare requests
        requests = [
            {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": text}]},
            }
            for text in texts
        ]
        
        response = await client.post(
            url,
            json={"requests": requests},
            params={"key": self.api_key},
        )
        response.raise_for_status()
        
        data = response.json()
        embeddings = [
            item["values"] for item in data.get("embeddings", [])
        ]
        
        logger.info(f"Generated {len(embeddings)} embeddings via Gemini API")
        return embeddings
    
    async def _generate_vertex_embeddings(
        self, client: httpx.AsyncClient, texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings using Vertex AI"""
        # Vertex AI requires different authentication (service account)
        # This is a simplified version - production should use google-auth
        logger.warning(
            "Vertex AI embeddings require service account authentication. "
            "Consider using Gemini API instead or implement proper auth."
        )
        raise NotImplementedError(
            "Vertex AI embeddings require service account setup. "
            "Use Gemini API (text-embedding-004) instead."
        )
    
    def get_stats(self):
        """Get provider statistics"""
        return {
            "provider": "google",
            "api_type": self.api_type,
            "model": self.model,
            "embedding_dim": self.embedding_dim,
        }

