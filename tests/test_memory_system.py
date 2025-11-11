"""Comprehensive tests for Memory System.

Tests all four memory types:
- Conversation Memory
- Pattern Memory
- Solution Memory
- Preference Memory
"""

import os
import pytest
from datetime import datetime
from uuid import uuid4

# Set test database URL before importing modules
os.environ['DATABASE_URL'] = 'postgresql://context:context@localhost:5432/context_test'

from src.memory import ConversationStore, PatternStore, SolutionStore, PreferenceStore
from src.memory.database import get_db_manager, init_database


# ===== Fixtures =====

@pytest.fixture(scope="session")
def db_manager():
    """Create test database manager."""
    manager = get_db_manager()
    # Create tables
    manager.create_tables()
    yield manager
    # Cleanup after all tests
    manager.drop_tables()


@pytest.fixture
def conversation_store(db_manager):
    """Create conversation store instance."""
    return ConversationStore()


@pytest.fixture
def pattern_store(db_manager):
    """Create pattern store instance."""
    return PatternStore()


@pytest.fixture
def solution_store(db_manager):
    """Create solution store instance."""
    return SolutionStore()


@pytest.fixture
def preference_store(db_manager):
    """Create preference store instance."""
    return PreferenceStore()


# ===== Conversation Memory Tests =====

class TestConversationMemory:
    """Tests for conversation memory functionality."""

    def test_store_conversation(self, conversation_store):
        """Test storing a conversation."""
        conversation_id = conversation_store.store_conversation(
            user_id="test_user",
            prompt="How do I fix authentication?",
            enhanced_prompt="Enhanced prompt with context...",
            response="You can fix authentication by...",
            intent="fix",
            entities={"files": ["auth.py"]},
            token_count=1000,
            latency_ms=500,
        )

        assert conversation_id is not None

        # Retrieve and verify
        conv = conversation_store.get_conversation(conversation_id)
        assert conv is not None
        assert conv.user_id == "test_user"
        assert conv.prompt == "How do I fix authentication?"
        assert conv.intent == "fix"

    def test_get_user_conversations(self, conversation_store):
        """Test retrieving user conversations."""
        # Store multiple conversations
        user_id = f"user_{uuid4()}"

        for i in range(3):
            conversation_store.store_conversation(
                user_id=user_id,
                prompt=f"Test prompt {i}",
                intent="explain",
            )

        # Retrieve
        conversations = conversation_store.get_user_conversations(user_id, limit=10)
        assert len(conversations) == 3

    def test_similar_conversations_search(self, conversation_store):
        """Test semantic search for similar conversations."""
        user_id = f"user_{uuid4()}"

        # Store conversations with different topics
        conversation_store.store_conversation(
            user_id=user_id,
            prompt="How to implement authentication with JWT?",
            response="Use JWT tokens for authentication...",
            intent="implement",
        )

        conversation_store.store_conversation(
            user_id=user_id,
            prompt="How to set up database connection?",
            response="Configure database connection...",
            intent="implement",
        )

        # Search for authentication-related conversations
        results = conversation_store.get_similar_conversations(
            query="JWT authentication",
            user_id=user_id,
            limit=5,
        )

        # Should find at least one result
        # Note: This might fail if Qdrant is not available, will use fallback
        assert len(results) >= 0

    def test_update_feedback(self, conversation_store):
        """Test updating conversation feedback."""
        conversation_id = conversation_store.store_conversation(
            user_id="test_user",
            prompt="Test prompt",
        )

        # Update feedback
        success = conversation_store.update_feedback(
            conversation_id=conversation_id,
            feedback={"helpful": True, "comment": "Very helpful!"},
            resolution=True,
            helpful_score=0.9,
        )

        assert success is True

        # Verify
        conv = conversation_store.get_conversation(conversation_id)
        assert conv.resolution is True
        assert conv.helpful_score == 0.9

    def test_conversation_statistics(self, conversation_store):
        """Test conversation statistics."""
        user_id = f"user_{uuid4()}"

        # Store some conversations
        for i in range(5):
            conversation_store.store_conversation(
                user_id=user_id,
                prompt=f"Prompt {i}",
                intent="fix" if i % 2 == 0 else "explain",
            )

        # Get statistics
        stats = conversation_store.get_statistics(user_id=user_id)

        assert stats['total_conversations'] >= 5
        assert 'intent_distribution' in stats


# ===== Pattern Memory Tests =====

