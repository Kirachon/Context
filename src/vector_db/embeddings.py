"""
Embedding Service

Generates vector embeddings for code using sentence-transformers.
"""

import logging
import os
import sys
from typing import List, Optional, Dict, Any
import hashlib
import asyncio
from functools import lru_cache

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from sentence_transformers import SentenceTransformer
import torch
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding Service
    
    Generates vector embeddings for code text using sentence-transformers.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service
        
        Args:
            model_name: Name of the sentence-transformers model
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.embedding_dim = 384  # Default for all-MiniLM-L6-v2
        self.max_chunk_length = 512
        self.cache: Dict[str, List[float]] = {}
        
        logger.info(f"EmbeddingService initialized with model: {model_name}")
    
    async def initialize(self):
        """Initialize the embedding model"""
        if self.model is not None:
            logger.warning("Embedding model already initialized")
            return
        
        logger.info(f"Loading embedding model: {self.model_name}")
        
        try:
            # Load model in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, 
                lambda: SentenceTransformer(self.model_name)
            )
            
            # Get actual embedding dimension
            test_embedding = self.model.encode(["test"])
            self.embedding_dim = len(test_embedding[0])
            
            logger.info(f"Embedding model loaded successfully (dim: {self.embedding_dim})")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}", exc_info=True)
            raise
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def chunk_text(self, text: str, max_length: int = None) -> List[str]:
        """
        Chunk text into smaller pieces for embedding
        
        Args:
            text: Text to chunk
            max_length: Maximum length per chunk
            
        Returns:
            List of text chunks
        """
        if max_length is None:
            max_length = self.max_chunk_length
        
        if len(text) <= max_length:
            return [text]
        
        # Simple chunking by lines and then by characters
        lines = text.split('\n')
        chunks = []
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk) + len(line) + 1 <= max_length:
                current_chunk += line + '\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If single line is too long, chunk it
                if len(line) > max_length:
                    for i in range(0, len(line), max_length):
                        chunks.append(line[i:i + max_length])
                else:
                    current_chunk = line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        if not self.model:
            logger.error("Embedding model not initialized")
            return None
        
        if not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(text)
        if cache_key in self.cache:
            logger.debug("Returning cached embedding")
            return self.cache[cache_key]
        
        try:
            logger.debug(f"Generating embedding for text (length: {len(text)})")
            
            # Generate embedding in thread to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode([text])[0]
            )

            # Convert to list and cache (support numpy, torch, or plain list)
            if hasattr(embedding, "tolist"):
                embedding_list = embedding.tolist()
            elif isinstance(embedding, (list, tuple)):
                embedding_list = list(embedding)
            else:
                try:
                    import numpy as _np
                    if isinstance(embedding, _np.ndarray):
                        embedding_list = embedding.tolist()
                    else:
                        # Last resort: wrap in list() constructor
                        embedding_list = list(embedding)
                except Exception:
                    embedding_list = list(embedding)
            self.cache[cache_key] = embedding_list
            
            logger.debug(f"Generated embedding with dimension: {len(embedding_list)}")
            return embedding_list
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            return None
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (None for failed embeddings)
        """
        if not self.model:
            logger.error("Embedding model not initialized")
            return [None] * len(texts)
        
        if not texts:
            return []
        
        logger.info(f"Generating batch embeddings for {len(texts)} texts")
        
        try:
            # Filter out empty texts and track indices
            valid_texts = []
            valid_indices = []
            
            for i, text in enumerate(texts):
                if text.strip():
                    valid_texts.append(text)
                    valid_indices.append(i)
            
            if not valid_texts:
                logger.warning("No valid texts for batch embedding")
                return [None] * len(texts)
            
            # Generate embeddings in thread
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(valid_texts)
            )

            # Map results back to original indices
            results = [None] * len(texts)
            for i, embedding in enumerate(embeddings):
                original_index = valid_indices[i]
                if hasattr(embedding, "tolist"):
                    embedding_list = embedding.tolist()
                elif isinstance(embedding, (list, tuple)):
                    embedding_list = list(embedding)
                else:
                    try:
                        import numpy as _np
                        if isinstance(embedding, _np.ndarray):
                            embedding_list = embedding.tolist()
                        else:
                            embedding_list = list(embedding)
                    except Exception:
                        embedding_list = list(embedding)
                results[original_index] = embedding_list
                
                # Cache the result
                cache_key = self._get_cache_key(valid_texts[i])
                self.cache[cache_key] = embedding_list
            
            logger.info(f"Generated {len(valid_texts)} batch embeddings successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}", exc_info=True)
            return [None] * len(texts)
    
    async def generate_code_embedding(self, code: str, file_path: str = "", language: str = "") -> Optional[List[float]]:
        """
        Generate embedding specifically for code
        
        Args:
            code: Code content
            file_path: Path to the file (for context)
            language: Programming language
            
        Returns:
            Code embedding
        """
        if not code.strip():
            return None
        
        # Prepare code text with context
        context_parts = []
        
        if language:
            context_parts.append(f"Language: {language}")
        
        if file_path:
            context_parts.append(f"File: {os.path.basename(file_path)}")
        
        # Combine context with code
        if context_parts:
            text = " | ".join(context_parts) + "\n\n" + code
        else:
            text = code
        
        # Chunk if necessary
        chunks = self.chunk_text(text)
        
        if len(chunks) == 1:
            return await self.generate_embedding(chunks[0])
        else:
            # For multiple chunks, generate embeddings and average them
            chunk_embeddings = await self.generate_batch_embeddings(chunks)
            valid_embeddings = [emb for emb in chunk_embeddings if emb is not None]
            
            if not valid_embeddings:
                return None
            
            # Average the embeddings
            avg_embedding = np.mean(valid_embeddings, axis=0)
            return avg_embedding.tolist()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get embedding service statistics
        
        Returns:
            dict: Service statistics
        """
        return {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "max_chunk_length": self.max_chunk_length,
            "cache_size": len(self.cache),
            "model_loaded": self.model is not None
        }
    
    def clear_cache(self):
        """Clear embedding cache"""
        self.cache.clear()
        logger.info("Embedding cache cleared")


# Global embedding service instance
embedding_service = EmbeddingService()


async def initialize_embeddings():
    """Initialize embedding service (entry point for integration)"""
    await embedding_service.initialize()


async def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding (entry point for integration)"""
    return await embedding_service.generate_embedding(text)


async def generate_code_embedding(code: str, file_path: str = "", language: str = "") -> Optional[List[float]]:
    """Generate code embedding (entry point for integration)"""
    return await embedding_service.generate_code_embedding(code, file_path, language)


def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance"""
    return embedding_service


def get_embedding_stats() -> Dict[str, Any]:
    """Get embedding statistics (entry point for status endpoints)"""
    return embedding_service.get_stats()
