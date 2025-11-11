"""Examples demonstrating Memory System usage.

This file shows how to use all four memory types:
- Conversation Memory
- Pattern Memory
- Solution Memory
- Preference Memory
"""

from src.memory import ConversationStore, PatternStore, SolutionStore, PreferenceStore
from src.memory.database import init_database


def example_conversation_memory():
    """Example: Using Conversation Memory."""
    print("\n" + "="*60)
    print("EXAMPLE: Conversation Memory")
    print("="*60 + "\n")

    store = ConversationStore()

    # Store a conversation
    conversation_id = store.store_conversation(
        user_id="alice@example.com",
        prompt="How do I fix the authentication bug?",
        enhanced_prompt="""
        # USER REQUEST
        How do I fix the authentication bug?

        # CURRENT CONTEXT
        Current file: backend/auth.py
        Error: 401 Unauthorized

        # RELATED CODE
        ## backend/auth.py
        def authenticate(token):
            # JWT validation logic
            ...
        """,
        response="The authentication bug is caused by expired tokens...",
        intent="fix",
        entities={"files": ["backend/auth.py"], "errors": ["401 Unauthorized"]},
        token_count=5000,
        latency_ms=1200,
    )

    print(f"✓ Stored conversation: {conversation_id}")

    # Search for similar conversations
    print("\nSearching for similar conversations...")
    results = store.get_similar_conversations(
        query="authentication problems",
        user_id="alice@example.com",
        limit=3,
    )

    for result in results:
        conv = result['conversation']
        print(f"  - [{result['similarity_score']:.3f}] {conv.prompt[:60]}...")

    # Update with feedback
    store.update_feedback(
        conversation_id=conversation_id,
        feedback={"helpful": True, "comment": "Solved my problem!"},
        resolution=True,
        helpful_score=0.95,
    )

    print("✓ Updated conversation feedback")

    # Get statistics
    stats = store.get_statistics(user_id="alice@example.com")
    print(f"\nStatistics:")
    print(f"  - Total conversations: {stats['total_conversations']}")
    print(f"  - Resolution rate: {stats['resolution_rate']:.1%}")


def example_pattern_memory():
    """Example: Using Pattern Memory."""
    print("\n" + "="*60)
    print("EXAMPLE: Pattern Memory")
    print("="*60 + "\n")

    store = PatternStore()

    # Store a code pattern
    pattern_id = store.store_pattern(
        pattern_type="error_handling",
        name="retry_with_backoff",
        example_code="""
async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
        """,
        description="Retry function with exponential backoff",
        language="python",
        project_id="my_project",
    )

    print(f"✓ Stored pattern: {pattern_id}")

    # Extract patterns from code
    sample_code = '''
def test_example():
    """Test example"""
    assert True

async def fetch_data():
    """Async function"""
    return await client.get("/data")
'''

    pattern_ids = store.extract_patterns_from_file(
        file_path="example.py",
        content=sample_code,
        project_id="my_project",
    )

    print(f"✓ Extracted {len(pattern_ids)} patterns from code")

    # Get patterns by type
    patterns = store.get_patterns(
        pattern_type="error_handling",
        project_id="my_project",
        limit=5,
    )

    print(f"\nError handling patterns:")
    for pattern in patterns:
        print(f"  - {pattern.name} (used {pattern.usage_count} times)")

    # Get statistics
    stats = store.get_pattern_statistics(project_id="my_project")
    print(f"\nPattern Statistics:")
    print(f"  - Total patterns: {stats['total_patterns']}")
    print(f"  - Pattern types: {list(stats['pattern_types'].keys())}")


def example_solution_memory():
    """Example: Using Solution Memory."""
    print("\n" + "="*60)
    print("EXAMPLE: Solution Memory")
    print("="*60 + "\n")

    store = SolutionStore()

    # Store a problem-solution pair
    solution_id = store.store_solution(
        problem_description="Database connection pool exhausted under high load",
        solution_code="""
# Increase pool size and add connection timeout
DATABASE_CONFIG = {
    'pool_size': 20,          # Increased from 5
    'max_overflow': 10,       # Added overflow
    'pool_timeout': 30,       # Added timeout
    'pool_pre_ping': True,    # Verify connections
}
        """,
        solution_description="Increased connection pool size and added timeout configuration",
        problem_type="performance",
        error_message="PoolExhausted: QueuePool limit exceeded",
        files_affected=["config/database.py"],
        success_rate=0.95,
        resolution_time_sec=3600,
        user_id="bob@example.com",
        project_id="my_project",
    )

    print(f"✓ Stored solution: {solution_id}")

    # Search for similar solutions
    print("\nSearching for similar solutions...")
    results = store.get_similar_solutions(
        problem="connection pool issues",
        project_id="my_project",
        limit=3,
    )

    for result in results:
        sol = result['solution']
        print(f"  - [{result['similarity_score']:.3f}] {sol.problem_type}")
        print(f"    Success rate: {sol.success_rate:.1%}")

    # Update solution metrics after usage
    store.update_solution_metrics(
        solution_id=solution_id,
        success=True,
        resolution_time_sec=1800,
    )

    print("✓ Updated solution metrics")

    # Recluster solutions
    print("\nReclustering solutions...")
    cluster_stats = store.recluster_solutions(project_id="my_project")
    print(f"  - Clusters: {cluster_stats['clusters']}")
    print(f"  - Solutions: {cluster_stats['solutions']}")

    # Get statistics
    stats = store.get_solution_statistics(project_id="my_project")
    print(f"\nSolution Statistics:")
    print(f"  - Total solutions: {stats['total_solutions']}")
    print(f"  - Average success rate: {stats['avg_success_rate']:.1%}")