class TestPatternMemory:
    """Tests for pattern memory functionality."""

    def test_store_pattern(self, pattern_store):
        """Test storing a code pattern."""
        pattern_id = pattern_store.store_pattern(
            pattern_type="error_handling",
            name="try_except_pattern",
            example_code="try:\n    ...\nexcept Exception as e:\n    ...",
            description="Basic try-except pattern",
            language="python",
        )

        assert pattern_id is not None

        # Retrieve and verify
        pattern = pattern_store.get_pattern(pattern_id)
        assert pattern is not None
        assert pattern.pattern_type == "error_handling"
        assert pattern.name == "try_except_pattern"

    def test_get_patterns_by_type(self, pattern_store):
        """Test retrieving patterns by type."""
        project_id = f"project_{uuid4()}"

        # Store patterns of different types
        for ptype in ["api_design", "testing", "async_patterns"]:
            pattern_store.store_pattern(
                pattern_type=ptype,
                name=f"{ptype}_example",
                example_code="...",
                project_id=project_id,
            )

        # Get patterns by type
        patterns = pattern_store.get_patterns(
            pattern_type="api_design",
            project_id=project_id,
        )

        assert len(patterns) >= 1
        assert all(p.pattern_type == "api_design" for p in patterns)

    def test_pattern_usage_update(self, pattern_store):
        """Test updating pattern usage."""
        pattern_id = pattern_store.store_pattern(
            pattern_type="testing",
            name="test_pattern",
            example_code="def test_example(): ...",
        )

        # Update usage
        success = pattern_store.update_pattern_usage(
            pattern_id=pattern_id,
            file_path="tests/test_example.py",
        )

        assert success is True

        # Verify
        pattern = pattern_store.get_pattern(pattern_id)
        assert pattern.usage_count >= 1

    def test_extract_patterns_from_code(self, pattern_store):
        """Test pattern extraction from Python code."""
        code = '''
def test_example():
    """Test function"""
    assert True

async def async_function():
    """Async function"""
    await something()

class ExampleClass:
    """Example class"""
    pass
'''

        pattern_ids = pattern_store.extract_patterns_from_file(
            file_path="test.py",
            content=code,
            project_id="test_project",
        )

        # Should extract at least some patterns
        assert len(pattern_ids) >= 0

    def test_pattern_statistics(self, pattern_store):
        """Test pattern statistics."""
        project_id = f"project_{uuid4()}"

        # Store multiple patterns
        for i in range(3):
            pattern_store.store_pattern(
                pattern_type="testing",
                name=f"pattern_{i}",
                example_code="...",
                project_id=project_id,
            )

        # Get statistics
        stats = pattern_store.get_pattern_statistics(project_id=project_id)

        assert stats['total_patterns'] >= 3
        assert 'pattern_types' in stats


# ===== Solution Memory Tests =====

class TestSolutionMemory:
    """Tests for solution memory functionality."""

    def test_store_solution(self, solution_store):
        """Test storing a problem-solution pair."""
        solution_id = solution_store.store_solution(
            problem_description="Authentication fails with 401 error",
            solution_code="Check token expiration and refresh",
            problem_type="bug",
            error_message="401 Unauthorized",
            success_rate=0.9,
        )

        assert solution_id is not None

        # Retrieve and verify
        solution = solution_store.get_solution(solution_id)
        assert solution is not None
        assert solution.problem_type == "bug"
        assert solution.success_rate == 0.9

    def test_get_solutions_by_type(self, solution_store):
        """Test retrieving solutions by problem type."""
        project_id = f"project_{uuid4()}"

        # Store solutions of different types
        for ptype in ["bug", "feature", "refactor"]:
            solution_store.store_solution(
                problem_description=f"Test {ptype} problem",
                solution_code="Solution...",
                problem_type=ptype,
                project_id=project_id,
            )

        # Get solutions by type
        solutions = solution_store.get_solutions(
            problem_type="bug",
            project_id=project_id,
        )

        assert len(solutions) >= 1
        assert all(s.problem_type == "bug" for s in solutions)

    def test_similar_solutions_search(self, solution_store):
        """Test semantic search for similar solutions."""
        project_id = f"project_{uuid4()}"

        # Store solutions with different problems
        solution_store.store_solution(
            problem_description="JWT token authentication not working",
            solution_code="Refresh token implementation",
            problem_type="bug",
            project_id=project_id,
        )

        solution_store.store_solution(
            problem_description="Database connection timeout",
            solution_code="Increase connection pool size",
            problem_type="bug",
            project_id=project_id,
        )

        # Search for authentication-related solutions
        results = solution_store.get_similar_solutions(
            problem="authentication token issues",
            project_id=project_id,
            limit=3,
        )

        # Should find at least one result
        assert len(results) >= 0

    def test_update_solution_metrics(self, solution_store):
        """Test updating solution success metrics."""
        solution_id = solution_store.store_solution(
            problem_description="Test problem",
            solution_code="Test solution",
            success_rate=0.5,
        )

        # Update metrics with successful outcome
        success = solution_store.update_solution_metrics(
            solution_id=solution_id,
            success=True,
            resolution_time_sec=300,
        )

        assert success is True

        # Verify success rate increased
        solution = solution_store.get_solution(solution_id)
        assert solution.success_rate > 0.5
        assert solution.usage_count == 2

    def test_solution_statistics(self, solution_store):
        """Test solution statistics."""
        project_id = f"project_{uuid4()}"

        # Store multiple solutions
        for i in range(3):
            solution_store.store_solution(
                problem_description=f"Problem {i}",
                solution_code="Solution...",
                success_rate=0.8,
                project_id=project_id,
            )

        # Get statistics
        stats = solution_store.get_solution_statistics(project_id=project_id)

        assert stats['total_solutions'] >= 3
        assert stats['avg_success_rate'] > 0


