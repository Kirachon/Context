"""
Agent Orchestrator

Coordinates all autonomous agents and manages the workflow.
"""

import asyncio
import time
from typing import Optional, Dict, Any

from .base_agent import BaseAgent
from .models import (
    AgentContext,
    AgentResult,
    AgentState,
    ExecutionPlan,
    Task,
    TaskStatus,
    CodeChanges,
    TestResults,
    ReviewFeedback,
    PullRequest,
)
from .planning_agent import PlanningAgent
from .coding_agent import CodingAgent
from .testing_agent import TestingAgent
from .review_agent import ReviewAgent
from .pr_agent import PRAgent


class AgentOrchestrator(BaseAgent):
    """
    Orchestrates all autonomous agents to execute user requests.

    Workflow:
    1. Planning: Decompose request into tasks
    2. Coding: Generate code for each task
    3. Testing: Generate and run tests
    4. Review: Perform code review
    5. PR Creation: Create pull request

    Modes:
    - Supervised: Requires approval after each stage
    - Autonomous: Runs all stages automatically
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        context: AgentContext,
        mode: str = "supervised",
        approval_callback=None
    ):
        """
        Initialize the orchestrator.

        Args:
            context: Agent execution context
            mode: "supervised" or "autonomous"
            approval_callback: Function to call for approval in supervised mode
        """
        super().__init__(context)
        self.mode = mode
        self.approval_callback = approval_callback

        # Initialize agents
        self.planning_agent = PlanningAgent(context)
        self.coding_agent = CodingAgent(context)
        self.testing_agent = TestingAgent(context)
        self.review_agent = ReviewAgent(context)
        self.pr_agent = PRAgent(context)

    async def run(self, request: str) -> AgentResult:
        """
        Execute the full agent workflow for a request.

        Args:
            request: User request (e.g., "Add email validation")

        Returns:
            AgentResult with execution results
        """
        self.log_info(f"Starting agent orchestration: {request}")
        self.log_info(f"Mode: {self.mode}")

        start_time = time.time()
        result = AgentResult(
            request=request,
            state=AgentState.IDLE,
        )

        try:
            # Stage 1: Planning
            result.state = AgentState.PLANNING
            result.plan = await self._execute_planning(request)

            if self.mode == "supervised":
                if not await self._request_approval("Planning", result.plan):
                    result.state = AgentState.FAILED
                    result.error = "Planning rejected by user"
                    return result

            # Stage 2: Coding (for each task)
            result.state = AgentState.CODING
            code_changes_list = await self._execute_coding(result.plan)
            result.code_changes = code_changes_list

            if self.mode == "supervised":
                if not await self._request_approval("Coding", code_changes_list):
                    result.state = AgentState.FAILED
                    result.error = "Code changes rejected by user"
                    return result

            # Stage 3: Testing
            result.state = AgentState.TESTING
            test_results_list = await self._execute_testing(code_changes_list)
            result.test_results = test_results_list

            if self.mode == "supervised":
                if not await self._request_approval("Testing", test_results_list):
                    result.state = AgentState.FAILED
                    result.error = "Test results rejected by user"
                    return result

            # Stage 4: Review
            result.state = AgentState.REVIEWING
            # Combine all code changes for review
            combined_changes = self._combine_code_changes(code_changes_list)
            combined_tests = self._combine_test_results(test_results_list)
            review_feedback = await self._execute_review(combined_changes, combined_tests)
            result.review_feedback = review_feedback

            if self.mode == "supervised":
                if not await self._request_approval("Review", review_feedback):
                    result.state = AgentState.FAILED
                    result.error = "Review rejected by user"
                    return result

            # Stage 5: PR Creation
            result.state = AgentState.CREATING_PR
            pull_request = await self._execute_pr_creation(
                combined_changes,
                review_feedback,
                request
            )
            result.pull_request = pull_request

            if self.mode == "supervised":
                if not await self._request_approval("PR Creation", pull_request):
                    result.state = AgentState.FAILED
                    result.error = "PR creation rejected by user"
                    return result

            # Success!
            result.state = AgentState.COMPLETED
            result.success = True

        except Exception as e:
            self.log_error(f"Agent orchestration failed: {e}", exc_info=True)
            result.state = AgentState.FAILED
            result.error = str(e)
            result.success = False

        finally:
            result.execution_time = time.time() - start_time

        self.log_info(f"Orchestration completed: {result.state.value} in {result.execution_time:.2f}s")
        return result

    async def execute(self, request: str) -> AgentResult:
        """Execute agent orchestration"""
        return await self.run(request)

    async def _execute_planning(self, request: str) -> ExecutionPlan:
        """
        Execute planning stage with retry.

        Args:
            request: User request

        Returns:
            ExecutionPlan
        """
        self.log_info("=== Stage 1: Planning ===")

        for attempt in range(self.MAX_RETRIES):
            try:
                plan = await self.planning_agent.plan(request, self.context)
                self.log_info(f"Created plan with {len(plan.tasks)} tasks")

                # Log tasks
                for i, task in enumerate(plan.tasks, 1):
                    self.log_info(f"  Task {i}: {task.description} ({task.estimated_effort}h)")

                return plan

            except Exception as e:
                self.log_error(f"Planning attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise

        raise RuntimeError("Planning failed after all retries")

    async def _execute_coding(self, plan: ExecutionPlan) -> list[CodeChanges]:
        """
        Execute coding stage for all tasks with retry.

        Args:
            plan: Execution plan

        Returns:
            List of CodeChanges
        """
        self.log_info("=== Stage 2: Coding ===")

        code_changes_list = []

        # Execute tasks in dependency order
        while True:
            ready_tasks = plan.get_ready_tasks()
            if not ready_tasks:
                break

            # Execute ready tasks in parallel
            tasks_to_execute = []
            for task in ready_tasks:
                tasks_to_execute.append(self._execute_task_coding(task))

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks_to_execute, return_exceptions=True)

            # Update task statuses
            for task, result in zip(ready_tasks, results):
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    task.error = str(result)
                    self.log_error(f"Task {task.id} failed: {result}")
                else:
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    code_changes_list.append(result)
                    self.log_info(f"Task {task.id} completed: {len(result.changes)} files changed")

            # Check for failed tasks
            if any(task.status == TaskStatus.FAILED for task in ready_tasks):
                raise RuntimeError("Some tasks failed during coding")

        return code_changes_list

    async def _execute_task_coding(self, task: Task) -> CodeChanges:
        """
        Execute coding for a single task with retry.

        Args:
            task: Task to code

        Returns:
            CodeChanges
        """
        task.status = TaskStatus.IN_PROGRESS

        for attempt in range(self.MAX_RETRIES):
            try:
                code_changes = await self.coding_agent.code(task, self.context)

                # Validate code changes
                if not code_changes.is_valid:
                    self.log_warning(f"Code validation failed: {code_changes.validation_errors}")
                    if attempt == self.MAX_RETRIES - 1:
                        raise RuntimeError(f"Code validation failed: {code_changes.validation_errors}")
                    continue

                return code_changes

            except Exception as e:
                self.log_error(f"Coding attempt {attempt + 1} for task {task.id} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise

        raise RuntimeError(f"Coding failed for task {task.id} after all retries")

    async def _execute_testing(self, code_changes_list: list[CodeChanges]) -> list[TestResults]:
        """
        Execute testing stage with retry.

        Args:
            code_changes_list: List of code changes to test

        Returns:
            List of TestResults
        """
        self.log_info("=== Stage 3: Testing ===")

        test_results_list = []

        for changes in code_changes_list:
            for attempt in range(self.MAX_RETRIES):
                try:
                    test_results = await self.testing_agent.test(changes)
                    test_results_list.append(test_results)

                    self.log_info(
                        f"Tests for task {changes.task_id}: "
                        f"{test_results.passed}/{test_results.total_tests} passed, "
                        f"{test_results.coverage:.1f}% coverage"
                    )

                    break

                except Exception as e:
                    self.log_error(f"Testing attempt {attempt + 1} failed: {e}")
                    if attempt == self.MAX_RETRIES - 1:
                        # Don't fail the whole workflow if testing fails
                        # Create empty test results
                        test_results_list.append(TestResults(
                            task_id=changes.task_id,
                            test_cases=[],
                        ))

        return test_results_list

    async def _execute_review(
        self,
        changes: CodeChanges,
        test_results: TestResults
    ) -> ReviewFeedback:
        """
        Execute review stage with retry.

        Args:
            changes: Combined code changes
            test_results: Combined test results

        Returns:
            ReviewFeedback
        """
        self.log_info("=== Stage 4: Review ===")

        for attempt in range(self.MAX_RETRIES):
            try:
                review = await self.review_agent.review(changes, test_results)

                self.log_info(
                    f"Review complete: "
                    f"{'✅ Approved' if review.approved else '⚠️ Needs attention'}, "
                    f"{len(review.issues)} issues"
                )

                if review.critical_issues:
                    self.log_warning(f"Found {len(review.critical_issues)} critical issues")
                    for issue in review.critical_issues:
                        self.log_warning(f"  - {issue.message} ({issue.file_path})")

                return review

            except Exception as e:
                self.log_error(f"Review attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise

        raise RuntimeError("Review failed after all retries")

    async def _execute_pr_creation(
        self,
        changes: CodeChanges,
        review: ReviewFeedback,
        request: str
    ) -> PullRequest:
        """
        Execute PR creation stage with retry.

        Args:
            changes: Code changes
            review: Review feedback
            request: Original request

        Returns:
            PullRequest
        """
        self.log_info("=== Stage 5: PR Creation ===")

        for attempt in range(self.MAX_RETRIES):
            try:
                pull_request = await self.pr_agent.create_pr(changes, review, request)

                self.log_info(
                    f"PR created: {pull_request.title} "
                    f"({pull_request.branch_name})"
                )

                if pull_request.pr_url:
                    self.log_info(f"PR URL: {pull_request.pr_url}")

                return pull_request

            except Exception as e:
                self.log_error(f"PR creation attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    # Don't fail if PR creation fails - still return the branch
                    self.log_warning("PR creation failed, but changes are committed locally")
                    # Create a fallback PR object
                    return PullRequest(
                        title=request,
                        description="PR creation failed",
                        branch_name="agent/fallback",
                        files_changed=changes.files_affected,
                    )

        raise RuntimeError("PR creation failed after all retries")

    def _combine_code_changes(self, code_changes_list: list[CodeChanges]) -> CodeChanges:
        """Combine multiple CodeChanges into one"""
        if not code_changes_list:
            return CodeChanges(task_id="combined", changes=[])

        combined = CodeChanges(
            task_id="combined",
            changes=[],
            summary="Combined changes from all tasks",
        )

        for cc in code_changes_list:
            combined.changes.extend(cc.changes)
            combined.validation_errors.extend(cc.validation_errors)

        return combined

    def _combine_test_results(self, test_results_list: list[TestResults]) -> TestResults:
        """Combine multiple TestResults into one"""
        if not test_results_list:
            return TestResults(task_id="combined", test_cases=[])

        combined = TestResults(
            task_id="combined",
            test_cases=[],
        )

        for tr in test_results_list:
            combined.test_cases.extend(tr.test_cases)
            combined.total_tests += tr.total_tests
            combined.passed += tr.passed
            combined.failed += tr.failed
            combined.skipped += tr.skipped
            combined.errors += tr.errors
            combined.duration += tr.duration

        # Average coverage
        if test_results_list:
            combined.coverage = sum(tr.coverage for tr in test_results_list) / len(test_results_list)

        return combined

    async def _request_approval(self, stage: str, data: Any) -> bool:
        """
        Request approval from user in supervised mode.

        Args:
            stage: Stage name
            data: Data to approve

        Returns:
            True if approved, False otherwise
        """
        if self.mode != "supervised":
            return True

        self.log_info(f"Requesting approval for: {stage}")

        if self.approval_callback:
            return await self.approval_callback(stage, data)

        # Default: always approve
        return True


# CLI integration function
async def run_agent_cli(request: str, workspace_path: str, mode: str = "supervised") -> AgentResult:
    """
    Run agent from CLI.

    Args:
        request: User request
        workspace_path: Path to workspace
        mode: "supervised" or "autonomous"

    Returns:
        AgentResult
    """
    # Create context
    context = AgentContext(
        workspace_path=workspace_path,
        project_name="unknown",
        language="python",
        test_framework="pytest",
    )

    # Create orchestrator
    orchestrator = AgentOrchestrator(context, mode=mode)

    # Run
    result = await orchestrator.run(request)

    return result
