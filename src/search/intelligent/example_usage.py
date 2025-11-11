"""
Example Usage of Intelligent Search Engine

Demonstrates how to use the intelligent search components.
"""

from src.search.intelligent import (
    IntelligentSearchEngine,
    QueryParser,
    QueryExpander,
    ContextCollector,
    ContextRanker,
    SearchTemplateManager,
    SearchContext,
)


def example_query_parsing():
    """Example: Parse natural language queries"""
    print("=" * 60)
    print("Example 1: Query Parsing")
    print("=" * 60)

    parser = QueryParser(use_spacy=False)  # Fallback parser

    queries = [
        "find user authentication logic",
        "show all API endpoints in backend",
        "where is the database configuration",
        "list React components",
    ]

    for query in queries:
        parsed = parser.parse(query)
        print(f"\nQuery: {query}")
        print(f"  Intent: {parsed.intent.value}")
        print(f"  Keywords: {', '.join(parsed.keywords)}")
        print(f"  Entities: {[e.text for e in parsed.entities]}")
        print(f"  Expanded: {', '.join(parsed.expanded_terms[:5])}")
        print(f"  Confidence: {parsed.confidence:.2f}")


def example_query_expansion():
    """Example: Expand queries with synonyms"""
    print("\n" + "=" * 60)
    print("Example 2: Query Expansion")
    print("=" * 60)

    expander = QueryExpander()

    queries = [
        "auth",
        "API endpoint",
        "error handling",
        "database query",
    ]

    for query in queries:
        expansion = expander.expand(query)
        print(f"\nQuery: {query}")
        print(f"  Expanded terms:")
        for term in expansion.expanded_terms[:5]:
            print(f"    - {term.expanded} (score: {term.relevance_score:.2f}, type: {term.expansion_type})")

        if expansion.synonyms:
            print(f"  Synonyms:")
            for original, syns in list(expansion.synonyms.items())[:2]:
                print(f"    - {original}: {', '.join(syns[:3])}")


def example_context_collection():
    """Example: Track user context"""
    print("\n" + "=" * 60)
    print("Example 3: Context Collection")
    print("=" * 60)

    collector = ContextCollector()

    # Simulate user activity
    user_id = "developer1"

    # Track file accesses
    files = [
        "backend/auth/jwt.py",
        "backend/auth/oauth.py",
        "frontend/hooks/useAuth.ts",
        "backend/models/user.py",
        "backend/auth/jwt.py",  # Access again
        "frontend/components/Login.tsx",
    ]

    for file_path in files:
        collector.track_file_access(user_id, file_path)

    # Set current file
    collector.set_current_file(user_id, "frontend/components/Dashboard.tsx")

    # Track queries
    queries = [
        "authentication logic",
        "user model",
        "login component",
    ]
    for query in queries:
        collector.track_query(user_id, query)

    # Collect context
    context = collector.collect(user_id)

    print(f"\nUser: {user_id}")
    print(f"  Current file: {context.current_file}")
    print(f"  Current project: {context.current_project}")
    print(f"  Recent files: {len(context.recent_files)}")
    for file in context.recent_files[:3]:
        print(f"    - {file}")
    print(f"  Frequent files: {len(context.frequent_files)}")
    for file in context.frequent_files[:3]:
        print(f"    - {file}")
    print(f"  Recent queries: {context.recent_queries}")