def example_preference_memory():
    """Example: Using Preference Memory."""
    print("\n" + "="*60)
    print("EXAMPLE: Preference Memory")
    print("="*60 + "\n")

    store = PreferenceStore()

    # Update preferences manually (active learning)
    store.update_preference(
        user_id="charlie@example.com",
        preference_key="code_style.indentation",
        preference_value="4_spaces",
    )

    store.update_preference(
        user_id="charlie@example.com",
        preference_key="code_style.quote_style",
        preference_value="double",
    )

    store.update_preference(
        user_id="charlie@example.com",
        preference_key="preferred_libraries.testing",
        preference_value="pytest",
    )

    print("✓ Updated user preferences")

    # Get user preferences
    prefs = store.get_user_preferences("charlie@example.com")
    if prefs:
        print(f"\nPreferences for charlie@example.com:")
        print(f"  - Indentation: {prefs.code_style.get('indentation', 'unknown')}")
        print(f"  - Quote style: {prefs.code_style.get('quote_style', 'unknown')}")
        if prefs.preferred_libraries:
            print(f"  - Testing library: {prefs.preferred_libraries.get('testing', 'unknown')}")

    # Note: Learning from git history requires a real git repository
    # Example:
    # result = store.learn_from_git_history(
    #     user_id="charlie@example.com",
    #     repo_path="/path/to/repo",
    #     max_commits=100,
    # )
    # print(f"Learned from {result['commits_analyzed']} commits")


def example_integrated_workflow():
    """Example: Integrated workflow using all memory types."""
    print("\n" + "="*60)
    print("EXAMPLE: Integrated Workflow")
    print("="*60 + "\n")

    conversation_store = ConversationStore()
    pattern_store = PatternStore()
    solution_store = SolutionStore()
    preference_store = PreferenceStore()

    user_id = "developer@example.com"
    project_id = "my_project"

    # 1. User asks a question
    print("1. User asks: 'How to handle API rate limiting?'")

    # 2. Store conversation
    conv_id = conversation_store.store_conversation(
        user_id=user_id,
        prompt="How to handle API rate limiting?",
        intent="implement",
        entities={"concepts": ["rate limiting", "API"]},
    )

    # 3. Search for similar past solutions
    print("\n2. Searching for similar solutions...")
    similar_solutions = solution_store.get_similar_solutions(
        problem="API rate limiting",
        project_id=project_id,
        limit=3,
    )

    if similar_solutions:
        print(f"   Found {len(similar_solutions)} similar solutions")

    # 4. Search for relevant patterns
    print("\n3. Searching for relevant patterns...")
    patterns = pattern_store.get_patterns(
        pattern_type="api_design",
        project_id=project_id,
    )

    if patterns:
        print(f"   Found {len(patterns)} API design patterns")

    # 5. Get user preferences for code generation
    print("\n4. Getting user preferences...")
    prefs = preference_store.get_user_preferences(user_id)

    if prefs:
        print(f"   User prefers: {prefs.code_style}")

    # 6. Generate solution (simulated)
    print("\n5. Generated solution with user's preferred style")

    # 7. Store the new solution
    solution_id = solution_store.store_solution(
        problem_description="Implement API rate limiting",
        solution_code="# Rate limiting implementation...",
        problem_type="feature",
        success_rate=0.0,  # Will be updated as it's used
        project_id=project_id,
    )

    # 8. Extract patterns from the solution
    pattern_id = pattern_store.store_pattern(
        pattern_type="api_design",
        name="rate_limiter",
        example_code="# Rate limiting pattern...",
        project_id=project_id,
    )

    # 9. Update conversation with success
    conversation_store.update_feedback(
        conversation_id=conv_id,
        feedback={
            "solution_id": str(solution_id),
            "pattern_id": str(pattern_id),
        },
        resolution=True,
        helpful_score=0.9,
    )

    print("\n6. Workflow complete!")
    print(f"   - Conversation: {conv_id}")
    print(f"   - Solution: {solution_id}")
    print(f"   - Pattern: {pattern_id}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Memory System Examples")
    print("Context Workspace v3.0")
    print("="*60)

    # Initialize database
    print("\nInitializing database...")
    init_database()
    print("✓ Database initialized")

    # Run examples
    try:
        example_conversation_memory()
        example_pattern_memory()
        example_solution_memory()
        example_preference_memory()
        example_integrated_workflow()

        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
