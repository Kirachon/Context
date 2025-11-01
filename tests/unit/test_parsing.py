"""
Unit tests for parsing functionality.
"""

from pathlib import Path
from unittest.mock import Mock, patch
from src.parsing.parser import CodeParser, detect_language, get_parser
from src.parsing.models import Language, ASTNode, SymbolInfo, ClassInfo, ParameterInfo
from src.parsing.cache import ASTCache
from src.parsing.extractors import PythonExtractor, get_symbol_extractor


class TestLanguageDetection:
    """Test language detection from file extensions."""

    def test_detect_python(self):
        assert detect_language(Path("test.py")) == Language.PYTHON

    def test_detect_javascript(self):
        assert detect_language(Path("test.js")) == Language.JAVASCRIPT
        assert detect_language(Path("test.jsx")) == Language.JAVASCRIPT

    def test_detect_typescript(self):
        assert detect_language(Path("test.ts")) == Language.TYPESCRIPT
        assert detect_language(Path("test.tsx")) == Language.TYPESCRIPT

    def test_detect_java(self):
        assert detect_language(Path("Test.java")) == Language.JAVA

    def test_detect_cpp(self):
        assert detect_language(Path("test.cpp")) == Language.CPP
        assert detect_language(Path("test.cc")) == Language.CPP
        assert detect_language(Path("test.hpp")) == Language.CPP
        assert detect_language(Path("test.h")) == Language.CPP

    def test_detect_go(self):
        assert detect_language(Path("test.go")) == Language.GO

    def test_detect_rust(self):
        assert detect_language(Path("test.rs")) == Language.RUST

    def test_detect_unsupported(self):
        assert detect_language(Path("test.txt")) is None
        assert detect_language(Path("test.unknown")) is None


class TestCodeParser:
    """Test CodeParser functionality."""

    def setup_method(self):
        self.parser = CodeParser()

    def test_parser_initialization(self):
        assert len(self.parser.supported_languages) == 7
        assert Language.PYTHON in self.parser.supported_languages

    def test_parse_unsupported_extension(self):
        result = self.parser.parse(Path("test.txt"), "content")
        assert not result.parse_success
        assert "Unsupported file extension" in result.parse_error

    @patch("src.parsing.parser._get_tree_sitter_parser")
    def test_parse_no_parser_available(self, mock_get_parser):
        mock_get_parser.return_value = None

        result = self.parser.parse(Path("test.py"), "print('hello')")
        assert not result.parse_success
        assert "Parser not available" in result.parse_error
        assert result.language == Language.PYTHON

    def test_parse_file_read_error(self):
        # Test with non-existent file and no content
        result = self.parser.parse(Path("nonexistent.py"))
        assert not result.parse_success
        assert "Failed to read file" in result.parse_error

    @patch("src.parsing.parser._get_tree_sitter_parser")
    def test_parse_success_mock(self, mock_get_parser):
        # Mock tree-sitter parser
        mock_parser = Mock()
        mock_tree = Mock()
        mock_root_node = Mock()

        # Configure mock tree-sitter node
        mock_root_node.type = "module"
        mock_root_node.start_byte = 0
        mock_root_node.end_byte = 13
        mock_root_node.start_point = Mock(row=0, column=0)
        mock_root_node.end_point = Mock(row=0, column=13)
        mock_root_node.children = []

        mock_tree.root_node = mock_root_node
        mock_parser.parse.return_value = mock_tree
        mock_get_parser.return_value = mock_parser

        result = self.parser.parse(Path("test.py"), "print('hello')")

        assert result.parse_success
        assert result.language == Language.PYTHON
        assert result.ast_root is not None
        assert result.ast_root.type == "module"
        assert result.parse_time_ms > 0

    def test_get_parser_singleton(self):
        parser1 = get_parser()
        parser2 = get_parser()
        assert parser1 is parser2


class TestASTNode:
    """Test ASTNode model."""

    def test_ast_node_creation(self):
        node = ASTNode(
            type="function_definition",
            text="def test(): pass",
            start_byte=0,
            end_byte=16,
            start_point=(0, 0),
            end_point=(0, 16),
        )

        assert node.type == "function_definition"
        assert node.text == "def test(): pass"
        assert node.start_byte == 0
        assert node.end_byte == 16
        assert node.children == []
        assert node.parent is None

    def test_ast_node_to_dict(self):
        child = ASTNode("identifier", "test", 4, 8, (0, 4), (0, 8))
        parent = ASTNode(
            "function_definition", "def test(): pass", 0, 16, (0, 0), (0, 16)
        )
        parent.children.append(child)
        child.parent = parent

        result = parent.to_dict()

        assert result["type"] == "function_definition"
        assert result["text"] == "def test(): pass"
        assert len(result["children"]) == 1
        assert result["children"][0]["type"] == "identifier"