def example_context_ranking():
    """Example: Rank results with context"""
    print("\n" + "=" * 60)
    print("Example 4: Context-Aware Ranking")
    print("=" * 60)

    ranker = ContextRanker()

    # Mock search results
    results = [
        {
            "file_path": "backend/auth/jwt.py",
            "file_name": "jwt.py",
            "file_type": "python",
            "similarity_score": 0.95,
        },
        {
            "file_path": "frontend/hooks/useAuth.ts",
            "file_name": "useAuth.ts",
            "file_type": "typescript",
            "similarity_score": 0.88,
        },
        {
            "file_path": "shared/types/auth.ts",
            "file_name": "auth.ts",
            "file_type": "typescript",
            "similarity_score": 0.82,
        },
    ]

    # User context (currently in frontend)
    context = SearchContext(
        user_id="developer1",
        current_file="frontend/App.tsx",
        current_project="frontend",
        recent_files=["frontend/hooks/useAuth.ts", "frontend/components/Login.tsx"],
        frequent_files=["frontend/App.tsx", "frontend/hooks/useAuth.ts"],
    )

    # Rank results
    ranked = ranker.rank(results, context)

    print("\nQuery: 'authentication logic'")
    print("Current file: frontend/App.tsx (frontend project)")
    print("\nRanked Results:")
    for i, result in enumerate(ranked, 1):
        print(f"\n{i}. {result.file_path}")
        print(f"   Base score: {result.base_score:.3f}")
        print(f"   Final score: {result.final_score:.3f}")
        print(f"   Context relevance: {result.context_relevance:.3f}")
        print(f"   Boosts applied:")
        boost_dict = result.boost_breakdown.to_dict()
        for factor, value in boost_dict.items():
            if factor != "total" and value > 0:
                print(f"     - {factor}: +{value:.3f}")


def example_search_templates():
    """Example: Use search templates"""
    print("\n" + "=" * 60)
    print("Example 5: Search Templates")
    print("=" * 60)

    manager = SearchTemplateManager()

    # List available templates
    print("\nAvailable Templates:")
    for template in manager.list_templates()[:8]:
        print(f"  - {template.name}: {template.description}")

    # Apply a template
    print("\n\nApplying templates:")

    templates = [
        ("api_endpoints", {}),
        ("authentication", {}),
        ("components", {"component_name": "Button"}),
        ("types", {"type_name": "User"}),
    ]

    for template_name, params in templates:
        query = manager.apply_template(template_name, **params)
        print(f"\n  Template: {template_name}")
        print(f"  Query: {query}")

    # Suggest templates for a query
    print("\n\nTemplate Suggestions:")
    query = "find login logic"
    suggestions = manager.suggest_templates(query, limit=3)
    print(f"Query: '{query}'")
    print("Suggested templates:")
    for template in suggestions:
        print(f"  - {template.name}: {template.description}")


def example_end_to_end():
    """Example: End-to-end intelligent search"""
    print("\n" + "=" * 60)
    print("Example 6: End-to-End Intelligent Search")
    print("=" * 60)

    # Mock search backend
    class MockSearchBackend:
        def search(self, query, limit=50):
            # Return mock results
            return [
                {
                    "file_path": "backend/auth/jwt.py",
                    "file_name": "jwt.py",
                    "file_type": "python",
                    "similarity_score": 0.95,
                },
                {
                    "file_path": "frontend/hooks/useAuth.ts",
                    "file_name": "useAuth.ts",
                    "file_type": "typescript",
                    "similarity_score": 0.88,
                },
                {
                    "file_path": "backend/auth/oauth.py",
                    "file_name": "oauth.py",
                    "file_type": "python",
                    "similarity_score": 0.85,
                },
            ]

    # Initialize engine
    engine = IntelligentSearchEngine(use_spacy=False)

    # Setup user context
    user_id = "developer1"
    engine.set_current_file(user_id, "frontend/App.tsx")
    engine.track_file_access(user_id, "frontend/hooks/useAuth.ts")
    engine.track_file_access(user_id, "frontend/components/Login.tsx")

    # Perform search
    backend = MockSearchBackend()
    query = "authentication logic"

    print(f"\nSearching for: '{query}'")
    print(f"User: {user_id}")
    print(f"Current file: frontend/App.tsx")

    results = engine.search(
        query=query,
        user_id=user_id,
        search_backend=backend
    )

    print("\nResults:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.file_path}")
        print(f"   Score: {result.final_score:.3f} (base: {result.base_score:.3f})")
        print(f"   Ranking explanation:")
        print(f"   {result.explain_ranking()}")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("INTELLIGENT SEARCH ENGINE - EXAMPLES")
    print("=" * 60)

    example_query_parsing()
    example_query_expansion()
    example_context_collection()
    example_context_ranking()
    example_search_templates()
    example_end_to_end()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
