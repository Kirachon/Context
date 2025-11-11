"""
Unit tests for Intelligent Search Engine

Tests all components of the intelligent search system.
"""

import unittest
from datetime import datetime

from src.search.intelligent import (
    QueryParser,
    QueryExpander,
    ContextCollector,
    ContextRanker,
    SearchTemplateManager,
    IntelligentSearchEngine,
    Intent,
    EntityType,
    SearchContext,
    BoostFactors,
)


class TestQueryParser(unittest.TestCase):
    """Test query parser"""

    def setUp(self):
        self.parser = QueryParser(use_spacy=False)

    def test_parse_find_intent(self):
        """Test finding find intent"""
        parsed = self.parser.parse("find user authentication")
        self.assertEqual(parsed.intent, Intent.FIND)

    def test_parse_list_intent(self):
        """Test finding list intent"""
        parsed = self.parser.parse("list all API endpoints")
        self.assertEqual(parsed.intent, Intent.LIST)

    def test_parse_show_intent(self):
        """Test finding show intent"""
        parsed = self.parser.parse("show me the config")
        self.assertEqual(parsed.intent, Intent.SHOW)

    def test_keyword_extraction(self):
        """Test keyword extraction"""
        parsed = self.parser.parse("find user authentication logic")
        self.assertIn("user", parsed.keywords)
        self.assertIn("authentication", parsed.keywords)
        self.assertIn("logic", parsed.keywords)

    def test_query_expansion(self):
        """Test that queries are expanded"""
        parsed = self.parser.parse("authentication")
        self.assertTrue(len(parsed.expanded_terms) > 1)
        # Should expand auth to related terms
        expanded_lower = [t.lower() for t in parsed.expanded_terms]
        self.assertTrue(
            any(term in expanded_lower for term in ["auth", "login", "oauth"])
        )

    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        parsed = self.parser.parse("find authentication")
        self.assertGreater(parsed.confidence, 0)
        self.assertLessEqual(parsed.confidence, 1.0)


class TestQueryExpander(unittest.TestCase):
    """Test query expander"""

    def setUp(self):
        self.expander = QueryExpander()

    def test_synonym_expansion(self):
        """Test synonym expansion"""
        expansion = self.expander.expand("auth")
        # Should have synonyms
        self.assertGreater(len(expansion.expanded_terms), 0)
        self.assertIn("auth", expansion.synonyms)

    def test_acronym_expansion(self):
        """Test acronym expansion"""
        expansion = self.expander.expand("API")
        # Should expand API acronym
        self.assertIn("API", expansion.acronym_expansions)
        self.assertEqual(
            expansion.acronym_expansions["API"],
            "Application Programming Interface"
        )

    def test_related_concepts(self):
        """Test related concept expansion"""
        expansion = self.expander.expand("authentication")
        # Should have related concepts
        self.assertGreater(len(expansion.related_concepts), 0)

    def test_expand_concept(self):
        """Test expanding a single concept"""
        terms = self.expander.expand_concept("auth")
        self.assertIn("auth", terms)
        self.assertIn("authentication", terms)

    def test_get_synonyms(self):
        """Test getting synonyms for a term"""
        synonyms = self.expander.get_synonyms("auth")
        self.assertGreater(len(synonyms), 0)
        self.assertIn("authentication", synonyms)

    def test_is_code_concept(self):
        """Test identifying code concepts"""
        self.assertTrue(self.expander.is_code_concept("auth"))
        self.assertTrue(self.expander.is_code_concept("API"))
        self.assertFalse(self.expander.is_code_concept("randomwordxyz"))