class TestASTCache:
    """Test AST caching functionality."""

    def setup_method(self):
        self.mock_redis = Mock()
        self.cache = ASTCache(self.mock_redis)

    def test_cache_disabled_without_redis(self):
        cache = ASTCache(None)
        assert not cache.enabled

        # Should return None for all operations
        assert cache.get(Path("test.py")) is None
        cache.set(Path("test.py"), Mock())  # Should not raise
        cache.invalidate(Path("test.py"))  # Should not raise

    def test_cache_key_generation(self):
        key = self.cache._get_cache_key(Path("test.py"))
        assert key.startswith("ast_cache:")
        assert "test.py" in key

    def test_cache_miss(self):
        self.mock_redis.hgetall.return_value = {}

        result = self.cache.get(Path("test.py"))
        assert result is None

    @patch("src.parsing.cache.Path.read_bytes")
    def test_cache_invalidation_on_file_change(self, mock_read_bytes):
        # Mock file content change
        mock_read_bytes.return_value = b"new content"

        self.mock_redis.hgetall.return_value = {
            b"file_hash": b"old_hash",
            b"result": b'{"file_path": "test.py", "language": "python", "parse_success": true}',
        }

        result = self.cache.get(Path("test.py"))
        assert result is None
        self.mock_redis.delete.assert_called_once()

    def test_cache_clear(self):
        self.mock_redis.keys.return_value = ["ast_cache:file1", "ast_cache:file2"]

        self.cache.clear()

        self.mock_redis.keys.assert_called_once_with("ast_cache:*")
        self.mock_redis.delete.assert_called_once_with(
            "ast_cache:file1", "ast_cache:file2"
        )


class TestSymbolExtraction:
    """Test symbol extraction functionality."""

    def setup_method(self):
        self.extractor = get_symbol_extractor()

    def test_extractor_initialization(self):
        """Test symbol extractor initialization."""
        assert len(self.extractor.language_extractors) == 7
        assert Language.PYTHON in self.extractor.language_extractors
        assert isinstance(
            self.extractor.language_extractors[Language.PYTHON], PythonExtractor
        )

    def test_python_function_extraction_mock(self):
        """Test Python function extraction with mock AST."""
        # Create mock AST for Python function
        func_node = ASTNode(
            type="function_definition",
            text="def hello_world():\n    print('Hello')",
            start_byte=0,
            end_byte=35,
            start_point=(0, 0),
            end_point=(1, 20),
        )

        # Add identifier child
        name_node = ASTNode(
            type="identifier",
            text="hello_world",
            start_byte=4,
            end_byte=15,
            start_point=(0, 4),
            end_point=(0, 15),
        )
        func_node.children.append(name_node)

        # Create root node
        root_node = ASTNode(
            type="module",
            text="def hello_world():\n    print('Hello')",
            start_byte=0,
            end_byte=35,
            start_point=(0, 0),
            end_point=(1, 20),
        )
        root_node.children.append(func_node)

        # Extract symbols
        symbols, classes, imports, relationships = self.extractor.extract_symbols(
            root_node, Language.PYTHON
        )

        # Verify function was extracted
        assert len(symbols) == 1
        assert symbols[0].name == "hello_world"
        assert symbols[0].type == "function"
        assert symbols[0].line_start == 1
        assert len(classes) == 0
        assert len(imports) == 0

    def test_python_class_extraction_mock(self):
        """Test Python class extraction with mock AST."""
        # Create mock AST for Python class
        class_node = ASTNode(
            type="class_definition",
            text="class TestClass:\n    pass",
            start_byte=0,
            end_byte=24,
            start_point=(0, 0),
            end_point=(1, 8),
        )

        # Add identifier child
        name_node = ASTNode(
            type="identifier",
            text="TestClass",
            start_byte=6,
            end_byte=15,
            start_point=(0, 6),
            end_point=(0, 15),
        )
        class_node.children.append(name_node)

        # Create root node
        root_node = ASTNode(
            type="module",
            text="class TestClass:\n    pass",
            start_byte=0,
            end_byte=24,
            start_point=(0, 0),
            end_point=(1, 8),
        )
        root_node.children.append(class_node)

        # Extract symbols
        symbols, classes, imports, relationships = self.extractor.extract_symbols(
            root_node, Language.PYTHON
        )

        # Verify class was extracted
        assert len(classes) == 1
        assert classes[0].name == "TestClass"
        assert classes[0].line_start == 1
        assert len(symbols) == 0
        assert len(imports) == 0

    def test_python_import_extraction_mock(self):
        """Test Python import extraction with mock AST."""
        # Create mock AST for Python import
        import_node = ASTNode(
            type="import_statement",
            text="import os",
            start_byte=0,
            end_byte=9,
            start_point=(0, 0),
            end_point=(0, 9),
        )

        # Add dotted_name child
        module_node = ASTNode(
            type="dotted_name",
            text="os",
            start_byte=7,
            end_byte=9,
            start_point=(0, 7),
            end_point=(0, 9),
        )
        import_node.children.append(module_node)

        # Create root node
        root_node = ASTNode(
            type="module",
            text="import os",
            start_byte=0,
            end_byte=9,
            start_point=(0, 0),
            end_point=(0, 9),
        )
        root_node.children.append(import_node)

        # Extract symbols
        symbols, classes, imports, relationships = self.extractor.extract_symbols(
            root_node, Language.PYTHON
        )

        # Verify import was extracted
        assert len(imports) == 1
        assert imports[0].module == "os"
        assert imports[0].import_type == "import"
        assert imports[0].line == 1
        assert len(symbols) == 0
        assert len(classes) == 0

    def test_javascript_function_extraction_mock(self):
        """Test JavaScript function extraction with mock AST."""
        # Create mock AST for JavaScript function
        func_node = ASTNode(
            type="function_declaration",
            text="function hello() { console.log('Hello'); }",
            start_byte=0,
            end_byte=42,
            start_point=(0, 0),
            end_point=(0, 42),
        )

        # Add identifier child
        name_node = ASTNode(
            type="identifier",
            text="hello",
            start_byte=9,
            end_byte=14,
            start_point=(0, 9),
            end_point=(0, 14),
        )
        func_node.children.append(name_node)

        # Create root node
        root_node = ASTNode(
            type="program",
            text="function hello() { console.log('Hello'); }",
            start_byte=0,
            end_byte=42,
            start_point=(0, 0),
            end_point=(0, 42),
        )
        root_node.children.append(func_node)

        # Extract symbols
        symbols, classes, imports, relationships = self.extractor.extract_symbols(
            root_node, Language.JAVASCRIPT
        )

        # Verify function was extracted
        assert len(symbols) == 1
        assert symbols[0].name == "hello"
        assert symbols[0].type == "function"
        assert symbols[0].line_start == 1

    def test_unsupported_language(self):
        """Test extraction with unsupported language."""
        root_node = ASTNode(
            type="root",
            text="some code",
            start_byte=0,
            end_byte=9,
            start_point=(0, 0),
            end_point=(0, 9),
        )

        # Create a fake language enum value (this would normally not exist)
        # We'll test with a supported language but empty AST instead
        symbols, classes, imports, relationships = self.extractor.extract_symbols(
            root_node, Language.PYTHON
        )

        # Should return empty lists for empty AST
        assert len(symbols) == 0
        assert len(classes) == 0
        assert len(imports) == 0
        assert len(relationships) == 0


