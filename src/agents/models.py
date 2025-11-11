"""
Data models for autonomous code generation agents.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentState(str, Enum):
    """Agent execution state"""
    IDLE = "idle"
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"
    REVIEWING = "reviewing"
    CREATING_PR = "creating_pr"
    COMPLETED = "completed"
    FAILED = "failed"


class TestStatus(str, Enum):
    """Test execution status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class Task:
    """A single task in an execution plan"""
    id: str
    description: str
    type: str  # "create", "update", "delete", "refactor"
    files: List[str]  # Files affected by this task
    dependencies: List[str] = field(default_factory=list)  # IDs of dependent tasks
    estimated_effort: int = 1  # Estimated effort in hours
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Validate task data"""
        if not self.id:
            raise ValueError("Task ID cannot be empty")
        if not self.description:
            raise ValueError("Task description cannot be empty")


@dataclass
class ExecutionPlan:
    """Complete execution plan with ordered tasks"""
    request: str  # Original user request
    tasks: List[Task]  # Ordered list of tasks
    estimated_total_effort: int = 0  # Total estimated effort in hours
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Calculate total effort"""
        if self.estimated_total_effort == 0:
            self.estimated_total_effort = sum(task.estimated_effort for task in self.tasks)

    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute (dependencies met)"""
        ready = []
        completed_ids = {task.id for task in self.tasks if task.status == TaskStatus.COMPLETED}

        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                if all(dep_id in completed_ids for dep_id in task.dependencies):
                    ready.append(task)

        return ready


@dataclass
class FileChange:
    """A change to a single file"""
    path: str
    old_content: Optional[str] = None  # None for new files
    new_content: str = ""
    operation: str = "update"  # "create", "update", "delete"

    def __post_init__(self):
        """Validate file change"""
        if not self.path:
            raise ValueError("File path cannot be empty")
        if self.operation not in ["create", "update", "delete"]:
            raise ValueError(f"Invalid operation: {self.operation}")


@dataclass
class CodeChanges:
    """Collection of code changes for a task"""
    task_id: str
    changes: List[FileChange]
    summary: str = ""
    language: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Check if changes are valid"""
        return len(self.validation_errors) == 0

    @property
    def files_affected(self) -> List[str]:
        """Get list of affected file paths"""
        return [change.path for change in self.changes]


@dataclass
class TestCase:
    """A single test case"""
    name: str
    file_path: str
    status: TestStatus = TestStatus.SKIPPED
    duration: float = 0.0  # seconds
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None


@dataclass
class TestResults:
    """Results from test execution"""
    task_id: str
    test_cases: List[TestCase]
    coverage: float = 0.0  # Percentage (0-100)
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0  # Total duration in seconds

    def __post_init__(self):
        """Calculate test statistics"""
        if self.total_tests == 0:
            self.total_tests = len(self.test_cases)
            self.passed = sum(1 for tc in self.test_cases if tc.status == TestStatus.PASSED)
            self.failed = sum(1 for tc in self.test_cases if tc.status == TestStatus.FAILED)
            self.skipped = sum(1 for tc in self.test_cases if tc.status == TestStatus.SKIPPED)
            self.errors = sum(1 for tc in self.test_cases if tc.status == TestStatus.ERROR)
            self.duration = sum(tc.duration for tc in self.test_cases)

    @property
    def success_rate(self) -> float:
        """Calculate test success rate"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

    @property
    def all_passed(self) -> bool:
        """Check if all tests passed"""
        return self.failed == 0 and self.errors == 0


@dataclass
class ReviewIssue:
    """A code review issue"""
    severity: str  # "critical", "high", "medium", "low", "info"
    category: str  # "security", "performance", "patterns", "style", "documentation"
    file_path: str
    line_number: Optional[int] = None
    message: str = ""
    suggestion: Optional[str] = None

    def __post_init__(self):
        """Validate review issue"""
        valid_severities = ["critical", "high", "medium", "low", "info"]
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity: {self.severity}")


@dataclass
class ReviewFeedback:
    """Code review feedback"""
    task_id: str
    issues: List[ReviewIssue]
    approved: bool = False
    summary: str = ""
    security_score: float = 0.0  # 0-100
    performance_score: float = 0.0  # 0-100
    pattern_compliance: float = 0.0  # 0-100
    test_coverage_adequate: bool = False

    @property
    def critical_issues(self) -> List[ReviewIssue]:
        """Get critical issues"""
        return [issue for issue in self.issues if issue.severity == "critical"]

    @property
    def has_blockers(self) -> bool:
        """Check if there are blocking issues"""
        return len(self.critical_issues) > 0


@dataclass
class PullRequest:
    """Pull request information"""
    title: str
    description: str
    branch_name: str
    base_branch: str = "main"
    files_changed: List[str] = field(default_factory=list)
    reviewers: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AgentResult:
    """Result from agent orchestration"""
    request: str
    state: AgentState
    plan: Optional[ExecutionPlan] = None
    code_changes: List[CodeChanges] = field(default_factory=list)
    test_results: List[TestResults] = field(default_factory=list)
    review_feedback: Optional[ReviewFeedback] = None
    pull_request: Optional[PullRequest] = None
    success: bool = False
    error: Optional[str] = None
    execution_time: float = 0.0  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        """Generate a summary of the agent execution"""
        lines = [f"Request: {self.request}", f"State: {self.state.value}"]

        if self.plan:
            total_tasks = len(self.plan.tasks)
            completed_tasks = sum(1 for t in self.plan.tasks if t.status == TaskStatus.COMPLETED)
            lines.append(f"Tasks: {completed_tasks}/{total_tasks} completed")

        if self.code_changes:
            total_files = sum(len(cc.changes) for cc in self.code_changes)
            lines.append(f"Files Changed: {total_files}")

        if self.test_results:
            total_tests = sum(tr.total_tests for tr in self.test_results)
            passed_tests = sum(tr.passed for tr in self.test_results)
            lines.append(f"Tests: {passed_tests}/{total_tests} passed")

        if self.review_feedback and self.review_feedback.issues:
            lines.append(f"Review Issues: {len(self.review_feedback.issues)}")

        if self.pull_request:
            lines.append(f"PR: {self.pull_request.title}")

        lines.append(f"Success: {self.success}")
        lines.append(f"Execution Time: {self.execution_time:.2f}s")

        return "\n".join(lines)


@dataclass
class AgentContext:
    """Context provided to agents during execution"""
    workspace_path: str
    project_name: str
    language: Optional[str] = None
    framework: Optional[str] = None
    test_framework: Optional[str] = None
    coding_patterns: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    enhanced_prompt: Optional[str] = None  # From prompt enhancement engine
    memory: Dict[str, Any] = field(default_factory=dict)  # From memory system