class TestContextCollector(unittest.TestCase):
    """Test context collector"""

    def setUp(self):
        self.collector = ContextCollector()

    def test_track_file_access(self):
        """Test tracking file access"""
        self.collector.track_file_access("user1", "file1.py")
        context = self.collector.collect("user1")
        self.assertIn("file1.py", context.recent_files)

    def test_set_current_file(self):
        """Test setting current file"""
        self.collector.set_current_file("user1", "file1.py")
        context = self.collector.collect("user1")
        self.assertEqual(context.current_file, "file1.py")

    def test_recent_files(self):
        """Test recent files tracking"""
        files = ["file1.py", "file2.py", "file3.py"]
        for file in files:
            self.collector.track_file_access("user1", file)

        context = self.collector.collect("user1")
        # All files should be in recent
        for file in files:
            self.assertIn(file, context.recent_files)

    def test_frequent_files(self):
        """Test frequent files tracking"""
        # Access file1 multiple times
        for _ in range(5):
            self.collector.track_file_access("user1", "file1.py")
        self.collector.track_file_access("user1", "file2.py")

        context = self.collector.collect("user1")
        # file1 should be first in frequent list
        self.assertEqual(context.frequent_files[0], "file1.py")

    def test_query_tracking(self):
        """Test query tracking"""
        queries = ["query1", "query2", "query3"]
        for query in queries:
            self.collector.track_query("user1", query)

        context = self.collector.collect("user1")
        for query in queries:
            self.assertIn(query, context.recent_queries)

    def test_team_patterns(self):
        """Test team pattern tracking"""
        # Multiple users access same file
        for i in range(3):
            self.collector.track_file_access(f"user{i}", "popular.py")

        context = self.collector.collect("user1")
        self.assertIn("popular.py", context.team_patterns)

    def test_project_inference(self):
        """Test project inference from file path"""
        self.collector.set_current_file("user1", "backend/src/auth.py")
        context = self.collector.collect("user1")
        # Should infer project from path
        self.assertIsNotNone(context.current_project)


class TestContextRanker(unittest.TestCase):
    """Test context ranker"""

    def setUp(self):
        self.ranker = ContextRanker()

    def test_current_file_boost(self):
        """Test current file boost"""
        results = [
            {"file_path": "/projects/myapp/frontend/src/app.tsx", "similarity_score": 0.8},
            {"file_path": "/projects/myapp/backend/src/api.py", "similarity_score": 0.9},
        ]

        context = SearchContext(
            user_id="user1",
            current_file="/projects/myapp/frontend/src/index.tsx",
            current_project="frontend",
            recent_files=[],
            frequent_files=[]
        )

        ranked = self.ranker.rank(results, context)

        # Frontend file should get boost
        frontend_result = next(r for r in ranked if "frontend" in r.file_path)
        self.assertGreater(
            frontend_result.boost_breakdown.current_file_boost,
            0
        )

    def test_recent_files_boost(self):
        """Test recent files boost"""
        results = [
            {"file_path": "file1.py", "similarity_score": 0.8},
            {"file_path": "file2.py", "similarity_score": 0.8},
        ]

        context = SearchContext(
            user_id="user1",
            recent_files=["file1.py"],
            frequent_files=[]
        )

        ranked = self.ranker.rank(results, context)

        # file1 should get boost
        file1_result = next(r for r in ranked if r.file_path == "file1.py")
        self.assertGreater(
            file1_result.boost_breakdown.recent_files_boost,
            0
        )

    def test_frequent_files_boost(self):
        """Test frequent files boost"""
        results = [
            {"file_path": "file1.py", "similarity_score": 0.8},
            {"file_path": "file2.py", "similarity_score": 0.8},
        ]

        context = SearchContext(
            user_id="user1",
            recent_files=[],
            frequent_files=["file1.py"]
        )

        ranked = self.ranker.rank(results, context)

        # file1 should get boost
        file1_result = next(r for r in ranked if r.file_path == "file1.py")
        self.assertGreater(
            file1_result.boost_breakdown.frequent_files_boost,
            0
        )

    def test_team_patterns_boost(self):
        """Test team patterns boost"""
        results = [
            {"file_path": "file1.py", "similarity_score": 0.8},
            {"file_path": "file2.py", "similarity_score": 0.8},
        ]

        context = SearchContext(
            user_id="user1",
            recent_files=[],
            frequent_files=[],
            team_patterns={"file1.py": 0.9}
        )

        ranked = self.ranker.rank(results, context)

        # file1 should get boost
        file1_result = next(r for r in ranked if r.file_path == "file1.py")
        self.assertGreater(
            file1_result.boost_breakdown.team_patterns_boost,
            0
        )

    def test_ranking_order(self):
        """Test that results are properly ranked"""
        results = [
            {"file_path": "file1.py", "similarity_score": 0.7},
            {"file_path": "file2.py", "similarity_score": 0.9},
        ]

        context = SearchContext(
            user_id="user1",
            recent_files=["file1.py"],  # Boost file1
            frequent_files=[]
        )

        ranked = self.ranker.rank(results, context)

        # file1 should rank higher despite lower base score
        self.assertEqual(ranked[0].file_path, "file1.py")
        self.assertGreater(ranked[0].final_score, ranked[1].final_score)


