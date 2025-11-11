"""
Planning Agent - Epic 9

Decomposes user requests into actionable tasks with dependencies and effort estimates.
"""

import re
import uuid
from typing import List, Dict, Any, Set
from collections import defaultdict, deque

from .base_agent import BaseAgent
from .models import ExecutionPlan, Task, TaskStatus, AgentContext


class PlanningAgent(BaseAgent):
    """
    Planning Agent that breaks down requests into executable tasks.

    Capabilities:
    - Task decomposition using pattern matching and LLM
    - Dependency detection and ordering (topological sort)
    - Effort estimation based on task complexity
    """

    # Common task patterns
    TASK_PATTERNS = {
        "add": r"(add|create|implement|build)\s+(?:a\s+)?(.+?)(?:\s+to|\s+in|\s+for|$)",
        "fix": r"(fix|resolve|correct)\s+(.+?)(?:\s+in|\s+bug|$)",
        "update": r"(update|modify|change|refactor)\s+(.+?)(?:\s+to|\s+in|$)",
        "delete": r"(delete|remove)\s+(.+?)(?:\s+from|$)",
        "test": r"(test|add\s+tests?)\s+(?:for\s+)?(.+?)(?:\s+in|$)",
    }

    def __init__(self, context: AgentContext):
        """Initialize the Planning Agent"""
        super().__init__(context)

    async def plan(self, request: str, context: AgentContext) -> ExecutionPlan:
        """
        Create an execution plan from a user request.

        Args:
            request: User request description
            context: Agent execution context

        Returns:
            ExecutionPlan with ordered tasks
        """
        self.log_info(f"Creating execution plan for: {request}")

        # Step 1: Decompose request into tasks
        tasks = await self._decompose_request(request)

        # Step 2: Detect dependencies between tasks
        self._detect_dependencies(tasks)

        # Step 3: Order tasks by dependencies (topological sort)
        ordered_tasks = self._topological_sort(tasks)

        # Step 4: Estimate effort for each task
        for task in ordered_tasks:
            task.estimated_effort = self._estimate_effort(task)

        # Step 5: Create execution plan
        plan = ExecutionPlan(
            request=request,
            tasks=ordered_tasks,
            metadata={
                "planning_method": "pattern_based",
                "total_tasks": len(ordered_tasks),
            }
        )

        self.log_info(f"Created plan with {len(ordered_tasks)} tasks")
        return plan

    async def execute(self, request: str) -> ExecutionPlan:
        """Execute planning for a request"""
        return await self.plan(request, self.context)

    async def _decompose_request(self, request: str) -> List[Task]:
        """
        Decompose user request into individual tasks.

        Uses pattern matching and heuristics to identify tasks.

        Args:
            request: User request

        Returns:
            List of tasks
        """
        tasks = []

        # Try pattern-based decomposition
        for task_type, pattern in self.TASK_PATTERNS.items():
            matches = re.finditer(pattern, request, re.IGNORECASE)
            for match in matches:
                task = self._create_task_from_match(task_type, match, request)
                if task:
                    tasks.append(task)

        # If no patterns matched, create a generic task
        if not tasks:
            tasks.append(Task(
                id=self._generate_task_id(),
                description=request,
                type="implement",
                files=self._infer_affected_files(request),
                estimated_effort=3,
            ))

        # Add implicit testing task if not present
        if not any(task.type == "test" for task in tasks):
            has_implementation = any(t.type in ["add", "update", "fix"] for t in tasks)
            if has_implementation:
                tasks.append(Task(
                    id=self._generate_task_id(),
                    description=f"Add tests for: {request}",
                    type="test",
                    files=[],
                    estimated_effort=2,
                ))

        return tasks

    def _create_task_from_match(self, task_type: str, match, request: str) -> Task:
        """
        Create a task from a regex match.

        Args:
            task_type: Type of task (add, fix, update, etc.)
            match: Regex match object
            request: Original request

        Returns:
            Task object
        """
        action = match.group(1)
        subject = match.group(2) if len(match.groups()) > 1 else request

        return Task(
            id=self._generate_task_id(),
            description=f"{action.capitalize()} {subject}",
            type=task_type,
            files=self._infer_affected_files(subject),
            estimated_effort=1,
        )

    def _infer_affected_files(self, description: str) -> List[str]:
        """
        Infer which files might be affected by a task.

        Uses simple heuristics to guess file paths from description.

        Args:
            description: Task description

        Returns:
            List of potentially affected file paths
        """
        files = []

        # Extract file paths (e.g., "src/auth/login.py")
        file_pattern = r'[\w/.-]+\.[\w]+'
        matches = re.findall(file_pattern, description)
        files.extend(matches)

        # Infer from common patterns
        if "auth" in description.lower():
            files.append("src/auth/")
        if "api" in description.lower():
            files.append("src/api/")
        if "database" in description.lower() or "model" in description.lower():
            files.append("src/models/")
        if "test" in description.lower():
            files.append("tests/")

        return list(set(files))  # Remove duplicates

    def _detect_dependencies(self, tasks: List[Task]) -> None:
        """
        Detect dependencies between tasks.

        Modifies tasks in-place to add dependency IDs.

        Args:
            tasks: List of tasks
        """
        # Test tasks depend on implementation tasks
        test_tasks = [t for t in tasks if t.type == "test"]
        impl_tasks = [t for t in tasks if t.type in ["add", "update", "fix"]]

        for test_task in test_tasks:
            for impl_task in impl_tasks:
                # Test depends on implementation
                if impl_task.id not in test_task.dependencies:
                    test_task.dependencies.append(impl_task.id)

        # File-based dependencies
        for i, task1 in enumerate(tasks):
            for task2 in tasks[i+1:]:
                # If task2 modifies files that task1 creates, it depends on task1
                if task1.type == "add" and task2.type in ["update", "test"]:
                    shared_files = set(task1.files) & set(task2.files)
                    if shared_files and task1.id not in task2.dependencies:
                        task2.dependencies.append(task1.id)

    def _topological_sort(self, tasks: List[Task]) -> List[Task]:
        """
        Order tasks using topological sort (Kahn's algorithm).

        Ensures that tasks are executed in dependency order.

        Args:
            tasks: Unordered list of tasks

        Returns:
            Ordered list of tasks
        """
        # Build adjacency list and in-degree map
        task_map = {task.id: task for task in tasks}
        in_degree = {task.id: 0 for task in tasks}
        adjacency = defaultdict(list)

        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in task_map:
                    adjacency[dep_id].append(task.id)
                    in_degree[task.id] += 1

        # Kahn's algorithm
        queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
        ordered = []

        while queue:
            task_id = queue.popleft()
            ordered.append(task_map[task_id])

            for dependent_id in adjacency[task_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        # Check for cycles
        if len(ordered) != len(tasks):
            self.log_warning("Dependency cycle detected, using partial order")
            # Add remaining tasks at the end
            remaining_ids = set(task_map.keys()) - set(t.id for t in ordered)
            for task_id in remaining_ids:
                ordered.append(task_map[task_id])

        return ordered

    def _estimate_effort(self, task: Task) -> int:
        """
        Estimate effort for a task in hours.

        Uses heuristics based on task type and complexity.

        Args:
            task: Task to estimate

        Returns:
            Estimated effort in hours
        """
        base_effort = {
            "add": 3,      # Creating new features takes time
            "fix": 2,      # Fixes are usually faster
            "update": 2,   # Updates are moderate
            "delete": 1,   # Deletion is fast
            "test": 2,     # Testing takes moderate time
        }

        effort = base_effort.get(task.type, 2)

        # Adjust based on description complexity
        description_lower = task.description.lower()

        # Increase for complex keywords
        if any(keyword in description_lower for keyword in ["authentication", "security", "payment", "database"]):
            effort += 2

        # Increase for multiple files
        if len(task.files) > 3:
            effort += 1

        # Increase for dependencies
        if len(task.dependencies) > 2:
            effort += 1

        return max(1, min(effort, 8))  # Clamp between 1-8 hours

    def _generate_task_id(self) -> str:
        """Generate a unique task ID"""
        return f"task-{uuid.uuid4().hex[:8]}"
