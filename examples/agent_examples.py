"""
Examples for using Autonomous Code Generation Agents

This file demonstrates various use cases for the agent system.
"""

import asyncio
import os
from pathlib import Path

from src.agents import (
    AgentContext,
    AgentOrchestrator,
    PlanningAgent,
    CodingAgent,
    TestingAgent,
    ReviewAgent,
    PRAgent,
)


async def example_1_simple_agent_workflow():
    """
    Example 1: Simple agent workflow in autonomous mode

    This example shows the basic usage of the agent orchestrator
    to autonomously plan, code, test, review, and create a PR.
    """
    print("=" * 80)
    print("Example 1: Simple Agent Workflow (Autonomous Mode)")
    print("=" * 80)

    # Create agent context
    context = AgentContext(
        workspace_path=os.getcwd(),
        project_name="example_project",
        language="python",
        framework="fastapi",
        test_framework="pytest",
    )

    # Create orchestrator in autonomous mode
    orchestrator = AgentOrchestrator(context, mode="autonomous")

    # Run agent workflow
    result = await orchestrator.run("Add email validation to the user registration endpoint")

    # Display results
    print(f"\n{'='*80}")
    print("Results:")
    print(f"{'='*80}")
    print(result.summary)

    if result.success:
        print("\n✅ Agent workflow completed successfully!")
        if result.pull_request:
            print(f"PR: {result.pull_request.title}")
            print(f"Branch: {result.pull_request.branch_name}")
            if result.pull_request.pr_url:
                print(f"URL: {result.pull_request.pr_url}")
    else:
        print(f"\n❌ Agent workflow failed: {result.error}")


async def example_2_supervised_mode():
    """
    Example 2: Supervised mode with user approval

    This example shows how to use supervised mode where the user
    must approve each stage of the workflow.
    """
    print("=" * 80)
    print("Example 2: Supervised Mode with Approval")
    print("=" * 80)

    # Define approval callback
    async def approval_callback(stage: str, data) -> bool:
        print(f"\n{'='*80}")
        print(f"Approval Required: {stage}")
        print(f"{'='*80}")

        if stage == "Planning":
            print(f"Tasks to execute: {len(data.tasks)}")
            for i, task in enumerate(data.tasks, 1):
                print(f"  {i}. {task.description} ({task.estimated_effort}h)")

        elif stage == "Coding":
            total_files = sum(len(cc.changes) for cc in data)
            print(f"Files to be changed: {total_files}")

        elif stage == "Testing":
            total_tests = sum(tr.total_tests for tr in data)
            passed = sum(tr.passed for tr in data)
            print(f"Test results: {passed}/{total_tests} passed")

        elif stage == "Review":
            print(f"Review status: {'✅ Approved' if data.approved else '⚠️ Needs attention'}")
            print(f"Issues found: {len(data.issues)}")

        elif stage == "PR Creation":
            print(f"PR title: {data.title}")
            print(f"Branch: {data.branch_name}")

        # Auto-approve for example (in real use, ask user)
        print("\n⚠️  Auto-approving for example purposes")
        return True

    # Create context
    context = AgentContext(
        workspace_path=os.getcwd(),
        project_name="example_project",
        language="python",
        test_framework="pytest",
    )

    # Create orchestrator in supervised mode
    orchestrator = AgentOrchestrator(
        context,
        mode="supervised",
        approval_callback=approval_callback
    )

    # Run workflow
    result = await orchestrator.run("Add logging to authentication module")

    print(f"\n{'='*80}")
    print("Final Results:")
    print(f"{'='*80}")
    print(result.summary)


async def example_3_individual_agents():
    """
    Example 3: Using individual agents separately

    This example shows how to use each agent individually
    for more fine-grained control.
    """
    print("=" * 80)
    print("Example 3: Using Individual Agents")
    print("=" * 80)

    # Create context
    context = AgentContext(
        workspace_path=os.getcwd(),
        project_name="example_project",
        language="python",
    )

    # 1. Planning Agent
    print("\n--- Step 1: Planning ---")
    planning_agent = PlanningAgent(context)
    plan = await planning_agent.plan(
        "Add rate limiting to API endpoints",
        context
    )
    print(f"Created plan with {len(plan.tasks)} tasks:")
    for i, task in enumerate(plan.tasks, 1):
        print(f"  {i}. {task.description}")

    # 2. Coding Agent
    print("\n--- Step 2: Coding ---")
    coding_agent = CodingAgent(context)
    task = plan.tasks[0]  # Get first task
    code_changes = await coding_agent.code(task, context)
    print(f"Generated {len(code_changes.changes)} file changes")
    for change in code_changes.changes:
        print(f"  - {change.path} ({change.operation})")

    # 3. Testing Agent
    print("\n--- Step 3: Testing ---")
    testing_agent = TestingAgent(context)
    test_results = await testing_agent.test(code_changes)
    print(f"Tests: {test_results.passed}/{test_results.total_tests} passed")
    print(f"Coverage: {test_results.coverage:.1f}%")

    # 4. Review Agent
    print("\n--- Step 4: Review ---")
    review_agent = ReviewAgent(context)
    review = await review_agent.review(code_changes, test_results)
    print(f"Review: {'✅ Approved' if review.approved else '⚠️ Needs attention'}")
    print(f"Issues: {len(review.issues)}")
    print(f"Security score: {review.security_score:.1f}/100")

    # 5. PR Agent
    print("\n--- Step 5: PR Creation ---")
    pr_agent = PRAgent(context)
    pull_request = await pr_agent.create_pr(
        code_changes,
        review,
        "Add rate limiting to API endpoints"
    )
    print(f"PR created: {pull_request.title}")
    print(f"Branch: {pull_request.branch_name}")