class TestSearchTemplateManager(unittest.TestCase):
    """Test search template manager"""

    def setUp(self):
        self.manager = SearchTemplateManager()

    def test_list_templates(self):
        """Test listing templates"""
        templates = self.manager.list_templates()
        self.assertGreater(len(templates), 0)

    def test_get_template(self):
        """Test getting a template"""
        template = self.manager.get_template("api_endpoints")
        self.assertIsNotNone(template)
        self.assertEqual(template.name, "api_endpoints")

    def test_apply_template(self):
        """Test applying a template"""
        query = self.manager.apply_template("api_endpoints")
        self.assertIsNotNone(query)
        self.assertIn("endpoint", query.lower())

    def test_apply_template_with_params(self):
        """Test applying template with parameters"""
        query = self.manager.apply_template("components", component_name="Button")
        self.assertIsNotNone(query)
        self.assertIn("Button", query)

    def test_suggest_templates(self):
        """Test template suggestions"""
        suggestions = self.manager.suggest_templates("find login logic")
        self.assertGreater(len(suggestions), 0)
        # Should suggest authentication template
        names = [t.name for t in suggestions]
        self.assertIn("authentication", names)

    def test_add_custom_template(self):
        """Test adding custom template"""
        from src.search.intelligent.models import SearchTemplate

        template = SearchTemplate(
            name="custom_test",
            description="Test template",
            query_pattern="test query",
            intent=Intent.FIND
        )
        self.manager.add_custom_template(template)

        retrieved = self.manager.get_template("custom_test")
        self.assertEqual(retrieved.name, "custom_test")

    def test_remove_custom_template(self):
        """Test removing custom template"""
        from src.search.intelligent.models import SearchTemplate

        template = SearchTemplate(
            name="custom_test",
            description="Test template",
            query_pattern="test query",
            intent=Intent.FIND
        )
        self.manager.add_custom_template(template)
        self.manager.remove_custom_template("custom_test")

        retrieved = self.manager.get_template("custom_test")
        self.assertIsNone(retrieved)


class TestIntelligentSearchEngine(unittest.TestCase):
    """Test end-to-end intelligent search engine"""

    def setUp(self):
        self.engine = IntelligentSearchEngine(use_spacy=False)

    def test_parse_query(self):
        """Test parsing query"""
        parsed = self.engine.parse_query("find authentication")
        self.assertEqual(parsed.intent, Intent.FIND)

    def test_expand_query(self):
        """Test expanding query"""
        expansion = self.engine.expand_query("auth")
        self.assertGreater(len(expansion.expanded_terms), 0)

    def test_suggest_templates(self):
        """Test template suggestions"""
        suggestions = self.engine.suggest_templates("find login")
        self.assertGreater(len(suggestions), 0)

    def test_set_current_file(self):
        """Test setting current file"""
        self.engine.set_current_file("user1", "test.py")
        context = self.engine.get_context("user1")
        self.assertEqual(context.current_file, "test.py")

    def test_track_file_access(self):
        """Test tracking file access"""
        self.engine.track_file_access("user1", "test.py")
        context = self.engine.get_context("user1")
        self.assertIn("test.py", context.recent_files)


class TestBoostFactors(unittest.TestCase):
    """Test boost factors"""

    def test_boost_calculation(self):
        """Test boost total calculation"""
        boosts = BoostFactors(
            current_file_boost=1.0,
            recent_files_boost=0.5,
            frequent_files_boost=0.3,
        )

        total = boosts.total_boost()
        expected = 1.0 * 2.0 + 0.5 * 1.5 + 0.3 * 1.3
        self.assertAlmostEqual(total, expected, places=2)

    def test_to_dict(self):
        """Test conversion to dictionary"""
        boosts = BoostFactors(
            current_file_boost=1.0,
            recent_files_boost=0.5,
        )

        boost_dict = boosts.to_dict()
        self.assertIn("current_file", boost_dict)
        self.assertIn("recent_files", boost_dict)
        self.assertIn("total", boost_dict)


if __name__ == "__main__":
    unittest.main()
