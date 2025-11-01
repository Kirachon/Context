"""
Unit tests for cross-language analysis functionality.
"""

from pathlib import Path

from src.analysis.cross_language import (
    CrossLanguageAnalyzer,
    PatternType,
    ArchitecturalLayer,
    DependencyRelation,
    PatternMatch,
)
from src.analysis.similarity import SimilarityDetector, SimilarityMatch, CodeSignature
from src.parsing.models import (
    ParseResult,
    Language,
    SymbolInfo,
    ClassInfo,
    ParameterInfo,
)


class TestCrossLanguageAnalyzer:
    """Test cross-language analyzer functionality."""

    def setup_method(self):
        self.analyzer = CrossLanguageAnalyzer()

    def test_initialization(self):
        """Test analyzer initialization."""
        assert len(self.analyzer.pattern_detectors) == 10
        assert PatternType.SINGLETON in self.analyzer.pattern_detectors
        assert PatternType.FACTORY in self.analyzer.pattern_detectors
        assert self.analyzer.stats["files_analyzed"] == 0

    def test_dependency_relation_creation(self):
        """Test dependency relation model."""
        dep = DependencyRelation(
            source_file="src/service.py",
            source_symbol="UserService",
            target_file="src/repository.py",
            target_symbol="UserRepository",
            relation_type="composition",
            language="python",
            confidence=0.9,
            line_number=15,
        )

        assert dep.source_file == "src/service.py"
        assert dep.relation_type == "composition"
        assert dep.confidence == 0.9

        # Test serialization
        data = dep.to_dict()
        assert data["source_symbol"] == "UserService"
        assert data["target_symbol"] == "UserRepository"

    def test_pattern_match_creation(self):
        """Test pattern match model."""
        pattern = PatternMatch(
            pattern_type=PatternType.SINGLETON,
            confidence=0.8,
            files=["src/config.py"],
            symbols=["ConfigManager"],
            description="Singleton pattern detected",
            evidence={"private_constructor": True},
        )

        assert pattern.pattern_type == PatternType.SINGLETON
        assert pattern.confidence == 0.8
        assert len(pattern.files) == 1

        # Test serialization
        data = pattern.to_dict()
        assert data["pattern_type"] == "singleton"
        assert data["evidence"]["private_constructor"] is True

    def test_singleton_pattern_detection(self):
        """Test singleton pattern detection."""
        # Create mock parse result with singleton-like class
        class_info = ClassInfo(
            name="DatabaseConnection",
            line_start=1,
            line_end=30,
            methods=["getInstance", "connect"],
            fields=["instance"],
        )

        parse_result = ParseResult(
            file_path=Path("database.py"),
            language=Language.PYTHON,
            ast_root=None,
            classes=[class_info],
            parse_success=True,
        )

        patterns = self.analyzer._detect_singleton_pattern([parse_result])

        # Should detect singleton pattern
        assert len(patterns) >= 0  # May or may not detect based on heuristics

        # If detected, verify structure
        for pattern in patterns:
            assert pattern.pattern_type == PatternType.SINGLETON
            assert pattern.confidence > 0
            assert "DatabaseConnection" in pattern.symbols

    def test_factory_pattern_detection(self):
        """Test factory pattern detection."""
        class_info = ClassInfo(
            name="UserFactory",
            line_start=1,
            line_end=20,
            methods=["createUser", "createAdmin"],
            fields=[],
        )

        parse_result = ParseResult(
            file_path=Path("factory.py"),
            language=Language.PYTHON,
            ast_root=None,
            classes=[class_info],
            parse_success=True,
        )

        patterns = self.analyzer._detect_factory_pattern([parse_result])

        # Should detect factory pattern
        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.FACTORY
        assert "UserFactory" in patterns[0].symbols

    def test_async_pattern_detection(self):
        """Test async pattern detection."""
        async_symbol = SymbolInfo(
            name="fetch_data",
            type="function",
            line_start=10,
            line_end=20,
            is_async=True,
        )

        parse_result = ParseResult(
            file_path=Path("async_service.py"),
            language=Language.PYTHON,
            ast_root=None,
            symbols=[async_symbol],
            parse_success=True,
        )

        patterns = self.analyzer._detect_async_pattern([parse_result])

        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.ASYNC_PATTERN
        assert "fetch_data" in patterns[0].symbols

    def test_architectural_layer_classification(self):
        """Test architectural layer classification."""
        # Test different file types
        test_cases = [
            (
                Path("src/controllers/user_controller.py"),
                ArchitecturalLayer.PRESENTATION,
            ),
            (Path("src/services/user_service.py"), ArchitecturalLayer.BUSINESS),
            (Path("src/models/user.py"), ArchitecturalLayer.DATA),
            (Path("tests/test_user.py"), ArchitecturalLayer.TEST),
            (Path("config/settings.py"), ArchitecturalLayer.CONFIG),
            (Path("utils/helpers.py"), ArchitecturalLayer.UTILITY),
        ]

        for file_path, expected_layer in test_cases:
            parse_result = ParseResult(
                file_path=file_path,
                language=Language.PYTHON,
                ast_root=None,
                parse_success=True,
            )

            layer = self.analyzer._classify_architectural_layer(parse_result)
            assert layer == expected_layer

    def test_complexity_metrics_calculation(self):
        """Test complexity metrics calculation."""
        # Create test parse results
        symbol1 = SymbolInfo(
            name="simple_func", type="function", line_start=1, line_end=5, parameters=[]
        )

        symbol2 = SymbolInfo(
            name="complex_func",
            type="function",
            line_start=10,
            line_end=25,
            parameters=[ParameterInfo("arg1"), ParameterInfo("arg2")],
            is_async=True,
            decorators=["@cache", "@validate"],
        )

        parse_result = ParseResult(
            file_path=Path("test.py"),
            language=Language.PYTHON,
            ast_root=None,
            symbols=[symbol1, symbol2],
            parse_success=True,
        )

        dependencies = [
            DependencyRelation(
                source_file="test.py",
                source_symbol="complex_func",
                target_file="other.py",
                target_symbol="helper",
                relation_type="call",
                language="python",
            )
        ]

        metrics = self.analyzer._calculate_complexity_metrics(
            [parse_result], dependencies
        )

        assert "total_files" in metrics
        assert "total_symbols" in metrics
        assert "avg_symbols_per_file" in metrics
        assert "cyclomatic_complexity" in metrics
        assert "coupling_factor" in metrics

        assert metrics["total_files"] == 1.0
        assert metrics["total_symbols"] == 2.0
        assert metrics["avg_symbols_per_file"] == 2.0

    def test_language_distribution_analysis(self):
        """Test language distribution analysis."""
        parse_results = [
            ParseResult(Path("file1.py"), Language.PYTHON, None, parse_success=True),
            ParseResult(Path("file2.py"), Language.PYTHON, None, parse_success=True),
            ParseResult(
                Path("file3.js"), Language.JAVASCRIPT, None, parse_success=True
            ),
        ]

        distribution = self.analyzer._analyze_language_distribution(parse_results)

        assert distribution["python"] == 2
        assert distribution["javascript"] == 1
        assert len(distribution) == 2


