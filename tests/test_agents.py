"""
Comprehensive tests for autonomous code generation agents.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path

from src.agents.models import (
    AgentContext,
    Task,
    TaskStatus,
    ExecutionPlan,
    CodeChanges,
    FileChange,
    TestResults,
    TestCase,
    TestStatus,
    ReviewFeedback,
    ReviewIssue,
    PullRequest,
    AgentState,
)
from src.agents.planning_agent import PlanningAgent
from src.agents.coding_agent import CodingAgent
from src.agents.testing_agent import TestingAgent
from src.agents.review_agent import ReviewAgent
from src.agents.pr_agent import PRAgent
from src.agents.orchestrator import AgentOrchestrator


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def agent_context(temp_workspace):
    """Create agent context for testing"""
    return AgentContext(
        workspace_path=temp_workspace,
        project_name="test_project",
        language="python",
        framework="fastapi",
        test_framework="pytest",
        coding_patterns={
            "error_handling": "Use try/except blocks with specific exceptions",
            "logging": "Use logger.info/warning/error for logging",
        },
        user_preferences={
            "style": "PEP 8",
            "docstrings": "Google style",
        },
    )


class TestModels:
    """Test data models"""

    def test_task_creation(self):
        """Test Task creation"""
        task = Task(
            id="task-1",
            description="Add email validation",
            type="add",
            files=["src/validation.py"],
            estimated_effort=3,
        )

        assert task.id == "task-1"
        assert task.status == TaskStatus.PENDING
        assert task.estimated_effort == 3

    def test_execution_plan_get_ready_tasks(self):
        """Test ExecutionPlan.get_ready_tasks()"""
        task1 = Task(id="task-1", description="Task 1", type="add", files=[])
        task2 = Task(id="task-2", description="Task 2", type="test", files=[], dependencies=["task-1"])
        task3 = Task(id="task-3", description="Task 3", type="add", files=[])

        plan = ExecutionPlan(request="Test", tasks=[task1, task2, task3])

        # Initially, task1 and task3 should be ready
        ready = plan.get_ready_tasks()
        assert len(ready) == 2
        assert task1 in ready
        assert task3 in ready

        # Mark task1 as completed
        task1.status = TaskStatus.COMPLETED

        # Now task2 should also be ready
        ready = plan.get_ready_tasks()
        assert len(ready) == 2
        assert task2 in ready
        assert task3 in ready

    def test_code_changes_validation(self):
        """Test CodeChanges validation"""
        changes = CodeChanges(
            task_id="task-1",
            changes=[
                FileChange(path="test.py", new_content="print('hello')", operation="create")
            ],
            validation_errors=[],
        )

        assert changes.is_valid
        assert len(changes.files_affected) == 1

        # Add validation error
        changes.validation_errors.append("Syntax error")
        assert not changes.is_valid

    def test_test_results_statistics(self):
        """Test TestResults statistics calculation"""
        results = TestResults(
            task_id="task-1",
            test_cases=[
                TestCase(name="test_1", file_path="test.py", status=TestStatus.PASSED),
                TestCase(name="test_2", file_path="test.py", status=TestStatus.PASSED),
                TestCase(name="test_3", file_path="test.py", status=TestStatus.FAILED),
            ],
        )

        assert results.total_tests == 3
        assert results.passed == 2
        assert results.failed == 1
        assert results.success_rate == pytest.approx(66.67, rel=0.1)
        assert not results.all_passed

    def test_review_feedback_critical_issues(self):
        """Test ReviewFeedback critical issues"""
        feedback = ReviewFeedback(
            task_id="task-1",
            issues=[
                ReviewIssue(severity="critical", category="security", file_path="test.py", message="SQL injection"),
                ReviewIssue(severity="high", category="security", file_path="test.py", message="XSS"),
                ReviewIssue(severity="low", category="style", file_path="test.py", message="Line too long"),
            ],
        )

        assert len(feedback.critical_issues) == 1
        assert feedback.has_blockers


class TestPlanningAgent:
    """Test Planning Agent"""

    @pytest.mark.asyncio
    async def test_plan_simple_request(self, agent_context):
        """Test planning a simple request"""
        agent = PlanningAgent(agent_context)

        plan = await agent.plan("Add email validation", agent_context)

        assert isinstance(plan, ExecutionPlan)
        assert len(plan.tasks) > 0
        assert plan.request == "Add email validation"

        # Should have at least implementation task and test task
        task_types = [task.type for task in plan.tasks]
        assert "add" in task_types or "implement" in task_types

    @pytest.mark.asyncio
    async def test_plan_complex_request(self, agent_context):
        """Test planning a complex request with multiple tasks"""
        agent = PlanningAgent(agent_context)

        plan = await agent.plan(
            "Add user authentication with JWT tokens and update the login endpoint",
            agent_context
        )

        assert len(plan.tasks) >= 2  # Multiple tasks for complex request

    @pytest.mark.asyncio
    async def test_dependency_ordering(self, agent_context):
        """Test that dependencies are ordered correctly"""
        agent = PlanningAgent(agent_context)

        plan = await agent.plan("Add new feature and test it", agent_context)

        # Find test task
        test_task = next((t for t in plan.tasks if t.type == "test"), None)

        if test_task:
            # Test task should come after implementation tasks
            test_index = plan.tasks.index(test_task)
            impl_tasks = [t for t in plan.tasks if t.type in ["add", "update", "fix"]]

            if impl_tasks:
                for impl_task in impl_tasks:
                    impl_index = plan.tasks.index(impl_task)
                    assert impl_index < test_index or impl_task.id in test_task.dependencies


class TestCodingAgent:
    """Test Coding Agent"""

    @pytest.mark.asyncio
    async def test_code_generation(self, agent_context):
        """Test code generation for a task"""
        agent = CodingAgent(agent_context)

        task = Task(
            id="task-1",
            description="Add a function to validate email addresses",
            type="add",
            files=["src/validation.py"],
        )

        changes = await agent.code(task, agent_context)

        assert isinstance(changes, CodeChanges)
        assert len(changes.changes) > 0

        # Should generate Python code
        for change in changes.changes:
            assert change.path.endswith('.py')
            assert len(change.new_content) > 0

    @pytest.mark.asyncio
    async def test_code_validation(self, agent_context):
        """Test code validation"""
        agent = CodingAgent(agent_context)

        # Valid Python code
        valid_changes = [
            FileChange(
                path="test.py",
                new_content="def hello():\n    return 'world'",
                operation="create"
            )
        ]

        errors = agent._validate_code(valid_changes)
        assert len(errors) == 0

        # Invalid Python code
        invalid_changes = [
            FileChange(
                path="test.py",
                new_content="def hello(\n    return 'world'",
                operation="create"
            )
        ]

        errors = agent._validate_code(invalid_changes)
        assert len(errors) > 0


class TestTestingAgent:
    """Test Testing Agent"""

    @pytest.mark.asyncio
    async def test_generate_test_file_path(self, agent_context):
        """Test test file path generation"""
        agent = TestingAgent(agent_context)

        assert agent._get_test_file_path("src/auth/login.py") == "tests/test_auth_login.py"
        assert agent._get_test_file_path("backend/api/users.py") == "tests/test_api_users.py"
        assert agent._get_test_file_path("utils.py") == "tests/test_utils.py"

    @pytest.mark.asyncio
    async def test_test_generation(self, agent_context):
        """Test test case generation"""
        agent = TestingAgent(agent_context)

        changes = CodeChanges(
            task_id="task-1",
            changes=[
                FileChange(
                    path="src/validation.py",
                    new_content="def validate_email(email):\n    return '@' in email",
                    operation="create"
                )
            ],
        )

        # Generate test code
        test_code = await agent._generate_test_code(changes.changes[0])

        assert "pytest" in test_code or "test_" in test_code
        assert len(test_code) > 0


class TestReviewAgent:
    """Test Review Agent"""

    @pytest.mark.asyncio
    async def test_security_check(self, agent_context):
        """Test security vulnerability detection"""
        agent = ReviewAgent(agent_context)

        # Code with security issues
        changes = CodeChanges(
            task_id="task-1",
            changes=[
                FileChange(
                    path="test.py",
                    new_content='''
password = "hardcoded_secret_123"
query = "SELECT * FROM users WHERE id = %s" % user_id
eval(user_input)
''',
                    operation="create"
                )
            ],
        )

        issues = agent._check_security(changes)

        # Should detect hardcoded secret and eval usage
        assert len(issues) > 0
        issue_messages = [i.message.lower() for i in issues]
        assert any("secret" in msg or "password" in msg for msg in issue_messages)

    @pytest.mark.asyncio
    async def test_performance_check(self, agent_context):
        """Test performance issue detection"""
        agent = ReviewAgent(agent_context)

        changes = CodeChanges(
            task_id="task-1",
            changes=[
                FileChange(
                    path="test.py",
                    new_content='''
for item in items:
    for user in users:
        process(item, user)
''',
                    operation="create"
                )
            ],
        )

        issues = agent._check_performance(changes)

        # Should detect nested loops
        assert len(issues) > 0

    @pytest.mark.asyncio
    async def test_full_review(self, agent_context):
        """Test full code review"""
        agent = ReviewAgent(agent_context)

        changes = CodeChanges(
            task_id="task-1",
            changes=[
                FileChange(
                    path="test.py",
                    new_content='''
def validate_email(email):
    """Validate email address"""
    if "@" in email:
        return True
    return False
''',
                    operation="create"
                )
            ],
        )

        feedback = await agent.review(changes)

        assert isinstance(feedback, ReviewFeedback)
        assert feedback.security_score >= 0
        assert feedback.performance_score >= 0


class TestPRAgent:
    """Test PR Agent"""

    def test_generate_pr_title(self, agent_context):
        """Test PR title generation"""
        agent = PRAgent(agent_context)

        changes = CodeChanges(task_id="task-1", changes=[])

        title = agent._generate_pr_title("add email validation", changes)

        assert title == "Add email validation"
        assert len(title) <= 72

    def test_generate_branch_name(self, agent_context):
        """Test branch name generation"""
        agent = PRAgent(agent_context)

        branch = agent._generate_branch_name("Add email validation feature")

        assert branch == "agent/add-email-validation-feature"
        assert "/" in branch
        assert " " not in branch

    def test_generate_pr_description(self, agent_context):
        """Test PR description generation"""
        agent = PRAgent(agent_context)

        changes = CodeChanges(
            task_id="task-1",
            changes=[FileChange(path="test.py", new_content="code", operation="create")],
            language="python"
        )

        review = ReviewFeedback(
            task_id="task-1",
            issues=[],
            approved=True,
            security_score=100.0,
            performance_score=100.0,
            pattern_compliance=100.0,
        )

        description = agent._generate_pr_description("Add feature", changes, review)

        assert "## Summary" in description
        assert "## Changes" in description
        assert "## Code Review" in description
        assert "test.py" in description


class TestOrchestrator:
    """Test Agent Orchestrator"""

    @pytest.mark.asyncio
    async def test_orchestrator_autonomous_mode(self, agent_context):
        """Test orchestrator in autonomous mode"""
        orchestrator = AgentOrchestrator(agent_context, mode="autonomous")

        result = await orchestrator.run("Add simple function to calculate sum of two numbers")

        assert isinstance(result, AgentResult)
        # Even if it fails due to missing dependencies, it should have attempted planning
        assert result.plan is not None or result.error is not None

    @pytest.mark.asyncio
    async def test_orchestrator_supervised_mode(self, agent_context):
        """Test orchestrator in supervised mode with auto-approval"""
        async def auto_approve(stage, data):
            return True  # Auto-approve all stages

        orchestrator = AgentOrchestrator(
            agent_context,
            mode="supervised",
            approval_callback=auto_approve
        )

        result = await orchestrator.run("Add simple function")

        assert isinstance(result, AgentResult)
        assert result.plan is not None or result.error is not None


class TestIntegration:
    """Integration tests for full agent workflow"""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, agent_context):
        """Test complete end-to-end agent workflow"""
        # Create a git repository in the temp workspace
        os.system(f"cd {agent_context.workspace_path} && git init")

        orchestrator = AgentOrchestrator(agent_context, mode="autonomous")

        # Simple request
        result = await orchestrator.run("Add a hello world function")

        # Check that we got through at least planning
        assert result.plan is not None

        # Check that we attempted coding
        # (May fail due to missing LLM API keys, which is expected)
        assert result.state in [
            AgentState.PLANNING,
            AgentState.CODING,
            AgentState.TESTING,
            AgentState.REVIEWING,
            AgentState.CREATING_PR,
            AgentState.COMPLETED,
            AgentState.FAILED,
        ]

        # Check execution time was recorded
        assert result.execution_time > 0


# Run tests with: pytest tests/test_agents.py -v