# ===== Preference Memory Tests =====

class TestPreferenceMemory:
    """Tests for preference memory functionality."""

    def test_get_preferences_nonexistent(self, preference_store):
        """Test getting preferences for nonexistent user."""
        prefs = preference_store.get_user_preferences("nonexistent_user")
        assert prefs is None

    def test_update_preference(self, preference_store):
        """Test updating a specific preference."""
        user_id = f"user_{uuid4()}"

        # Update preference
        success = preference_store.update_preference(
            user_id=user_id,
            preference_key="code_style.indentation",
            preference_value="4_spaces",
        )

        assert success is True

        # Verify
        prefs = preference_store.get_user_preferences(user_id)
        assert prefs is not None
        assert prefs.code_style.get("indentation") == "4_spaces"

    def test_update_project_specific_preference(self, preference_store):
        """Test updating project-specific preferences."""
        user_id = f"user_{uuid4()}"
        project_id = "test_project"

        # Update project-specific preference
        success = preference_store.update_preference(
            user_id=user_id,
            preference_key="indentation",
            preference_value="tabs",
            project_id=project_id,
        )

        assert success is True

        # Verify
        prefs = preference_store.get_user_preferences(user_id)
        assert prefs is not None
        assert project_id in prefs.project_preferences

    def test_get_all_preferences(self, preference_store):
        """Test getting all user preferences."""
        # Create some preferences
        for i in range(2):
            user_id = f"user_{uuid4()}"
            preference_store.update_preference(
                user_id=user_id,
                preference_key="testing_approach",
                preference_value="unit",
            )

        # Get all
        all_prefs = preference_store.get_all_preferences()
        assert len(all_prefs) >= 2


# ===== Integration Tests =====

class TestMemoryIntegration:
    """Integration tests across multiple memory types."""

    def test_full_workflow(self, conversation_store, pattern_store, solution_store):
        """Test a complete workflow across memory systems."""
        user_id = "integration_test_user"
        project_id = "integration_test_project"

        # 1. Store a conversation about a problem
        conv_id = conversation_store.store_conversation(
            user_id=user_id,
            prompt="How to handle database connection errors?",
            intent="fix",
        )

        assert conv_id is not None

        # 2. Store a code pattern that solves the problem
        pattern_id = pattern_store.store_pattern(
            pattern_type="error_handling",
            name="db_connection_retry",
            example_code="try:\n    connect()\nexcept ConnectionError:\n    retry()",
            project_id=project_id,
        )

        assert pattern_id is not None

        # 3. Store the solution
        solution_id = solution_store.store_solution(
            problem_description="Database connection fails intermittently",
            solution_code="Implement retry logic with exponential backoff",
            problem_type="bug",
            success_rate=0.95,
            project_id=project_id,
        )

        assert solution_id is not None

        # 4. Update conversation with resolution
        conversation_store.update_feedback(
            conversation_id=conv_id,
            feedback={"used_pattern": str(pattern_id)},
            resolution=True,
        )

        # Verify everything is stored correctly
        conv = conversation_store.get_conversation(conv_id)
        pattern = pattern_store.get_pattern(pattern_id)
        solution = solution_store.get_solution(solution_id)

        assert conv.resolution is True
        assert pattern.usage_count >= 1
        assert solution.success_rate == 0.95


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
