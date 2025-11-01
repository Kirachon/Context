"""
Unit tests for AST metadata storage functionality.
"""

from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.vector_db.ast_store import ASTVectorStore
from src.search.ast_models import (
    ASTSearchRequest,
    SymbolType,
    SearchScope,
    SymbolEmbeddingPayload,
)
from src.parsing.models import (
    ParseResult,
    Language,
    SymbolInfo,
    ClassInfo,
    ImportInfo,
    ParameterInfo,
)


class TestASTVectorStore:
    """Test AST vector store functionality."""

    def setup_method(self):
        self.ast_store = ASTVectorStore("test_context")

    def test_initialization(self):
        """Test AST vector store initialization."""
        assert self.ast_store.base_collection_name == "test_context"
        assert self.ast_store.symbol_collection == "test_context_symbols"
        assert self.ast_store.class_collection == "test_context_classes"
        assert self.ast_store.import_collection == "test_context_imports"
        assert self.ast_store.stats["symbols_stored"] == 0

    def test_generate_symbol_search_text(self):
        """Test symbol search text generation."""
        # Create test symbol
        param = ParameterInfo(name="name", type_hint="str", default_value="'test'")
        symbol = SymbolInfo(
            name="create_user",
            type="function",
            line_start=10,
            line_end=20,
            parameters=[param],
            return_type="User",
            docstring="Create a new user",
            is_async=True,
            decorators=["@validate"],
        )

        # Create test parse result
        parse_result = ParseResult(
            file_path=Path("test.py"), language=Language.PYTHON, ast_root=None
        )

        # Generate search text
        search_text = self.ast_store._generate_symbol_search_text(symbol, parse_result)

        # Verify search text contains key information
        assert "Language: python" in search_text
        assert "Type: function" in search_text
        assert "Name: create_user" in search_text
        assert "Parameters: name" in search_text
        assert "Returns: User" in search_text
        assert "Documentation: Create a new user" in search_text
        assert "async" in search_text
        assert "@validate" in search_text

    def test_generate_class_search_text(self):
        """Test class search text generation."""
        class_info = ClassInfo(
            name="UserService",
            line_start=5,
            line_end=50,
            base_classes=["BaseService"],
            interfaces=["IUserService"],
            methods=["create_user", "get_user"],
            docstring="Service for user management",
            is_abstract=True,
        )

        parse_result = ParseResult(
            file_path=Path("service.py"), language=Language.PYTHON, ast_root=None
        )

        search_text = self.ast_store._generate_class_search_text(
            class_info, parse_result
        )

        assert "Language: python" in search_text
        assert "Type: class" in search_text
        assert "Name: UserService" in search_text
        assert "Extends: BaseService" in search_text
        assert "Implements: IUserService" in search_text
        assert "Methods: create_user, get_user" in search_text
        assert "Documentation: Service for user management" in search_text
        assert "abstract" in search_text

    def test_generate_import_search_text(self):
        """Test import search text generation."""
        import_info = ImportInfo(
            module="os.path", alias="path", import_type="import", line=1
        )

        parse_result = ParseResult(
            file_path=Path("utils.py"), language=Language.PYTHON, ast_root=None
        )

        search_text = self.ast_store._generate_import_search_text(
            import_info, parse_result
        )

        assert "Language: python" in search_text
        assert "Import: import" in search_text
        assert "Module: os.path" in search_text
        assert "Alias: path" in search_text

    def test_generate_unique_ids(self):
        """Test unique ID generation for different types."""
        file_path = Path("test.py")

        # Test symbol ID
        symbol = SymbolInfo(
            name="test_func", type="function", line_start=10, line_end=15
        )
        symbol_id = self.ast_store._generate_symbol_id(file_path, symbol)
        assert len(symbol_id) == 32  # MD5 hash length

        # Test class ID
        class_info = ClassInfo(name="TestClass", line_start=5, line_end=25)
        class_id = self.ast_store._generate_class_id(file_path, class_info)
        assert len(class_id) == 32

        # Test import ID
        import_info = ImportInfo(module="os", import_type="import", line=1)
        import_id = self.ast_store._generate_import_id(file_path, import_info)
        assert len(import_id) == 32

        # IDs should be different
        assert symbol_id != class_id != import_id

    @patch("src.vector_db.ast_store.get_qdrant_client")
    async def test_ensure_collections(self, mock_get_client):
        """Test collection creation."""
        # Mock Qdrant client
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = []
        mock_client.get_collections.return_value = mock_collections
        mock_get_client.return_value = mock_client

        # Mock embedding service
        with patch.object(
            self.ast_store.embedding_service, "initialize", new_callable=AsyncMock
        ):
            with patch.object(self.ast_store.embedding_service, "embedding_dim", 384):
                result = await self.ast_store.ensure_collections()

        assert result is True
        assert (
            mock_client.create_collection.call_count == 3
        )  # symbols, classes, imports

    @patch("src.vector_db.ast_store.get_qdrant_client")
    async def test_store_parse_result_success(self, mock_get_client):
        """Test successful parse result storage."""
        # Mock Qdrant client
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = [
            Mock(name="test_context_symbols"),
            Mock(name="test_context_classes"),
            Mock(name="test_context_imports"),
        ]
        mock_client.get_collections.return_value = mock_collections
        mock_get_client.return_value = mock_client

        # Mock embedding service
        mock_embedding = [0.1] * 384
        with patch.object(
            self.ast_store.embedding_service, "initialize", new_callable=AsyncMock
        ):
            with patch.object(self.ast_store.embedding_service, "embedding_dim", 384):
                with patch.object(
                    self.ast_store.embedding_service,
                    "generate_embedding",
                    new_callable=AsyncMock,
                    return_value=mock_embedding,
                ):

                    # Create test parse result
                    symbol = SymbolInfo(
                        name="test_func", type="function", line_start=1, line_end=5
                    )
                    class_info = ClassInfo(name="TestClass", line_start=10, line_end=20)
                    import_info = ImportInfo(module="os", import_type="import", line=1)

                    parse_result = ParseResult(
                        file_path=Path("test.py"),
                        language=Language.PYTHON,
                        ast_root=None,
                        symbols=[symbol],
                        classes=[class_info],
                        imports=[import_info],
                        parse_success=True,
                    )

                    # Store parse result
                    result = await self.ast_store.store_parse_result(parse_result)

        assert result is True
        assert mock_client.upsert.call_count == 3  # symbols, classes, imports
        assert self.ast_store.stats["symbols_stored"] == 1
        assert self.ast_store.stats["classes_stored"] == 1
        assert self.ast_store.stats["imports_stored"] == 1

    async def test_store_failed_parse_result(self):
        """Test handling of failed parse results."""
        parse_result = ParseResult(
            file_path=Path("invalid.py"),
            language=Language.PYTHON,
            ast_root=None,
            parse_success=False,
            parse_error="Syntax error",
        )

        result = await self.ast_store.store_parse_result(parse_result)
        assert result is False


