"""
Intelligent Search Engine

Natural language search with context-aware ranking.

Components:
- QueryParser: NLP-based query parsing using spaCy
- QueryExpander: Query expansion with synonyms and related terms
- ContextCollector: User context tracking
- ContextRanker: Multi-factor ranking with context boosts
- SearchTemplateManager: Pre-built search templates

Example Usage:
    >>> from search.intelligent import IntelligentSearchEngine
    >>> engine = IntelligentSearchEngine()
    >>> results = engine.search("find user authentication", user_id="user123")
    >>> for result in results:
    ...     print(f"{result.file_path}: {result.final_score:.3f}")
"""

from .models import (
    Intent,
    EntityType,
    Entity,
    ParsedQuery,
    ExpandedTerm,
    SearchContext,
    BoostFactors,
    EnhancedSearchResult,
    SearchTemplate,
    QueryExpansion,
)

from .query_parser import QueryParser
from .query_expander import QueryExpander
from .context_collector import ContextCollector
from .context_ranker import ContextRanker
from .templates import SearchTemplateManager

__all__ = [
    # Models
    "Intent",
    "EntityType",
    "Entity",
    "ParsedQuery",
    "ExpandedTerm",
    "SearchContext",
    "BoostFactors",
    "EnhancedSearchResult",
    "SearchTemplate",
    "QueryExpansion",
    # Components
    "QueryParser",
    "QueryExpander",
    "ContextCollector",
    "ContextRanker",
    "SearchTemplateManager",
    # Main engine
    "IntelligentSearchEngine",
]


class IntelligentSearchEngine:
    """
    Main intelligent search engine orchestrator.

    Combines all components for end-to-end intelligent search:
    1. Query parsing and expansion
    2. Context collection
    3. Search execution (delegated to backend)
    4. Context-aware ranking
    """

    def __init__(
        self,
        use_spacy: bool = True,
        use_word2vec: bool = False,
        use_codebert: bool = False,
        enable_explanations: bool = True,
    ):
        """
        Initialize intelligent search engine.

        Args:
            use_spacy: Whether to use spaCy for NLP (requires installation)
            use_word2vec: Whether to use Word2Vec for expansion (requires gensim)
            use_codebert: Whether to use CodeBERT for expansion (requires transformers)
            enable_explanations: Whether to generate ranking explanations
        """
        self.parser = QueryParser(use_spacy=use_spacy)
        self.expander = QueryExpander(
            use_word2vec=use_word2vec,
            use_codebert=use_codebert
        )
        self.context_collector = ContextCollector()
        self.ranker = ContextRanker(enable_explanations=enable_explanations)
        self.template_manager = SearchTemplateManager()

    def search(
        self,
        query: str,
        user_id: str,
        search_backend,
        project_relationships=None,
        max_results: int = 50,
    ) -> list:
        """
        Perform intelligent search.

        Args:
            query: Natural language search query
            user_id: User identifier
            search_backend: Search backend (semantic, keyword, etc.)
            project_relationships: Optional project dependency graph
            max_results: Maximum number of results

        Returns:
            List of EnhancedSearchResult
        """
        # Step 1: Parse query
        parsed_query = self.parser.parse(query)

        # Step 2: Expand query
        expansion = self.expander.expand(query)

        # Step 3: Collect user context
        context = self.context_collector.collect(user_id)

        # Step 4: Build enhanced query
        all_terms = [query] + expansion.get_all_terms()
        enhanced_query = " ".join(all_terms[:10])  # Limit terms

        # Step 5: Execute search (delegated to backend)
        # This would call the actual search backend (Qdrant, etc.)
        raw_results = search_backend.search(enhanced_query, limit=max_results)

        # Step 6: Apply context-aware ranking
        ranked_results = self.ranker.rank(
            raw_results,
            context=context,
            query=parsed_query,
            project_relationships=project_relationships
        )

        # Step 7: Track this query
        self.context_collector.track_query(user_id, query)

        return ranked_results

    def search_with_template(
        self,
        template_name: str,
        user_id: str,
        search_backend,
        project_relationships=None,
        **template_params
    ) -> list:
        """
        Search using a pre-built template.

        Args:
            template_name: Name of template to use
            user_id: User identifier
            search_backend: Search backend
            project_relationships: Optional project dependency graph
            **template_params: Parameters for template

        Returns:
            List of EnhancedSearchResult
        """
        # Apply template
        query = self.template_manager.apply_template(template_name, **template_params)
        if not query:
            raise ValueError(f"Template not found: {template_name}")

        # Use regular search
        return self.search(
            query=query,
            user_id=user_id,
            search_backend=search_backend,
            project_relationships=project_relationships
        )

    def parse_query(self, query: str) -> ParsedQuery:
        """Parse a query without executing search"""
        return self.parser.parse(query)

    def expand_query(self, query: str) -> QueryExpansion:
        """Expand a query without executing search"""
        return self.expander.expand(query)

    def suggest_templates(self, query: str, limit: int = 3) -> list:
        """Suggest templates for a query"""
        return self.template_manager.suggest_templates(query, limit=limit)

    def track_file_access(self, user_id: str, file_path: str):
        """Track file access for context"""
        self.context_collector.track_file_access(user_id, file_path)

    def set_current_file(self, user_id: str, file_path: str):
        """Set current file for user"""
        self.context_collector.set_current_file(user_id, file_path)

    def get_context(self, user_id: str) -> SearchContext:
        """Get current context for user"""
        return self.context_collector.collect(user_id)
