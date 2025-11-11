"""
Review Agent - Epic 12

Performs code review checking patterns, security, performance, and quality.
"""

import re
import ast
from typing import List, Dict, Any
from pathlib import Path

from .base_agent import BaseAgent
from .models import CodeChanges, ReviewFeedback, ReviewIssue, TestResults, AgentContext


class ReviewAgent(BaseAgent):
    """
    Review Agent that performs automated code review.

    Capabilities:
    - Pattern compliance checking
    - Security vulnerability scanning
    - Performance analysis
    - Documentation verification
    - Test coverage verification
    """

    # Security patterns to check
    SECURITY_PATTERNS = {
        "sql_injection": r"execute\s*\(\s*[\"'].*%s.*[\"']\s*%",
        "xss": r"innerHTML\s*=",
        "hardcoded_secret": r"(password|secret|api_key)\s*=\s*[\"'][^\"']+[\"']",
        "eval_usage": r"\beval\s*\(",
    }

    # Performance anti-patterns
    PERFORMANCE_ANTIPATTERNS = {
        "nested_loops": r"for\s+.*:\s+for\s+",
        "multiple_db_calls": r"(\.get\(|\.filter\(|\.all\(\)).*\n.*\.(get\(|filter\(|all\(\))",
    }

    def __init__(self, context: AgentContext):
        """Initialize the Review Agent"""
        super().__init__(context)

    async def review(self, changes: CodeChanges, test_results: TestResults = None) -> ReviewFeedback:
        """
        Perform code review on changes.

        Args:
            changes: Code changes to review
            test_results: Optional test results

        Returns:
            ReviewFeedback with issues and scores
        """
        self.log_info(f"Reviewing changes for task: {changes.task_id}")

        issues = []

        # Step 1: Check security
        security_issues = self._check_security(changes)
        issues.extend(security_issues)

        # Step 2: Check performance
        performance_issues = self._check_performance(changes)
        issues.extend(performance_issues)

        # Step 3: Check patterns
        pattern_issues = self._check_patterns(changes)
        issues.extend(pattern_issues)

        # Step 4: Check documentation
        doc_issues = self._check_documentation(changes)
        issues.extend(doc_issues)

        # Step 5: Check code style
        style_issues = self._check_style(changes)
        issues.extend(style_issues)

        # Calculate scores
        security_score = self._calculate_security_score(security_issues)
        performance_score = self._calculate_performance_score(performance_issues)
        pattern_compliance = self._calculate_pattern_compliance(pattern_issues)

        # Check test coverage
        test_coverage_adequate = False
        if test_results:
            test_coverage_adequate = test_results.coverage >= 80.0

        # Determine if approved
        approved = (
            len([i for i in issues if i.severity == "critical"]) == 0 and
            security_score >= 70.0 and
            performance_score >= 70.0
        )

        feedback = ReviewFeedback(
            task_id=changes.task_id,
            issues=issues,
            approved=approved,
            summary=self._generate_summary(issues, approved),
            security_score=security_score,
            performance_score=performance_score,
            pattern_compliance=pattern_compliance,
            test_coverage_adequate=test_coverage_adequate,
        )

        self.log_info(f"Review complete: {len(issues)} issues found, approved={approved}")
        return feedback

    async def execute(self, changes: CodeChanges, test_results: TestResults = None) -> ReviewFeedback:
        """Execute code review"""
        return await self.review(changes, test_results)

    def _check_security(self, changes: CodeChanges) -> List[ReviewIssue]:
        """
        Check for security vulnerabilities.

        Args:
            changes: Code changes

        Returns:
            List of security issues
        """
        issues = []

        for change in changes.changes:
            content = change.new_content

            # Check each security pattern
            for vuln_type, pattern in self.SECURITY_PATTERNS.items():
                matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append(ReviewIssue(
                        severity="critical",
                        category="security",
                        file_path=change.path,
                        line_number=line_num,
                        message=f"Potential {vuln_type.replace('_', ' ')} vulnerability",
                        suggestion=self._get_security_suggestion(vuln_type),
                    ))

            # Check for missing input validation
            if "input(" in content or "request." in content:
                if "validate" not in content.lower() and "sanitize" not in content.lower():
                    issues.append(ReviewIssue(
                        severity="high",
                        category="security",
                        file_path=change.path,
                        message="Missing input validation",
                        suggestion="Add input validation before processing user input",
                    ))

        return issues

    def _check_performance(self, changes: CodeChanges) -> List[ReviewIssue]:
        """
        Check for performance issues.

        Args:
            changes: Code changes

        Returns:
            List of performance issues
        """
        issues = []

        for change in changes.changes:
            content = change.new_content

            # Check each performance anti-pattern
            for antipattern, pattern in self.PERFORMANCE_ANTIPATTERNS.items():
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append(ReviewIssue(
                        severity="medium",
                        category="performance",
                        file_path=change.path,
                        line_number=line_num,
                        message=f"Potential performance issue: {antipattern.replace('_', ' ')}",
                        suggestion=self._get_performance_suggestion(antipattern),
                    ))

            # Check for N+1 queries (Python ORM)
            if ".filter(" in content and ".all()" in content:
                if "select_related" not in content and "prefetch_related" not in content:
                    issues.append(ReviewIssue(
                        severity="medium",
                        category="performance",
                        file_path=change.path,
                        message="Potential N+1 query",
                        suggestion="Consider using select_related() or prefetch_related()",
                    ))

        return issues

    def _check_patterns(self, changes: CodeChanges) -> List[ReviewIssue]:
        """
        Check compliance with coding patterns.

        Args:
            changes: Code changes

        Returns:
            List of pattern issues
        """
        issues = []

        for change in changes.changes:
            # Skip non-Python files for now
            if not change.path.endswith('.py'):
                continue

            content = change.new_content

            # Check for missing error handling
            if "def " in content:
                has_try_except = "try:" in content and "except" in content
                has_raise = "raise " in content

                if not has_try_except and not has_raise:
                    issues.append(ReviewIssue(
                        severity="medium",
                        category="patterns",
                        file_path=change.path,
                        message="Missing error handling",
                        suggestion="Add try/except blocks or raise exceptions for error cases",
                    ))

            # Check for type hints
            if "def " in content:
                func_pattern = r'def\s+\w+\s*\([^)]*\)\s*:'
                func_with_hints = r'def\s+\w+\s*\([^)]*:\s*\w+[^)]*\)\s*->\s*\w+'

                total_functions = len(re.findall(func_pattern, content))
                functions_with_hints = len(re.findall(func_with_hints, content))

                if total_functions > 0 and functions_with_hints / total_functions < 0.5:
                    issues.append(ReviewIssue(
                        severity="low",
                        category="patterns",
                        file_path=change.path,
                        message="Missing type hints on functions",
                        suggestion="Add type hints to function parameters and return values",
                    ))

        return issues

    def _check_documentation(self, changes: CodeChanges) -> List[ReviewIssue]:
        """
        Check for adequate documentation.

        Args:
            changes: Code changes

        Returns:
            List of documentation issues
        """
        issues = []

        for change in changes.changes:
            if not change.path.endswith('.py'):
                continue

            content = change.new_content

            # Check for module docstring
            try:
                tree = ast.parse(content)
                if not ast.get_docstring(tree):
                    issues.append(ReviewIssue(
                        severity="low",
                        category="documentation",
                        file_path=change.path,
                        line_number=1,
                        message="Missing module docstring",
                        suggestion="Add a docstring at the top of the file",
                    ))

                # Check for function docstrings
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Skip private functions
                        if node.name.startswith('_') and not node.name.startswith('__'):
                            continue

                        if not ast.get_docstring(node):
                            issues.append(ReviewIssue(
                                severity="low",
                                category="documentation",
                                file_path=change.path,
                                line_number=node.lineno,
                                message=f"Missing docstring for function '{node.name}'",
                                suggestion="Add a docstring describing the function's purpose",
                            ))

                    elif isinstance(node, ast.ClassDef):
                        if not ast.get_docstring(node):
                            issues.append(ReviewIssue(
                                severity="medium",
                                category="documentation",
                                file_path=change.path,
                                line_number=node.lineno,
                                message=f"Missing docstring for class '{node.name}'",
                                suggestion="Add a docstring describing the class's purpose",
                            ))

            except SyntaxError:
                # Skip files with syntax errors (will be caught by validation)
                pass

        return issues

    def _check_style(self, changes: CodeChanges) -> List[ReviewIssue]:
        """
        Check code style compliance.

        Args:
            changes: Code changes

        Returns:
            List of style issues
        """
        issues = []

        for change in changes.changes:
            if not change.path.endswith('.py'):
                continue

            content = change.new_content
            lines = content.split('\n')

            # Check line length (PEP 8: max 79 characters)
            for i, line in enumerate(lines, start=1):
                if len(line) > 88:  # Using Black's default of 88
                    issues.append(ReviewIssue(
                        severity="low",
                        category="style",
                        file_path=change.path,
                        line_number=i,
                        message=f"Line too long ({len(line)} > 88 characters)",
                        suggestion="Break line into multiple lines",
                    ))

            # Check for trailing whitespace
            for i, line in enumerate(lines, start=1):
                if line.endswith(' ') or line.endswith('\t'):
                    issues.append(ReviewIssue(
                        severity="info",
                        category="style",
                        file_path=change.path,
                        line_number=i,
                        message="Trailing whitespace",
                        suggestion="Remove trailing whitespace",
                    ))

        return issues

    def _calculate_security_score(self, issues: List[ReviewIssue]) -> float:
        """Calculate security score (0-100)"""
        if not issues:
            return 100.0

        critical = sum(1 for i in issues if i.severity == "critical")
        high = sum(1 for i in issues if i.severity == "high")

        # Deduct points for each issue
        score = 100.0 - (critical * 30) - (high * 15)
        return max(0.0, score)

    def _calculate_performance_score(self, issues: List[ReviewIssue]) -> float:
        """Calculate performance score (0-100)"""
        if not issues:
            return 100.0

        # Deduct points for each performance issue
        score = 100.0 - (len(issues) * 10)
        return max(0.0, score)

    def _calculate_pattern_compliance(self, issues: List[ReviewIssue]) -> float:
        """Calculate pattern compliance score (0-100)"""
        if not issues:
            return 100.0

        # Deduct points for each pattern violation
        score = 100.0 - (len(issues) * 5)
        return max(0.0, score)

    def _generate_summary(self, issues: List[ReviewIssue], approved: bool) -> str:
        """Generate review summary"""
        if approved:
            return f"Code review passed with {len(issues)} minor issues"
        else:
            critical = len([i for i in issues if i.severity == "critical"])
            high = len([i for i in issues if i.severity == "high"])
            return f"Code review failed: {critical} critical and {high} high severity issues"

    def _get_security_suggestion(self, vuln_type: str) -> str:
        """Get security fix suggestion"""
        suggestions = {
            "sql_injection": "Use parameterized queries or ORM instead of string formatting",
            "xss": "Use textContent instead of innerHTML or sanitize input",
            "hardcoded_secret": "Move secrets to environment variables or secret management system",
            "eval_usage": "Avoid using eval() - use safer alternatives like ast.literal_eval()",
        }
        return suggestions.get(vuln_type, "Review and fix security issue")

    def _get_performance_suggestion(self, antipattern: str) -> str:
        """Get performance fix suggestion"""
        suggestions = {
            "nested_loops": "Consider using list comprehensions or optimizing algorithm",
            "multiple_db_calls": "Batch database calls or use eager loading",
        }
        return suggestions.get(antipattern, "Optimize code for better performance")