class TestASTSearchModels:
    """Test AST search models."""

    def test_symbol_embedding_payload(self):
        """Test SymbolEmbeddingPayload model."""
        payload = SymbolEmbeddingPayload(
            file_path="test.py",
            symbol_name="test_func",
            symbol_type="function",
            language="python",
            line_start=1,
            line_end=5,
            search_text="Language: python | Type: function | Name: test_func",
        )

        assert payload.file_path == "test.py"
        assert payload.symbol_name == "test_func"
        assert payload.is_async is False  # default value

        # Test serialization
        data = payload.to_dict()
        assert isinstance(data, dict)
        assert data["file_path"] == "test.py"
        assert "indexed_at" in data

    def test_ast_search_request(self):
        """Test ASTSearchRequest model."""
        request = ASTSearchRequest(
            query="async functions",
            limit=20,
            symbol_types=[SymbolType.FUNCTION],
            languages=["python"],
            search_scope=SearchScope.SYMBOLS,
            is_async=True,
        )

        assert request.query == "async functions"
        assert request.limit == 20
        assert SymbolType.FUNCTION in request.symbol_types
        assert request.is_async is True
        assert request.search_scope == SearchScope.SYMBOLS

    def test_ast_search_request_validation(self):
        """Test ASTSearchRequest validation."""
        # Test limit bounds
        request = ASTSearchRequest(query="test", limit=150)
        assert request.limit == 100  # Should be clamped to max

        request = ASTSearchRequest(query="test", limit=0)
        assert request.limit == 1  # Should be clamped to min

        # Test score bounds
        request = ASTSearchRequest(query="test", min_score=1.5)
        assert request.min_score == 1.0  # Should be clamped to max

        request = ASTSearchRequest(query="test", min_score=-0.5)
        assert request.min_score == 0.0  # Should be clamped to min