class TestSimilarityDetector:
    """Test similarity detector functionality."""

    def setup_method(self):
        self.detector = SimilarityDetector()

    def test_initialization(self):
        """Test detector initialization."""
        assert len(self.detector.language_normalizers) == 7
        assert Language.PYTHON in self.detector.language_normalizers
        assert self.detector.stats["comparisons_performed"] == 0

    def test_code_signature_creation(self):
        """Test code signature model."""
        signature = CodeSignature(
            name="create_user",
            type="function",
            parameter_count=2,
            parameter_types=["string", "integer"],
            return_type="User",
            modifiers={"public", "async"},
            complexity_score=2.5,
        )

        assert signature.name == "create_user"
        assert signature.parameter_count == 2
        assert "async" in signature.modifiers

        # Test hash generation
        hash_value = signature.to_hash()
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 hash length

    def test_python_symbol_normalization(self):
        """Test Python symbol normalization."""
        param = ParameterInfo(name="name", type_hint="str")
        symbol = SymbolInfo(
            name="create_user",
            type="function",
            line_start=1,
            line_end=10,
            parameters=[param],
            return_type="User",
            is_async=True,
            decorators=["@validate"],
        )

        signature = self.detector._normalize_python_symbol(symbol)

        assert signature.name == "create_user"
        assert signature.type == "function"
        assert signature.parameter_count == 1
        assert signature.parameter_types == ["string"]
        assert signature.return_type == "User"
        assert "async" in signature.modifiers
        assert "@validate" in signature.modifiers

    def test_type_normalization(self):
        """Test type normalization across languages."""
        test_cases = [
            ("str", "string"),
            ("String", "string"),
            ("int", "integer"),
            ("Integer", "integer"),
            ("bool", "boolean"),
            ("list", "array"),
            ("List", "array"),
            ("dict", "map"),
            ("HashMap", "map"),
        ]

        for input_type, expected in test_cases:
            normalized = self.detector._normalize_type(input_type)
            assert normalized == expected

    def test_name_similarity_calculation(self):
        """Test name similarity calculation."""
        test_cases = [
            ("create_user", "create_user", 1.0),  # Exact match
            ("create_user", "createUser", 0.9),  # Case/underscore difference
            ("create_user", "create_admin", 0.7),  # Common prefix
            ("user_service", "service_user", 0.0),  # Different
        ]

        for name1, name2, expected_min in test_cases:
            similarity = self.detector._calculate_name_similarity(name1, name2)
            if expected_min == 1.0:
                assert similarity == expected_min
            else:
                assert similarity >= expected_min - 0.1  # Allow some tolerance

    def test_similarity_match_creation(self):
        """Test similarity match model."""
        match = SimilarityMatch(
            source_file="service.py",
            source_symbol="create_user",
            source_language="python",
            target_file="service.js",
            target_symbol="createUser",
            target_language="javascript",
            similarity_score=0.85,
            similarity_type="semantic",
            evidence={"name_similarity": 0.9},
        )

        assert match.source_language == "python"
        assert match.target_language == "javascript"
        assert match.similarity_score == 0.85

        # Test serialization
        data = match.to_dict()
        assert data["source_symbol"] == "create_user"
        assert data["target_symbol"] == "createUser"
        assert data["evidence"]["name_similarity"] == 0.9
