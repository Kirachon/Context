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

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from sentence_transformers import SentenceTransformer
import torch
import numpy as np
from src.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding Service

    Generates vector embeddings for code text using sentence-transformers or UniXcoder (feature-flagged).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service

        Args:
            model_name: Name of the sentence-transformers model
        """
        # Provider selection via settings
        self.provider = (
            settings.embeddings_provider or "sentence-transformers"
        ).lower()

        # Handle provider-specific configuration
        if self.provider == "google":
            # Google embeddings (Gemini API)
            self.model_name = getattr(settings, "google_embedding_model", "text-embedding-004")
            self.embedding_dim = 768  # Default for Gemini embeddings
        elif self.provider == "unixcoder":
            if not settings.unixcoder_enabled:
                logger.warning(
                    "UniXcoder provider selected but not enabled; falling back to sentence-transformers"
                )
                self.provider = "sentence-transformers"
                self.model_name = model_name
                self.embedding_dim = 384
            else:
                self.model_name = "microsoft/unixcoder-base"
                self.embedding_dim = 768
        else:
            # sentence-transformers (default)
            self.model_name = model_name
            self.embedding_dim = 384  # Default for all-MiniLM-L6-v2; will update after load

        self.model: Optional[Any] = None
        self.tokenizer: Optional[Any] = None  # For UniXcoder
        self.google_provider: Optional[Any] = None  # For Google embeddings
        self.max_chunk_length = 512
        self.cache: Dict[str, List[float]] = {}

        # GPU device detection (automatic with CPU fallback)
        self.device = None
        self.device_name = "CPU"
        self.gpu_available = False

        try:
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
                self.gpu_available = True
                self.device_name = torch.cuda.get_device_name(0)
                gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                logger.info(
                    f"🚀 GPU detected: {self.device_name} "
                    f"({gpu_memory_gb:.1f}GB VRAM) - Embeddings will use GPU acceleration"
                )
            else:
                self.device = torch.device("cpu")
                logger.info("💻 No GPU detected - Embeddings will use CPU")
        except Exception as e:
            # Graceful fallback to CPU on any GPU detection error
            self.device = torch.device("cpu")
            logger.warning(f"⚠️  GPU detection failed ({e}), falling back to CPU")
            self.device_name = "CPU"
            self.gpu_available = False

        logger.info(
            f"EmbeddingService initialized provider={self.provider} model={self.model_name}"
        )

    def is_initialized(self) -> bool:
        """
        Check if embedding service is initialized and ready to use

        Returns:
            bool: True if service is ready
        """
        return self.model is not None or self.google_provider is not None

    async def initialize(self, max_retries: int = 3, retry_delay: float = 2.0):
        """
        Initialize the embedding model with retry logic

        Args:
            max_retries: Maximum number of initialization attempts
            retry_delay: Delay between retries in seconds
        """
        if self.is_initialized():
            logger.debug("Embedding model already initialized")
            return

        logger.info(f"Loading embedding model: {self.model_name} (provider={self.provider})")

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                loop = asyncio.get_event_loop()

                if self.provider == "google":
                    # Initialize Google embeddings provider (no model download needed!)
                    from src.vector_db.google_embeddings import GoogleEmbeddingsProvider

                    google_api_key = getattr(settings, "google_api_key", None)
                    if not google_api_key:
                        raise ValueError(
                            "GOOGLE_API_KEY environment variable required for Google embeddings"
                        )

                    logger.info(f"Initializing Google embeddings provider (attempt {attempt}/{max_retries})...")
                    self.google_provider = GoogleEmbeddingsProvider(
                        api_key=google_api_key,
                        model=self.model_name,
                        embedding_dim=self.embedding_dim,
                    )

                    # Test the connection with retry
                    logger.info("Testing Google API connection...")
                    test_embedding = await self.google_provider.generate_embedding("test")
                    self.embedding_dim = len(test_embedding)
                    logger.info(f"✅ Google embeddings initialized successfully (dim={self.embedding_dim})")

                elif self.provider == "sentence-transformers":
                    # Load ST model in a thread to avoid blocking
                    logger.info(
                        f"Loading sentence-transformers model (attempt {attempt}/{max_retries}) "
                        f"on device={self.device_name}..."
                    )

                    def _load_and_move_model():
                        """Load model and move to GPU device"""
                        model = SentenceTransformer(self.model_name)
                        # Move model to GPU if available
                        model = model.to(self.device)
                        return model

                    self.model = await loop.run_in_executor(None, _load_and_move_model)
                    test_embedding = self.model.encode(["test"])
                    self.embedding_dim = len(test_embedding[0])

                    logger.info(
                        f"✅ Sentence-transformers model loaded on {self.device_name} "
                        f"(dim={self.embedding_dim})"
                    )

                else:
                    # Load UniXcoder model/tokenizer with GPU support
                    from transformers import AutoTokenizer, AutoModel

                    logger.info(
                        f"Loading UniXcoder model (attempt {attempt}/{max_retries}) "
                        f"on device={self.device_name}..."
                    )

                    def _load_unixcoder():
                        """Load UniXcoder and move to GPU device"""
                        tok = AutoTokenizer.from_pretrained(self.model_name)
                        mdl = AutoModel.from_pretrained(self.model_name)
                        # Move model to GPU if available
                        mdl = mdl.to(self.device)
                        return tok, mdl

                    self.tokenizer, self.model = await loop.run_in_executor(
                        None, _load_unixcoder
                    )
                    # Infer hidden size from model config
                    hidden = getattr(
                        getattr(self.model, "config", None), "hidden_size", None
                    )
                    if hidden:
                        self.embedding_dim = int(hidden)

                    logger.info(
                        f"✅ UniXcoder model loaded on {self.device_name} "
                        f"(dim={self.embedding_dim})"
                    )

                logger.info(
                    f"✅ Embedding service initialized successfully (provider={self.provider}, dim={self.embedding_dim})"
                )
                return  # Success!

            except Exception as e:
                last_error = e
                logger.error(
                    f"❌ Failed to initialize embedding service (attempt {attempt}/{max_retries}): {e}",
                    exc_info=(attempt == max_retries)  # Only log full traceback on last attempt
                )

                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(
                        f"❌ Failed to initialize embedding service after {max_retries} attempts"
                    )
                    raise RuntimeError(
                        f"Failed to initialize embedding service: {last_error}"
                    ) from last_error

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
        lines = text.split("\n")
        chunks = []
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 <= max_length:
                current_chunk += line + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # If single line is too long, chunk it
                if len(line) > max_length:
                    for i in range(0, len(line), max_length):
                        chunks.append(line[i : i + max_length])
                else:
                    current_chunk = line + "\n"

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
        if not self.model and not self.google_provider:
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
            logger.debug(
                f"Generating embedding for text (length: {len(text)}) provider={self.provider}"
            )

            if self.provider == "google":
                # Use Google embeddings API (no local model needed!)
                embedding = await self.google_provider.generate_embedding(text)
            elif self.provider == "sentence-transformers":
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None, lambda: self.model.encode([text])[0]
                )
            else:
                # UniXcoder: mean pool last hidden state
                import numpy as _np

                with torch.no_grad():
                    inputs = self.tokenizer(
                        text, return_tensors="pt", truncation=True, max_length=512
                    )
                    # Move inputs to the same device as the model
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    outputs = self.model(**inputs)
                    token_embeddings = outputs.last_hidden_state  # [1, seq, hidden]
                    mask = inputs["attention_mask"].unsqueeze(-1).float()
                    summed = (token_embeddings * mask).sum(dim=1)
                    counts = mask.sum(dim=1).clamp(min=1.0)
                    mean_pooled = (summed / counts).squeeze(0).cpu().numpy()
                    embedding = mean_pooled

            # Convert to list and cache
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
            self.cache[cache_key] = embedding_list

            logger.debug(f"Generated embedding with dimension: {len(embedding_list)}")
            return embedding_list

        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            return None

    async def generate_batch_embeddings(
        self, texts: List[str]
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (None for failed embeddings)
        """
        # Check if embedding service is initialized (either model or google_provider)
        if not self.model and not self.google_provider:
            logger.error("Embedding model not initialized")
            return [None] * len(texts)

        if not texts:
            return []

        logger.info(f"Generating batch embeddings for {len(texts)} texts provider={self.provider}")

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

            # Generate embeddings based on provider
            if self.provider == "google":
                # Use Google embeddings API for batch generation
                embeddings = await self.google_provider.generate_embeddings(valid_texts)
            else:
                # Use sentence-transformers or UniXcoder (local models)
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None, lambda: self.model.encode(valid_texts)
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

    async def generate_code_embedding(
        self, code: str, file_path: str = "", language: str = ""
    ) -> Optional[List[float]]:
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
        # Check if any provider is loaded (model for local, google_provider for API)
        is_loaded = self.model is not None or self.google_provider is not None

        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "max_chunk_length": self.max_chunk_length,
            "cache_size": len(self.cache),
            "model_loaded": is_loaded,
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


async def generate_code_embedding(
    code: str, file_path: str = "", language: str = ""
) -> Optional[List[float]]:
    """Generate code embedding (entry point for integration)"""
    return await embedding_service.generate_code_embedding(code, file_path, language)


def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance"""
    return embedding_service


def get_embedding_stats() -> Dict[str, Any]:
    """Get embedding statistics (entry point for status endpoints)"""
    return embedding_service.get_stats()
