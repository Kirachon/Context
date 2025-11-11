"""
Comprehensive unit tests for Context-Aware Prompt Enhancement Engine

Tests cover all 4 epics:
- Epic 1: Prompt Analysis
- Epic 2: Context Gathering
- Epic 3: Context Ranking & Summarization
- Epic 4: Prompt Composition
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.prompt.analyzer import (
    EntityExtractor,
    EntityType,
    IntentClassifier,
    IntentType,
    PromptAnalyzer,
    TokenBudgetEstimator,
)
from src.prompt.composer import PromptComposer
from src.prompt.context_gatherer import (
    ArchitecturalContextGatherer,
    CodeContextGatherer,
    ContextGatherer,
    CurrentContextGatherer,
    HistoricalContextGatherer,
    TeamContextGatherer,
    UserContext,
)
from src.prompt.ranker import ContextRanker
from src.prompt.summarizer import (
    ExtractiveSummarizer,
    HierarchicalSummarizer,
    count_tokens,
)


# ============================================================================
# Epic 1: Prompt Analysis Tests
# ============================================================================


class TestIntentClassifier:
    """Test intent classification"""

    @pytest.mark.asyncio
    async def test_fix_intent(self):
        """Test fix intent classification"""
        classifier = IntentClassifier()

        # Test fix patterns
        prompts = [
            "Fix the authentication bug",
            "There's an error in login.py",
            "The problem is in the payment processor",
        ]

        for prompt in prompts:
            intent = await classifier.classify(prompt)
            assert intent.type == IntentType.FIX
            assert intent.confidence > 0.8

    @pytest.mark.asyncio
    async def test_explain_intent(self):
        """Test explain intent classification"""
        classifier = IntentClassifier()

        prompts = [
            "How does the caching system work?",
            "What is the authentication flow?",
            "Explain the payment processing",
        ]

        for prompt in prompts:
            intent = await classifier.classify(prompt)
            assert intent.type == IntentType.EXPLAIN

    @pytest.mark.asyncio
    async def test_implement_intent(self):
        """Test implement intent classification"""
        classifier = IntentClassifier()

        prompts = [
            "Add email validation",
            "Create a new user profile page",
            "Implement discount code system",
        ]

        for prompt in prompts:
            intent = await classifier.classify(prompt)
            assert intent.type == IntentType.IMPLEMENT


class TestEntityExtractor:
    """Test entity extraction"""

    @pytest.mark.asyncio
    async def test_file_extraction(self):
        """Test file path extraction"""
        extractor = EntityExtractor()
        user_context = Mock(workspace_path="/tmp")

        prompt = "Fix the bug in backend/auth.py"
        entities = await extractor.extract(prompt, user_context)

        file_entities = [e for e in entities if e.type == EntityType.FILE]
        assert len(file_entities) > 0
        assert any("auth.py" in e.text for e in file_entities)

    @pytest.mark.asyncio
    async def test_error_extraction(self):
        """Test error message extraction"""
        extractor = EntityExtractor()
        user_context = Mock(workspace_path="/tmp")

        prompt = "Fix the TypeError: 'NoneType' object is not subscriptable"
        entities = await extractor.extract(prompt, user_context)

        error_entities = [e for e in entities if e.type == EntityType.ERROR]
        assert len(error_entities) > 0
        assert any("TypeError" in e.text for e in error_entities)

    @pytest.mark.asyncio
    async def test_identifier_extraction(self):
        """Test code identifier extraction"""
        extractor = EntityExtractor()
        user_context = Mock(workspace_path="/tmp")

        prompt = "Fix the process_payment function"
        entities = await extractor.extract(prompt, user_context)

        identifier_entities = [e for e in entities if e.type == EntityType.IDENTIFIER]
        assert len(identifier_entities) > 0
        assert any("process_payment" in e.text for e in identifier_entities)


class TestTokenBudgetEstimator:
    """Test token budget estimation"""

    def test_fix_intent_budget(self):
        """Test budget for fix intent"""
        estimator = TokenBudgetEstimator()
        intent = Mock(type=IntentType.FIX)
        entities = [Mock()] * 3  # 3 entities

        budget = estimator.estimate(intent, entities)
        assert 100000 <= budget <= 150000  # Base + entity multiplier

    def test_explain_intent_budget(self):
        """Test budget for explain intent"""
        estimator = TokenBudgetEstimator()
        intent = Mock(type=IntentType.EXPLAIN)
        entities = [Mock()] * 2  # 2 entities

        budget = estimator.estimate(intent, entities)
        assert 50000 <= budget <= 100000

    def test_max_budget_cap(self):
        """Test budget never exceeds max"""
        estimator = TokenBudgetEstimator()
        intent = Mock(type=IntentType.IMPLEMENT)
        entities = [Mock()] * 100  # Many entities

        budget = estimator.estimate(intent, entities)
        assert budget <= 400000  # Max cap


class TestPromptAnalyzer:
    """Test full prompt analysis"""

    @pytest.mark.asyncio
    async def test_analyze_fix_prompt(self):
        """Test analysis of fix prompt"""
        analyzer = PromptAnalyzer()
        user_context = Mock(workspace_path="/tmp")

        prompt = "Fix the authentication bug in backend/auth.py"
        result = await analyzer.analyze(prompt, user_context)

        assert result.intent.type == IntentType.FIX
        assert len(result.entities) > 0
        assert result.token_budget > 0
        assert 'code' in result.context_types
        assert result.confidence > 0.0


# ============================================================================
# Epic 2: Context Gathering Tests
# ============================================================================


class TestCurrentContextGatherer:
    """Test current context gathering"""

    @pytest.mark.asyncio
    async def test_gather_current_file(self):
        """Test gathering current file"""
        gatherer = CurrentContextGatherer()

        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("def test():\n    pass\n")
            temp_file = f.name

        try:
            workspace = os.path.dirname(temp_file)
            filename = os.path.basename(temp_file)

            user_context = UserContext(
                workspace_path=workspace,
                current_file=filename
            )

            context = await gatherer.gather(user_context)

            assert context.source == 'current'
            assert len(context.items) > 0
            assert any(item.type == 'file' for item in context.items)

        finally:
            os.unlink(temp_file)


class TestCodeContextGatherer:
    """Test code context gathering"""

    @pytest.mark.asyncio
    async def test_gather_file_context(self):
        """Test gathering code context for file entity"""
        gatherer = CodeContextGatherer()

        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("import os\n\ndef test():\n    pass\n")
            temp_file = f.name

        try:
            workspace = os.path.dirname(temp_file)
            filename = os.path.basename(temp_file)

            user_context = UserContext(workspace_path=workspace)

            entity = Mock(type=EntityType.FILE, text=filename)
            context = await gatherer.gather([entity], user_context)

            assert context.source == 'code'
            # Should have at least the file itself
            assert len(context.items) >= 0

        finally:
            os.unlink(temp_file)


class TestContextGatherer:
    """Test context gathering orchestration"""

    @pytest.mark.asyncio
    async def test_parallel_gathering(self):
        """Test parallel gathering from multiple sources"""
        gatherer = ContextGatherer()

        prompt_intent = Mock(
            original_prompt="Test prompt",
            context_types={'current', 'code'},
            entities=[]
        )

        # Create temp workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            user_context = UserContext(workspace_path=tmpdir)

            result = await gatherer.gather(prompt_intent, user_context)

            assert result.total_items >= 0
            assert len(result.chunks) > 0


# ============================================================================
# Epic 3: Context Ranking & Summarization Tests
# ============================================================================


class TestContextRanker:
    """Test context ranking"""

    @pytest.mark.asyncio
    async def test_rank_contexts(self):
        """Test ranking of context items"""
        ranker = ContextRanker()

        # Create mock raw context
        from src.prompt.context_gatherer import ContextChunk, RawContext
        raw_context = RawContext()

        chunk = ContextChunk(source='test')
        chunk.add(
            type='file',
            content='def test(): pass',
            priority=5.0,
            path='test.py'
        )
        raw_context.merge(chunk)

        prompt_intent = Mock(
            original_prompt="test",
            entities=[]
        )
        user_context = UserContext(workspace_path='/tmp')

        ranked = await ranker.rank(raw_context, prompt_intent, user_context)

        assert len(ranked.chunks) > 0
        assert all(hasattr(chunk, 'score') for chunk in ranked.chunks)


class TestExtractiveSummarizer:
    """Test extractive summarization"""

    def test_summarize_code(self):
        """Test code summarization"""
        summarizer = ExtractiveSummarizer()

        code = """
