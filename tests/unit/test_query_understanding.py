"""
Unit tests for Query Understanding (Story 2.6)
"""
import pytest
from datetime import datetime
from pathlib import Path

from src.search.query_intent import QueryIntentClassifier, QueryIntent, QueryScope
from src.search.query_enhancement import QueryEnhancer
from src.search.query_history import QueryHistory, QueryRecord


class TestQueryIntentClassifier:
    """Tests for query intent classification"""

    @pytest.fixture
    def classifier(self):
        return QueryIntentClassifier()

    def test_classify_search_intent(self, classifier):
        """Test classification of search intent"""
        result = classifier.classify("find all functions that handle authentication")
        assert result.intent == QueryIntent.SEARCH
        assert result.confidence > 0.5

    def test_classify_understand_intent(self, classifier):
        """Test classification of understand intent"""
        result = classifier.classify("explain how the database connection works")
        assert result.intent == QueryIntent.UNDERSTAND
        assert result.confidence > 0.5

    def test_classify_refactor_intent(self, classifier):
        """Test classification of refactor intent"""
        result = classifier.classify("refactor this code to improve readability")
        assert result.intent == QueryIntent.REFACTOR
        assert result.confidence > 0.5

    def test_classify_debug_intent(self, classifier):
        """Test classification of debug intent"""
        result = classifier.classify("why is this function crashing with null pointer")
        assert result.intent == QueryIntent.DEBUG
        assert result.confidence > 0.5

    def test_classify_optimize_intent(self, classifier):
        """Test classification of optimize intent"""
        result = classifier.classify("optimize this loop for better performance")
        assert result.intent == QueryIntent.OPTIMIZE
        assert result.confidence > 0.5

    def test_extract_entities(self, classifier):
        """Test entity extraction"""
        result = classifier.classify("find UserService and AuthController")
        assert "UserService" in result.entities or "AuthController" in result.entities

    def test_extract_keywords(self, classifier):
        """Test keyword extraction"""
        result = classifier.classify("find authentication functions in user module")
        assert len(result.keywords) > 0
        assert any("auth" in kw.lower() for kw in result.keywords)

    def test_scope_detection_file(self, classifier):
        """Test file scope detection"""
        result = classifier.classify("find functions in this file")
        assert result.scope.level == "file"

    def test_scope_detection_codebase(self, classifier):
        """Test codebase scope detection"""
        result = classifier.classify("find all database queries")
        assert result.scope.level == "codebase"


class TestQueryEnhancer:
    """Tests for query enhancement"""

    @pytest.fixture
    def enhancer(self):
        return QueryEnhancer()

    @pytest.fixture
    def classifier(self):
        return QueryIntentClassifier()

    def test_enhance_query_with_entities(self, enhancer, classifier):
        """Test query enhancement with entities"""
        intent_result = classifier.classify("find UserService")
        enhanced = enhancer.enhance("find UserService", intent_result)
        
        assert enhanced.original_query == "find UserService"
        assert len(enhanced.enhanced_query) > len(enhanced.original_query)
        assert len(enhanced.context_additions) > 0

    def test_enhance_query_with_recent_files(self, enhancer, classifier):
        """Test query enhancement with recent files"""
        intent_result = classifier.classify("find authentication code")
        recent_files = ["src/auth/login.py", "src/auth/token.py"]
        enhanced = enhancer.enhance("find authentication code", intent_result, recent_files=recent_files)
        
        assert "recent" in enhanced.enhanced_query.lower() or len(enhanced.context_additions) > 0

    def test_follow_up_questions_search(self, enhancer, classifier):
        """Test follow-up questions for search intent"""
        intent_result = classifier.classify("find database queries")
        questions = enhancer.get_follow_up_questions(intent_result)
        
        assert len(questions) > 0
        assert any("filter" in q.lower() or "type" in q.lower() for q in questions)

    def test_follow_up_questions_debug(self, enhancer, classifier):
        """Test follow-up questions for debug intent"""
        intent_result = classifier.classify("why is this function crashing with null pointer")
        questions = enhancer.get_follow_up_questions(intent_result)

        assert len(questions) > 0
        assert any("error" in q.lower() or "stack" in q.lower() for q in questions)

    def test_add_recent_change(self, enhancer):
        """Test tracking recent changes"""
        enhancer.add_recent_change("src/module.py")
        enhancer.add_recent_change("src/other.py")
        
        assert len(enhancer.recent_changes) == 2
        assert enhancer.recent_changes[0] == "src/other.py"

    def test_add_pattern(self, enhancer):
        """Test tracking patterns"""
        enhancer.add_pattern("singleton", ["Logger", "Config"])
        
        assert "singleton" in enhancer.common_patterns
        assert "Logger" in enhancer.common_patterns["singleton"]


class TestQueryHistory:
    """Tests for query history"""

    @pytest.fixture
    def history(self):
        return QueryHistory(max_history=100)

    def test_add_query(self, history):
        """Test adding query to history"""
        record = history.add_query("find functions", "search", 5)
        
        assert record.query == "find functions"
        assert record.intent == "search"
        assert record.results_count == 5
        assert len(history.history) == 1

    def test_get_recent(self, history):
        """Test retrieving recent queries"""
        history.add_query("query 1", "search", 5)
        history.add_query("query 2", "understand", 3)
        history.add_query("query 3", "debug", 2)
        
        recent = history.get_recent(2)
        assert len(recent) == 2
        assert recent[0].query == "query 3"

    def test_search_history(self, history):
        """Test searching history"""
        history.add_query("find authentication", "search", 5)
        history.add_query("find database", "search", 3)
        history.add_query("understand logging", "understand", 2)
        
        results = history.search_history("find")
        assert len(results) == 2

    def test_get_by_intent(self, history):
        """Test filtering by intent"""
        history.add_query("query 1", "search", 5)
        history.add_query("query 2", "search", 3)
        history.add_query("query 3", "debug", 2)
        
        search_queries = history.get_by_intent("search")
        assert len(search_queries) == 2

    def test_rate_query(self, history):
        """Test rating query quality"""
        history.add_query("find functions", "search", 5)
        history.rate_query(0, 0.9, "Great results")
        
        assert history.history[0].result_quality == 0.9
        assert history.history[0].notes == "Great results"

    def test_get_high_quality(self, history):
        """Test retrieving high-quality queries"""
        history.add_query("query 1", "search", 5)
        history.add_query("query 2", "search", 3)
        history.add_query("query 3", "debug", 2)
        
        history.rate_query(0, 0.9)
        history.rate_query(1, 0.5)
        history.rate_query(2, 0.8)
        
        high_quality = history.get_high_quality(min_quality=0.7)
        assert len(high_quality) == 2

    def test_get_statistics(self, history):
        """Test history statistics"""
        history.add_query("query 1", "search", 5)
        history.add_query("query 2", "search", 3)
        history.add_query("query 3", "debug", 2)
        
        stats = history.get_statistics()
        assert stats["total_queries"] == 3
        assert stats["intent_distribution"]["search"] == 2
        assert stats["intent_distribution"]["debug"] == 1