async def example_4_custom_context():
    """
    Example 4: Using custom context with patterns and preferences

    This example shows how to provide custom coding patterns
    and user preferences to guide code generation.
    """
    print("=" * 80)
    print("Example 4: Custom Context with Patterns")
    print("=" * 80)

    # Create context with custom patterns and preferences
    context = AgentContext(
        workspace_path=os.getcwd(),
        project_name="example_project",
        language="python",
        framework="fastapi",
        test_framework="pytest",
        coding_patterns={
            "error_handling": """
# Always use specific exceptions
try:
    # operation
except SpecificError as e:
    logger.error(f"Error: {e}")
    raise
""",
            "api_endpoint": """
@router.post("/endpoint")
async def endpoint(data: Schema):
    '''Endpoint description'''
    # Validate
    # Process
    # Return
    return Response(data)
""",
            "logging": """
import logging
logger = logging.getLogger(__name__)
logger.info("Message")
""",
        },
        user_preferences={
            "style": "PEP 8",
            "docstrings": "Google style",
            "type_hints": "Always use type hints",
            "naming": "snake_case for functions/variables",
            "imports": "Group: stdlib, third-party, local",
        },
    )

    # Run agent with custom context
    orchestrator = AgentOrchestrator(context, mode="autonomous")
    result = await orchestrator.run("Add endpoint to get user profile")

    print("\nAgent used custom patterns and preferences for code generation")
    print(result.summary)


async def example_5_error_handling():
    """
    Example 5: Error handling and retry logic

    This example demonstrates how the agents handle errors
    and retry failed operations.
    """
    print("=" * 80)
    print("Example 5: Error Handling and Retry")
    print("=" * 80)

    context = AgentContext(
        workspace_path="/nonexistent/path",  # Invalid path
        project_name="example_project",
        language="python",
    )

    orchestrator = AgentOrchestrator(context, mode="autonomous")

    try:
        result = await orchestrator.run("Add feature")

        if result.error:
            print(f"✅ Error was caught and handled: {result.error}")
        else:
            print("Workflow completed (unexpected)")

    except Exception as e:
        print(f"✅ Exception was caught: {type(e).__name__}: {e}")


async def example_6_integration_with_prompt_enhancement():
    """
    Example 6: Integration with prompt enhancement engine

    This example shows how agents can use enhanced prompts
    from the prompt enhancement engine (Epics 1-4).
    """
    print("=" * 80)
    print("Example 6: Integration with Prompt Enhancement")
    print("=" * 80)

    # Simulated enhanced prompt from prompt enhancement engine
    enhanced_prompt = """
# CURRENT CONTEXT
Current file: src/auth/jwt.py
Recent commits:
- Added JWT token generation
- Updated token expiry to 24 hours

# RELATED CODE
src/auth/models.py - User model with authentication fields
src/api/auth.py - Authentication endpoints

# ARCHITECTURE
Uses FastAPI framework with JWT authentication
Database: PostgreSQL with SQLAlchemy ORM

# TEAM PATTERNS
- Always hash passwords with bcrypt
- Use Pydantic models for request/response validation
- Add comprehensive error handling
"""

    # Create context with enhanced prompt
    context = AgentContext(
        workspace_path=os.getcwd(),
        project_name="example_project",
        language="python",
        framework="fastapi",
        enhanced_prompt=enhanced_prompt,  # From Epics 1-4
    )

    orchestrator = AgentOrchestrator(context, mode="autonomous")
    result = await orchestrator.run("Add password reset functionality")

    print("\nAgent used enhanced context from prompt enhancement engine")
    print(result.summary)


async def main():
    """Run all examples"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Agent System Examples" + " " * 37 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    examples = [
        ("Simple Agent Workflow", example_1_simple_agent_workflow),
        ("Supervised Mode", example_2_supervised_mode),
        ("Individual Agents", example_3_individual_agents),
        ("Custom Context", example_4_custom_context),
        ("Error Handling", example_5_error_handling),
        ("Prompt Enhancement Integration", example_6_integration_with_prompt_enhancement),
    ]

    print("Available examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\n" + "=" * 80)
    print("Running Example 1: Simple Agent Workflow")
    print("=" * 80 + "\n")

    # Run first example by default
    # To run specific example, uncomment one of these:
    # await example_1_simple_agent_workflow()
    # await example_2_supervised_mode()
    # await example_3_individual_agents()
    # await example_4_custom_context()
    # await example_5_error_handling()
    # await example_6_integration_with_prompt_enhancement()

    print("\n✅ Example completed!")
    print("\nTo run other examples, edit this file and uncomment the desired example.")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
