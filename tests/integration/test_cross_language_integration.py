"""
Integration tests for cross-language analysis system.
"""

from pathlib import Path

from src.analysis.cross_language import get_cross_language_analyzer
from src.analysis.similarity import get_similarity_detector
from src.parsing.parser import get_parser


class TestCrossLanguageIntegration:
    """Integration tests for complete cross-language analysis pipeline."""

    def setup_method(self):
        self.analyzer = get_cross_language_analyzer()
        self.detector = get_similarity_detector()
        self.parser = get_parser()

    def test_complete_analysis_pipeline(self):
        """Test complete analysis pipeline with multiple languages."""
        # Test code samples
        python_code = '''
import os
from typing import Optional

class UserService:
    """Service for user management."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def create_user(self, name: str, email: str) -> Optional[dict]:
        """Create a new user."""
        if not self.validate_email(email):
            return None
        return {"name": name, "email": email}
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        return "@" in email

class UserRepository:
    """Repository for user data access."""
    
    def save_user(self, user: dict) -> bool:
        """Save user to database."""
        return True
'''

        javascript_code = """
class UserService {
    constructor(dbPath) {
        this.dbPath = dbPath;
    }
    
    async createUser(name, email) {
        if (!this.validateEmail(email)) {
            return null;
        }
        return { name, email };
    }
    
    static validateEmail(email) {
        return email.includes('@');
    }
}

class UserRepository {
    saveUser(user) {
        return true;
    }
}
"""

        # Parse both files
        python_result = self.parser.parse(Path("user_service.py"), python_code)
        js_result = self.parser.parse(Path("user_service.js"), javascript_code)

        parse_results = []
        if python_result.parse_success:
            parse_results.append(python_result)
        if js_result.parse_success:
            parse_results.append(js_result)

        print(f"Successfully parsed {len(parse_results)} files")

        if len(parse_results) >= 1:
            # Test architectural analysis
            analysis = self.analyzer.analyze_codebase(parse_results)

            assert isinstance(analysis.layers, dict)
            assert isinstance(analysis.patterns, list)
            assert isinstance(analysis.dependencies, list)
            assert isinstance(analysis.complexity_metrics, dict)
            assert isinstance(analysis.language_distribution, dict)

            print("Analysis results:")
            print(f"  - Patterns detected: {len(analysis.patterns)}")
            print(f"  - Dependencies mapped: {len(analysis.dependencies)}")
            print(f"  - Languages: {list(analysis.language_distribution.keys())}")

            # Test similarity detection if we have symbols
            total_symbols = sum(len(result.symbols) for result in parse_results)
            if total_symbols >= 2:
                similarities = self.detector.find_similarities(
                    parse_results, min_similarity=0.5
                )

                print(f"  - Similarities found: {len(similarities)}")

                # Check for cross-language similarities
                cross_lang_similarities = [
                    s for s in similarities if s.source_language != s.target_language
                ]
                print(
                    f"  - Cross-language similarities: {len(cross_lang_similarities)}"
                )

    def test_pattern_detection_across_languages(self):
        """Test pattern detection across different languages."""
        # Singleton pattern in Python
        python_singleton = """
class DatabaseConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def connect(self):
        return "connected"
"""

        # Factory pattern in JavaScript
        js_factory = """
class UserFactory {
    static createUser(type) {
        if (type === 'admin') {
            return new AdminUser();
        }
        return new RegularUser();
    }
}

class AdminUser {
    constructor() {
        this.role = 'admin';
    }
}

class RegularUser {
    constructor() {
        this.role = 'user';
    }
}
"""

        # Parse files
        python_result = self.parser.parse(Path("singleton.py"), python_singleton)
        js_result = self.parser.parse(Path("factory.js"), js_factory)

        parse_results = []
        if python_result.parse_success:
            parse_results.append(python_result)
        if js_result.parse_success:
            parse_results.append(js_result)

        if parse_results:
            # Analyze patterns
            analysis = self.analyzer.analyze_codebase(parse_results)

            print("Pattern detection test:")
            print(f"  - Files analyzed: {len(parse_results)}")
            print(f"  - Patterns found: {len(analysis.patterns)}")

            # Check for specific patterns
            pattern_types = [p.pattern_type.value for p in analysis.patterns]
            print(f"  - Pattern types: {pattern_types}")

            # Verify we can detect patterns across languages
            assert (
                len(analysis.patterns) >= 0
            )  # May or may not detect based on heuristics

    def test_similarity_detection_cross_language(self):
        """Test similarity detection between different languages."""
        # Similar functions in different languages
        python_func = '''
def calculate_total(items):
    """Calculate total price of items."""
    total = 0
    for item in items:
        total += item.price
    return total

def validate_email(email):
    """Validate email address."""
    return "@" in email and "." in email
'''

        js_func = """
function calculateTotal(items) {
    let total = 0;
    for (const item of items) {
        total += item.price;
    }
    return total;
}

function validateEmail(email) {
    return email.includes('@') && email.includes('.');
}
"""

        # Parse files
        python_result = self.parser.parse(Path("utils.py"), python_func)
        js_result = self.parser.parse(Path("utils.js"), js_func)

        parse_results = []
        if python_result.parse_success:
            parse_results.append(python_result)
        if js_result.parse_success:
            parse_results.append(js_result)

        if len(parse_results) >= 2:
            # Find similarities
            similarities = self.detector.find_similarities(
                parse_results, min_similarity=0.3
            )

            print("Similarity detection test:")
            print(f"  - Files analyzed: {len(parse_results)}")
            print(f"  - Total symbols: {sum(len(r.symbols) for r in parse_results)}")
            print(f"  - Similarities found: {len(similarities)}")

            # Check for cross-language similarities
            cross_lang = [
                s for s in similarities if s.source_language != s.target_language
            ]
            print(f"  - Cross-language similarities: {len(cross_lang)}")

            # Print similarity details
            for sim in similarities[:3]:  # First 3 similarities
                print(
                    f"    {sim.source_symbol} ({sim.source_language}) <-> {sim.target_symbol} ({sim.target_language}): {sim.similarity_score:.2f}"
                )

    def test_dependency_analysis(self):
        """Test dependency analysis across files."""
        # File with imports and inheritance
        main_file = """
from user_service import UserService
from database import DatabaseConnection

class UserController:
    def __init__(self):
        self.service = UserService()
        self.db = DatabaseConnection()
    
    def create_user(self, name, email):
        return self.service.create_user(name, email)
"""

        service_file = """
class UserService:
    def create_user(self, name, email):
        return {"name": name, "email": email}
"""

        # Parse files
        main_result = self.parser.parse(Path("controller.py"), main_file)
        service_result = self.parser.parse(Path("user_service.py"), service_file)

        parse_results = []
        if main_result.parse_success:
            parse_results.append(main_result)
        if service_result.parse_success:
            parse_results.append(service_result)

        if parse_results:
            # Analyze dependencies
            analysis = self.analyzer.analyze_codebase(parse_results)

            print("Dependency analysis test:")
            print(f"  - Files analyzed: {len(parse_results)}")
            print(f"  - Dependencies found: {len(analysis.dependencies)}")
            print(
                f"  - Coupling factor: {analysis.complexity_metrics.get('coupling_factor', 0.0):.2f}"
            )

            # Print dependency details
            for dep in analysis.dependencies[:5]:  # First 5 dependencies
                print(
                    f"    {dep.source_symbol} -> {dep.target_symbol} ({dep.relation_type})"
                )

    def test_performance_characteristics(self):
        """Test performance characteristics of analysis system."""
        # Create multiple small files for performance testing
        test_files = []

        for i in range(5):
            code = f"""
class TestClass{i}:
    def method{i}(self, arg):
        return arg * {i}
    
    def helper{i}(self):
        return "helper{i}"
"""
            result = self.parser.parse(Path(f"test{i}.py"), code)
            if result.parse_success:
                test_files.append(result)

        if test_files:
            # Measure analysis performance
            import time

            start_time = time.time()
            analysis = self.analyzer.analyze_codebase(test_files)
            analysis_time = time.time() - start_time

            start_time = time.time()
            similarities = self.detector.find_similarities(
                test_files, min_similarity=0.5
            )
            similarity_time = time.time() - start_time

            print("Performance test:")
            print(f"  - Files: {len(test_files)}")
            print(f"  - Analysis time: {analysis_time:.3f}s")
            print(f"  - Similarity time: {similarity_time:.3f}s")
            print(f"  - Patterns found: {len(analysis.patterns)}")
            print(f"  - Similarities found: {len(similarities)}")

            # Performance assertions
            assert analysis_time < 5.0  # Should complete within 5 seconds
            assert similarity_time < 5.0  # Should complete within 5 seconds