class TestParameterInfo:
    """Test ParameterInfo model."""

    def test_parameter_creation(self):
        """Test parameter info creation."""
        param = ParameterInfo(
            name="arg1", type_hint="str", default_value="'default'", is_variadic=False
        )

        assert param.name == "arg1"
        assert param.type_hint == "str"
        assert param.default_value == "'default'"
        assert not param.is_variadic

    def test_parameter_to_dict(self):
        """Test parameter serialization."""
        param = ParameterInfo(name="arg", type_hint="int", is_variadic=True)
        result = param.to_dict()

        assert result["name"] == "arg"
        assert result["type_hint"] == "int"
        assert result["is_variadic"] is True
        assert result["default_value"] is None


class TestSymbolInfo:
    """Test enhanced SymbolInfo model."""

    def test_symbol_with_parameters(self):
        """Test symbol with parameter information."""
        params = [
            ParameterInfo("self"),
            ParameterInfo("name", "str"),
            ParameterInfo("age", "int", "0"),
        ]

        symbol = SymbolInfo(
            name="create_user",
            type="method",
            line_start=10,
            line_end=15,
            parameters=params,
            return_type="User",
            visibility="public",
            parent_class="UserService",
        )

        assert symbol.name == "create_user"
        assert len(symbol.parameters) == 3
        assert symbol.parameters[0].name == "self"
        assert symbol.parameters[1].type_hint == "str"
        assert symbol.parameters[2].default_value == "0"
        assert symbol.return_type == "User"
        assert symbol.parent_class == "UserService"

    def test_symbol_to_dict_with_parameters(self):
        """Test symbol serialization with parameters."""
        params = [ParameterInfo("arg", "str")]
        symbol = SymbolInfo(
            name="test_func",
            type="function",
            line_start=1,
            line_end=5,
            parameters=params,
            decorators=["@staticmethod"],
            is_async=True,
        )

        result = symbol.to_dict()

        assert result["name"] == "test_func"
        assert len(result["parameters"]) == 1
        assert result["parameters"][0]["name"] == "arg"
        assert result["decorators"] == ["@staticmethod"]
        assert result["is_async"] is True


class TestClassInfo:
    """Test ClassInfo model."""

    def test_class_creation(self):
        """Test class info creation."""
        class_info = ClassInfo(
            name="TestClass",
            line_start=1,
            line_end=20,
            base_classes=["BaseClass"],
            interfaces=["ITestable"],
            methods=["test_method"],
            fields=["test_field"],
            is_abstract=True,
        )

        assert class_info.name == "TestClass"
        assert class_info.base_classes == ["BaseClass"]
        assert class_info.interfaces == ["ITestable"]
        assert class_info.is_abstract is True

    def test_class_to_dict(self):
        """Test class serialization."""
        class_info = ClassInfo(
            name="TestClass", line_start=1, line_end=10, is_interface=True
        )

        result = class_info.to_dict()

        assert result["name"] == "TestClass"
        assert result["is_interface"] is True
        assert result["base_classes"] == []
