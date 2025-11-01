"""
Unit tests for Vector Database Integration

Tests Qdrant client, embeddings, vector store, and collections.
"""

import pytest
import os
from unittest.mock import Mock, patch

# Add project root to path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.vector_db.qdrant_client import QdrantClientService
from src.vector_db.embeddings import EmbeddingService
from src.vector_db.vector_store import VectorStore
from src.vector_db.collections import CollectionManager


class TestQdrantClient:
    """Test Qdrant client service"""

    @pytest.fixture
    def qdrant_service(self):
        """Create Qdrant service instance"""
        return QdrantClientService()

    @pytest.mark.asyncio
    @patch("src.vector_db.qdrant_client.QdrantClient")
    async def test_connect_success(self, mock_qdrant_class, qdrant_service):
        """Test successful connection to Qdrant"""
        mock_client = Mock()
        mock_qdrant_class.return_value = mock_client

        # Mock health check
        with patch.object(
            qdrant_service, "health_check", return_value={"status": "healthy"}
        ):
            result = await qdrant_service.connect()

        assert result is True
        assert qdrant_service.is_connected is True
        assert qdrant_service.client is not None

    @pytest.mark.asyncio
    async def test_connect_failure(self, qdrant_service):
        """Test connection failure with retries"""
        with patch(
            "src.vector_db.qdrant_client.QdrantClient",
            side_effect=Exception("Connection failed"),
        ):
            result = await qdrant_service.connect()

        assert result is False
        assert qdrant_service.is_connected is False
        assert qdrant_service.connection_attempts == 3

    @pytest.mark.asyncio
    async def test_health_check_success(self, qdrant_service):
        """Test successful health check"""
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = [Mock(), Mock()]
        mock_client.get_collections.return_value = mock_collections

        qdrant_service.client = mock_client

        health = await qdrant_service.health_check()

        assert health["status"] == "healthy"
        assert health["collections_count"] == 2

    @pytest.mark.asyncio
    async def test_health_check_no_client(self, qdrant_service):
        """Test health check without client"""
        health = await qdrant_service.health_check()

        assert health["status"] == "disconnected"
        assert "message" in health


class TestEmbeddingService:
    """Test embedding service"""

    @pytest.fixture
    def embedding_service(self):
        """Create embedding service instance"""
        return EmbeddingService()

    @pytest.mark.asyncio
    @patch("src.vector_db.embeddings.SentenceTransformer")
    async def test_initialize_success(self, mock_transformer_class, embedding_service):
        """Test successful embedding service initialization"""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
        mock_transformer_class.return_value = mock_model

        await embedding_service.initialize()

        assert embedding_service.model is not None
        assert embedding_service.embedding_dim == 3

    def test_chunk_text_small(self, embedding_service):
        """Test text chunking for small text"""
        text = "small text"
        chunks = embedding_service.chunk_text(text, max_length=100)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_large(self, embedding_service):
        """Test text chunking for large text"""
        text = "a" * 1000
        chunks = embedding_service.chunk_text(text, max_length=100)

        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, embedding_service):
        """Test successful embedding generation"""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
        embedding_service.model = mock_model

        embedding = await embedding_service.generate_embedding("test text")

        assert embedding == [0.1, 0.2, 0.3]
        assert embedding_service._get_cache_key("test text") in embedding_service.cache

    @pytest.mark.asyncio
    async def test_generate_embedding_no_model(self, embedding_service):
        """Test embedding generation without model"""
        embedding = await embedding_service.generate_embedding("test text")

        assert embedding is None

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings(self, embedding_service):
        """Test batch embedding generation"""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
        embedding_service.model = mock_model

        embeddings = await embedding_service.generate_batch_embeddings(
            ["text1", "text2"]
        )

        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2]
        assert embeddings[1] == [0.3, 0.4]


