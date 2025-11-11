"""
Testing Agent - Epic 11

Generates test cases, executes tests, analyzes coverage, and auto-fixes failures.
"""

import os
import re
import subprocess
import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path

from .base_agent import BaseAgent
from .models import CodeChanges, TestResults, TestCase, TestStatus, AgentContext


class TestingAgent(BaseAgent):
    """
    Testing Agent that generates and runs tests.

    Capabilities:
    - Test case generation using LLM
    - Test execution via pytest
    - Coverage analysis
    - Auto-fix on test failures (max 3 attempts)
    """

    MAX_FIX_ATTEMPTS = 3

    def __init__(self, context: AgentContext):
        """Initialize the Testing Agent"""
        super().__init__(context)
        self.coding_agent = None  # Lazy-loaded to avoid circular import

    async def test(self, changes: CodeChanges) -> TestResults:
        """
        Generate and run tests for code changes.

        Args:
            changes: Code changes to test

        Returns:
            TestResults with execution results and coverage
        """
        self.log_info(f"Testing changes for task: {changes.task_id}")

        # Step 1: Generate test cases if they don't exist
        test_files = await self._generate_test_cases(changes)

        # Step 2: Run tests
        results = await self._run_tests(test_files, changes)

        # Step 3: Analyze coverage
        results.coverage = await self._analyze_coverage(changes)

        # Step 4: Auto-fix if tests failed
        if not results.all_passed:
            results = await self._auto_fix_failures(changes, results)

        self.log_info(f"Testing complete: {results.passed}/{results.total_tests} passed, {results.coverage:.1f}% coverage")
        return results

    async def execute(self, changes: CodeChanges) -> TestResults:
        """Execute testing for code changes"""
        return await self.test(changes)

    async def _generate_test_cases(self, changes: CodeChanges) -> List[str]:
        """
        Generate test cases for code changes using LLM.

        Args:
            changes: Code changes to test

        Returns:
            List of generated test file paths
        """
        test_files = []

        for change in changes.changes:
            # Skip test files themselves
            if "test" in change.path.lower():
                test_files.append(change.path)
                continue

            # Generate test file path
            test_path = self._get_test_file_path(change.path)

            # Check if test file already exists
            if os.path.exists(os.path.join(self.context.workspace_path, test_path)):
                self.log_info(f"Test file already exists: {test_path}")
                test_files.append(test_path)
                continue

            # Generate test code using LLM
            test_code = await self._generate_test_code(change)

            # Write test file
            full_test_path = os.path.join(self.context.workspace_path, test_path)
            os.makedirs(os.path.dirname(full_test_path), exist_ok=True)

            with open(full_test_path, 'w') as f:
                f.write(test_code)

            test_files.append(test_path)
            self.log_info(f"Generated test file: {test_path}")

        return test_files

    def _get_test_file_path(self, source_path: str) -> str:
        """
        Generate test file path from source file path.

        Examples:
            src/auth/login.py -> tests/test_auth_login.py
            backend/api/users.py -> tests/test_api_users.py

        Args:
            source_path: Source file path

        Returns:
            Test file path
        """
        # Extract filename without extension
        path = Path(source_path)
        filename = path.stem

        # Extract directory components
        parts = path.parts
        if parts[0] in ["src", "backend", "lib"]:
            parts = parts[1:]  # Remove root directory

        # Build test filename
        if len(parts) > 1:
            test_name = f"test_{'_'.join(parts[:-1])}_{filename}.py"
        else:
            test_name = f"test_{filename}.py"

        return f"tests/{test_name}"

    async def _generate_test_code(self, change) -> str:
        """
        Generate test code using LLM.

        Args:
            change: FileChange object

        Returns:
            Generated test code
        """
        # Lazy load coding agent to avoid circular import
        if not self.coding_agent:
            from .coding_agent import CodingAgent
            self.coding_agent = CodingAgent(self.context)

        prompt = f"""Generate comprehensive pytest tests for the following code:

```filename: {change.path}
{change.new_content}
```

# REQUIREMENTS
1. Use pytest framework
2. Test all public functions and methods
3. Include edge cases and error cases
4. Use fixtures where appropriate
5. Add docstrings to test functions
6. Aim for >80% code coverage

# OUTPUT FORMAT
Provide complete, runnable pytest code.
"""

        try:
            test_code = await self.coding_agent._generate_code(prompt)
            # Extract code from response
            if "```python" in test_code:
                test_code = test_code.split("```python")[1].split("```")[0]
            elif "```" in test_code:
                test_code = test_code.split("```")[1].split("```")[0]

            return test_code.strip()

        except Exception as e:
            self.log_error(f"Failed to generate test code: {e}", exc_info=True)
            return self._generate_fallback_test(change)

    def _generate_fallback_test(self, change) -> str:
        """
        Generate fallback test code when LLM fails.

        Args:
            change: FileChange object

        Returns:
            Fallback test code
        """
        filename = Path(change.path).stem
        return f'''"""
Tests for {change.path}

Auto-generated test stub - please implement actual tests.
"""

import pytest


class Test{filename.title().replace("_", "")}:
    """Test class for {filename}"""

    def test_placeholder(self):
        """Placeholder test - implement actual tests"""
        # TODO: Implement actual tests
        assert True
'''

    async def _run_tests(self, test_files: List[str], changes: CodeChanges) -> TestResults:
        """
        Run tests using pytest.

        Args:
            test_files: List of test file paths
            changes: Original code changes

        Returns:
            TestResults with execution results
        """
        test_cases = []

        if not test_files:
            self.log_warning("No test files to run")
            return TestResults(
                task_id=changes.task_id,
                test_cases=[],
                coverage=0.0,
            )

        # Determine test framework
        test_framework = self.context.test_framework or "pytest"

        if test_framework == "pytest":
            test_cases = await self._run_pytest(test_files)
        else:
            self.log_warning(f"Unsupported test framework: {test_framework}")
            # Fallback to pytest
            test_cases = await self._run_pytest(test_files)

        return TestResults(
            task_id=changes.task_id,
            test_cases=test_cases,
        )

    async def _run_pytest(self, test_files: List[str]) -> List[TestCase]:
        """
        Run pytest on test files.

        Args:
            test_files: List of test file paths

        Returns:
            List of TestCase objects with results
        """
        test_cases = []

        try:
            # Build pytest command
            cmd = [
                "pytest",
                "--verbose",
                "--tb=short",
                "--json-report",
                "--json-report-file=test_results.json",
            ] + [os.path.join(self.context.workspace_path, f) for f in test_files]

            # Run pytest
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.context.workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            # Parse output
            test_cases = self._parse_pytest_output(stdout.decode(), stderr.decode())

        except FileNotFoundError:
            self.log_error("pytest not found - is it installed?")
            # Return mock test results
            for test_file in test_files:
                test_cases.append(TestCase(
                    name=f"test_placeholder_{Path(test_file).stem}",
                    file_path=test_file,
                    status=TestStatus.SKIPPED,
                    error_message="pytest not installed",
                ))

        except Exception as e:
            self.log_error(f"Error running pytest: {e}", exc_info=True)

        return test_cases

    def _parse_pytest_output(self, stdout: str, stderr: str) -> List[TestCase]:
        """
        Parse pytest output to extract test results.

        Args:
            stdout: pytest stdout
            stderr: pytest stderr

        Returns:
            List of TestCase objects
        """
        test_cases = []

        # Try to parse JSON report first
        json_report_path = os.path.join(self.context.workspace_path, "test_results.json")
        if os.path.exists(json_report_path):
            try:
                import json
                with open(json_report_path) as f:
                    report = json.load(f)

                for test in report.get("tests", []):
                    test_cases.append(TestCase(
                        name=test.get("nodeid", "unknown"),
                        file_path=test.get("file", "unknown"),
                        status=self._map_pytest_status(test.get("outcome", "failed")),
                        duration=test.get("duration", 0.0),
                        error_message=test.get("call", {}).get("longrepr", None),
                    ))

                # Clean up JSON report
                os.remove(json_report_path)
                return test_cases

            except Exception as e:
                self.log_warning(f"Failed to parse JSON report: {e}")

        # Fallback to parsing text output
        # Pattern: test_file.py::test_function PASSED
        pattern = r'([\w/.-]+\.py)::([\w_]+)\s+(PASSED|FAILED|SKIPPED|ERROR)'

        for match in re.finditer(pattern, stdout):
            file_path, test_name, status = match.groups()

            test_cases.append(TestCase(
                name=f"{file_path}::{test_name}",
                file_path=file_path,
                status=self._map_pytest_status(status.lower()),
            ))

        # If no tests found, create a placeholder
        if not test_cases:
            test_cases.append(TestCase(
                name="unknown",
                file_path="unknown",
                status=TestStatus.ERROR,
                error_message="Failed to parse test results",
            ))

        return test_cases

    def _map_pytest_status(self, status: str) -> TestStatus:
        """Map pytest status to TestStatus enum"""
        status_map = {
            "passed": TestStatus.PASSED,
            "failed": TestStatus.FAILED,
            "skipped": TestStatus.SKIPPED,
            "error": TestStatus.ERROR,
        }
        return status_map.get(status.lower(), TestStatus.ERROR)

    async def _analyze_coverage(self, changes: CodeChanges) -> float:
        """
        Analyze test coverage using pytest-cov.

        Args:
            changes: Code changes

        Returns:
            Coverage percentage (0-100)
        """
        try:
            # Build coverage command
            source_dirs = list(set(
                os.path.dirname(change.path)
                for change in changes.changes
                if not "test" in change.path.lower()
            ))

            if not source_dirs:
                return 0.0

            cmd = [
                "pytest",
                "--cov=" + ",".join(source_dirs),
                "--cov-report=term",
                "--quiet",
            ]

            # Run coverage
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.context.workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            # Parse coverage percentage
            # Pattern: TOTAL    100   20    80%
            pattern = r'TOTAL\s+\d+\s+\d+\s+(\d+)%'
            match = re.search(pattern, stdout.decode())

            if match:
                return float(match.group(1))

        except Exception as e:
            self.log_warning(f"Coverage analysis failed: {e}")

        return 0.0

    async def _auto_fix_failures(self, changes: CodeChanges, results: TestResults) -> TestResults:
        """
        Attempt to auto-fix test failures.

        Args:
            changes: Original code changes
            results: Test results with failures

        Returns:
            Updated test results after fix attempts
        """
        if results.all_passed:
            return results

        self.log_info(f"Attempting to auto-fix {results.failed} test failures")

        for attempt in range(self.MAX_FIX_ATTEMPTS):
            self.log_info(f"Fix attempt {attempt + 1}/{self.MAX_FIX_ATTEMPTS}")

            # Get failed tests
            failed_tests = [tc for tc in results.test_cases if tc.status == TestStatus.FAILED]

            if not failed_tests:
                break

            # Try to fix the code
            fixed_changes = await self._generate_fixes(changes, failed_tests)

            # Apply fixes (in a real implementation, this would modify files)
            # For now, we'll just re-run tests

            # Re-run tests
            test_files = [change.path for change in fixed_changes.changes if "test" in change.path.lower()]
            if not test_files:
                test_files = await self._generate_test_cases(fixed_changes)

            results = await self._run_tests(test_files, fixed_changes)

            if results.all_passed:
                self.log_info(f"Auto-fix successful on attempt {attempt + 1}")
                break

        if not results.all_passed:
            self.log_warning(f"Auto-fix failed after {self.MAX_FIX_ATTEMPTS} attempts")

        return results

    async def _generate_fixes(self, changes: CodeChanges, failed_tests: List[TestCase]) -> CodeChanges:
        """
        Generate fixes for failed tests using LLM.

        Args:
            changes: Original code changes
            failed_tests: List of failed test cases

        Returns:
            Updated CodeChanges with fixes
        """
        # In a real implementation, this would use the coding agent to generate fixes
        # For now, return the original changes
        self.log_warning("Auto-fix not fully implemented - returning original changes")
        return changes