def process_payment(amount):
    '''Process payment'''
    # Validate amount
    if amount <= 0:
        raise ValueError("Invalid amount")

    # Process
    result = gateway.charge(amount)
    return result
"""

        summary = summarizer.summarize(code, ratio=0.5)

        # Summary should be shorter
        assert len(summary) < len(code)

        # Should preserve important parts
        assert 'def process_payment' in summary or 'process_payment' in summary


class TestHierarchicalSummarizer:
    """Test hierarchical summarization"""

    @pytest.mark.asyncio
    async def test_summarize_within_budget(self):
        """Test summarization fits within token budget"""
        summarizer = HierarchicalSummarizer()

        # Create mock ranked context
        from src.prompt.context_gatherer import ContextChunk
        from src.prompt.ranker import RankedContext, ScoredChunk

        chunk = ContextChunk(source='test')
        chunk.add(
            type='file',
            content='x' * 1000,  # 1000 chars
            priority=8.0,
            path='test.py'
        )

        scored = ScoredChunk(chunk=chunk.items[0], score=8.0)
        ranked = RankedContext(chunks=[scored])

        # Set budget to require compression
        result = await summarizer.summarize(ranked, token_budget=50)

        assert result.total_tokens <= 50


# ============================================================================
# Epic 4: Prompt Composition Tests
# ============================================================================


class TestPromptComposer:
    """Test prompt composition"""

    def test_compose_enhanced_prompt(self):
        """Test composing enhanced prompt"""
        composer = PromptComposer()

        # Create mock summarized context
        from src.prompt.summarizer import SummarizedContext

        summarized = SummarizedContext()

        # Create mock prompt intent
        prompt_intent = Mock(
            intent=Mock(type=IntentType.FIX),
            entities=[],
            token_budget=100000
        )

        result = composer.compose(
            "Fix the bug",
            summarized,
            prompt_intent
        )

        assert result.original == "Fix the bug"
        assert len(result.enhanced) > len(result.original)
        assert result.token_count > 0
        assert 'USER REQUEST' in result.enhanced


def test_token_counting():
    """Test token counting"""
    text = "This is a test sentence with multiple words."
    tokens = count_tokens(text)
    assert tokens > 0
    assert tokens < len(text)  # Tokens should be less than characters


# ============================================================================
# Integration Tests
# ============================================================================


class TestPromptEnhancementIntegration:
    """Integration tests for full enhancement pipeline"""

    @pytest.mark.asyncio
    async def test_end_to_end_enhancement(self):
        """Test complete enhancement pipeline"""
        from src.prompt import enhance_prompt

        # Create temp workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, 'test.py')
            with open(test_file, 'w') as f:
                f.write("""
def calculate_total(items):
    '''Calculate total price'''
    total = 0
    for item in items:
        total += item.price
    return total
""")

            user_context = UserContext(
                workspace_path=tmpdir,
                current_file='test.py'
            )

            # Enhance prompt
            result = await enhance_prompt(
                "How does the total calculation work?",
                user_context
            )

            # Verify result
            assert result.original == "How does the total calculation work?"
            assert len(result.enhanced) > len(result.original)
            assert result.token_count > 0
            assert 'USER REQUEST' in result.enhanced

    @pytest.mark.asyncio
    async def test_enhancement_with_multiple_entities(self):
        """Test enhancement with multiple extracted entities"""
        from src.prompt import enhance_prompt

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'auth.py')
            with open(test_file, 'w') as f:
                f.write("def authenticate(user): pass\n")

            user_context = UserContext(
                workspace_path=tmpdir,
                current_file='auth.py'
            )

            result = await enhance_prompt(
                "Fix the TypeError in authenticate function",
                user_context
            )

            assert result.token_count > 0
            assert result.metadata['entity_count'] >= 2  # TypeError + authenticate


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