class TestVectorStore:
    """Test vector store service"""

    @pytest.fixture
    def vector_store(self):
        """Create vector store instance"""
        return VectorStore("test_collection")

    @pytest.mark.asyncio
    @patch("src.vector_db.vector_store.get_qdrant_client")
    async def test_ensure_collection_exists(self, mock_get_client, vector_store):
        """Test ensuring collection exists"""
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = [Mock(name="test_collection")]
        mock_client.get_collections.return_value = mock_collections
        mock_get_client.return_value = mock_client

        result = await vector_store.ensure_collection()

        assert result is True

    @pytest.mark.asyncio
    @patch("src.vector_db.vector_store.get_qdrant_client")
    async def test_upsert_vector_success(self, mock_get_client, vector_store):
        """Test successful vector upsert"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        with patch.object(vector_store, "ensure_collection", return_value=True):
            result = await vector_store.upsert_vector(
                id="test_id",
                vector=[0.1, 0.2, 0.3],
                payload={"file_path": "/test/file.py"},
            )

        assert result is True
        assert vector_store.stats["vectors_stored"] == 1
        mock_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.vector_db.vector_store.get_qdrant_client")
    async def test_search_vectors(self, mock_get_client, vector_store):
        """Test vector search"""
        mock_client = Mock()
        mock_result = Mock()
        mock_result.id = "test_id"
        mock_result.score = 0.95
        mock_result.payload = {"file_path": "/test/file.py"}
        mock_client.search.return_value = [mock_result]
        mock_get_client.return_value = mock_client

        results = await vector_store.search([0.1, 0.2, 0.3], limit=10)

        assert len(results) == 1
        assert results[0]["id"] == "test_id"
        assert results[0]["score"] == 0.95
        assert vector_store.stats["vectors_retrieved"] == 1


class TestCollectionManager:
    """Test collection manager"""

    @pytest.fixture
    def collection_manager(self):
        """Create collection manager instance"""
        return CollectionManager()

    @pytest.mark.asyncio
    @patch("src.vector_db.collections.get_qdrant_client")
    async def test_create_collection_success(self, mock_get_client, collection_manager):
        """Test successful collection creation"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        with patch.object(collection_manager, "collection_exists", return_value=False):
            result = await collection_manager.create_collection("test_collection")

        assert result is True
        mock_client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.vector_db.collections.get_qdrant_client")
    async def test_list_collections(self, mock_get_client, collection_manager):
        """Test listing collections"""
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = [Mock(name="col1"), Mock(name="col2")]
        mock_client.get_collections.return_value = mock_collections
        mock_get_client.return_value = mock_client

        collections = await collection_manager.list_collections()

        assert len(collections) == 2

    def test_generate_collection_name(self, collection_manager):
        """Test collection name generation"""
        name = collection_manager.generate_collection_name("/path/to/my-project")

        assert name == "context_my_project"
        assert name.startswith("context_")
        assert name.islower()


class TestIntegration:
    """Test integration between components"""

    @pytest.mark.asyncio
    @patch("src.vector_db.qdrant_client.get_qdrant_client")
    @patch("src.vector_db.embeddings.generate_code_embedding")
    async def test_file_indexing_with_vectors(
        self, mock_generate_embedding, mock_get_client
    ):
        """Test file indexing generates and stores vectors"""
        from src.indexing.file_indexer import file_indexer

        # Mock embedding generation
        mock_generate_embedding.return_value = [0.1, 0.2, 0.3]

        # Mock Qdrant client
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Mock file operations
        with patch("builtins.open", mock_open(read_data="print('hello')")):
            with patch("src.indexing.models.create_file_metadata"):
                with patch("src.indexing.models.get_file_metadata", return_value=None):
                    with patch(
                        "src.vector_db.vector_store.upsert_vector", return_value=True
                    ) as mock_upsert:
                        with patch("pathlib.Path.exists", return_value=True):
                            with patch("pathlib.Path.stat"):
                                result = await file_indexer.index_file("/test/file.py")

        # Verify embedding was generated and stored
        mock_generate_embedding.assert_called_once()
        mock_upsert.assert_called_once()
        assert result is not None


def mock_open(read_data=""):
    """Helper to create mock open function"""
    from unittest.mock import mock_open as _mock_open

    return _mock_open(read_data=read_data)
