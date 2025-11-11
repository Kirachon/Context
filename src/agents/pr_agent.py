"""
PR Agent - Epic 12

Creates pull requests with title, description, and reviewer selection.
"""

import os
import re
import subprocess
import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from .base_agent import BaseAgent
from .models import (
    CodeChanges,
    ReviewFeedback,
    PullRequest,
    AgentContext,
)


class PRAgent(BaseAgent):
    """
    PR Agent that creates GitHub pull requests.

    Capabilities:
    - Generate PR title and description
    - Create git branch
    - Commit changes
    - Push to remote
    - Create GitHub PR via API
    - Select reviewers from CODEOWNERS
    """

    def __init__(self, context: AgentContext):
        """Initialize the PR Agent"""
        super().__init__(context)
        self.github_token = os.getenv("GITHUB_TOKEN")

    async def create_pr(
        self,
        changes: CodeChanges,
        review: ReviewFeedback,
        request: str
    ) -> PullRequest:
        """
        Create a pull request for code changes.

        Args:
            changes: Code changes to PR
            review: Code review feedback
            request: Original user request

        Returns:
            PullRequest object with PR details
        """
        self.log_info(f"Creating pull request for: {request}")

        # Step 1: Generate PR title and description
        title = self._generate_pr_title(request, changes)
        description = self._generate_pr_description(request, changes, review)

        # Step 2: Create git branch
        branch_name = self._generate_branch_name(request)
        await self._create_branch(branch_name)

        # Step 3: Commit changes
        commit_message = self._generate_commit_message(request, changes)
        await self._commit_changes(changes, commit_message)

        # Step 4: Push to remote
        await self._push_branch(branch_name)

        # Step 5: Select reviewers
        reviewers = await self._select_reviewers(changes)

        # Step 6: Create GitHub PR
        pr_url, pr_number = await self._create_github_pr(
            title=title,
            description=description,
            branch=branch_name,
            reviewers=reviewers,
        )

        # Step 7: Create PullRequest object
        pull_request = PullRequest(
            title=title,
            description=description,
            branch_name=branch_name,
            files_changed=changes.files_affected,
            reviewers=reviewers,
            labels=self._generate_labels(changes, review),
            pr_url=pr_url,
            pr_number=pr_number,
        )

        self.log_info(f"Pull request created: {pr_url or branch_name}")
        return pull_request

    async def execute(
        self,
        changes: CodeChanges,
        review: ReviewFeedback,
        request: str
    ) -> PullRequest:
        """Execute PR creation"""
        return await self.create_pr(changes, review, request)

    def _generate_pr_title(self, request: str, changes: CodeChanges) -> str:
        """
        Generate PR title from request.

        Args:
            request: Original user request
            changes: Code changes

        Returns:
            PR title
        """
        # Clean up the request to make a good title
        title = request.strip()

        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:]

        # Remove trailing punctuation
        title = title.rstrip('.!?')

        # Limit length
        if len(title) > 72:
            title = title[:69] + "..."

        return title

    def _generate_pr_description(
        self,
        request: str,
        changes: CodeChanges,
        review: ReviewFeedback
    ) -> str:
        """
        Generate comprehensive PR description.

        Args:
            request: Original user request
            changes: Code changes
            review: Code review feedback

        Returns:
            PR description in markdown
        """
        sections = []

        # Summary
        sections.append("## Summary")
        sections.append(f"{request}\n")

        # Changes
        sections.append("## Changes")
        sections.append(f"- **Files Changed**: {len(changes.files_affected)}")
        sections.append(f"- **Language**: {changes.language or 'Unknown'}")
        sections.append("")

        # File list
        sections.append("### Files Modified")
        for file_path in changes.files_affected:
            sections.append(f"- `{file_path}`")
        sections.append("")

        # Code Review Results
        sections.append("## Code Review")
        sections.append(f"- **Status**: {'✅ Approved' if review.approved else '⚠️ Needs Attention'}")
        sections.append(f"- **Security Score**: {review.security_score:.1f}/100")
        sections.append(f"- **Performance Score**: {review.performance_score:.1f}/100")
        sections.append(f"- **Pattern Compliance**: {review.pattern_compliance:.1f}/100")
        sections.append(f"- **Test Coverage Adequate**: {'✅ Yes' if review.test_coverage_adequate else '❌ No'}")
        sections.append("")

        # Issues
        if review.issues:
            sections.append("### Review Issues")

            # Group by severity
            for severity in ["critical", "high", "medium", "low", "info"]:
                severity_issues = [i for i in review.issues if i.severity == severity]
                if severity_issues:
                    sections.append(f"\n**{severity.upper()}**")
                    for issue in severity_issues:
                        location = f"{issue.file_path}"
                        if issue.line_number:
                            location += f":{issue.line_number}"
                        sections.append(f"- [{issue.category}] {issue.message} ({location})")
                        if issue.suggestion:
                            sections.append(f"  - *Suggestion: {issue.suggestion}*")

            sections.append("")

        # Testing
        sections.append("## Testing")
        sections.append("- [ ] Unit tests pass")
        sections.append("- [ ] Integration tests pass")
        sections.append("- [ ] Manual testing completed")
        sections.append("")

        # Checklist
        sections.append("## Checklist")
        sections.append("- [x] Code follows project patterns")
        sections.append("- [x] Security review completed")
        sections.append("- [x] Performance review completed")
        sections.append("- [ ] Documentation updated")
        sections.append("- [ ] Changelog updated")
        sections.append("")

        # Auto-generated notice
        sections.append("---")
        sections.append("*This PR was automatically generated by Context Workspace AI Agents*")

        return "\n".join(sections)

    def _generate_branch_name(self, request: str) -> str:
        """
        Generate git branch name from request.

        Args:
            request: Original user request

        Returns:
            Branch name
        """
        # Convert to lowercase and replace spaces with hyphens
        branch = re.sub(r'[^a-z0-9]+', '-', request.lower())

        # Remove leading/trailing hyphens
        branch = branch.strip('-')

        # Limit length
        if len(branch) > 50:
            branch = branch[:50].rstrip('-')

        # Add prefix
        prefix = "agent"
        return f"{prefix}/{branch}"

    def _generate_commit_message(self, request: str, changes: CodeChanges) -> str:
        """
        Generate git commit message.

        Args:
            request: Original user request
            changes: Code changes

        Returns:
            Commit message
        """
        # Title line (max 50 chars)
        title = request.strip()
        if len(title) > 50:
            title = title[:47] + "..."

        # Body
        body_lines = [
            "",
            f"Generated by Context Workspace AI Agents",
            "",
            f"Files changed: {len(changes.files_affected)}",
        ]

        # List files
        for file_path in changes.files_affected[:10]:  # Limit to first 10
            body_lines.append(f"- {file_path}")

        if len(changes.files_affected) > 10:
            body_lines.append(f"- ... and {len(changes.files_affected) - 10} more")

        return title + "\n" + "\n".join(body_lines)

    async def _create_branch(self, branch_name: str) -> None:
        """
        Create git branch.

        Args:
            branch_name: Name of branch to create
        """
        try:
            # Create and checkout branch
            cmd = ["git", "checkout", "-b", branch_name]
            await self._run_git_command(cmd)
            self.log_info(f"Created branch: {branch_name}")

        except Exception as e:
            self.log_error(f"Failed to create branch: {e}", exc_info=True)
            raise

    async def _commit_changes(self, changes: CodeChanges, commit_message: str) -> None:
        """
        Commit code changes.

        Args:
            changes: Code changes to commit
            commit_message: Commit message
        """
        try:
            # Add all changed files
            for change in changes.changes:
                file_path = os.path.join(self.context.workspace_path, change.path)

                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Write file content
                with open(file_path, 'w') as f:
                    f.write(change.new_content)

                # Git add
                await self._run_git_command(["git", "add", change.path])

            # Commit
            await self._run_git_command(["git", "commit", "-m", commit_message])
            self.log_info("Committed changes")

        except Exception as e:
            self.log_error(f"Failed to commit changes: {e}", exc_info=True)
            raise

    async def _push_branch(self, branch_name: str) -> None:
        """
        Push branch to remote.

        Args:
            branch_name: Branch to push
        """
        try:
            # Push branch
            cmd = ["git", "push", "-u", "origin", branch_name]
            await self._run_git_command(cmd)
            self.log_info(f"Pushed branch: {branch_name}")

        except Exception as e:
            self.log_warning(f"Failed to push branch (may not have remote): {e}")

    async def _select_reviewers(self, changes: CodeChanges) -> List[str]:
        """
        Select reviewers based on CODEOWNERS file.

        Args:
            changes: Code changes

        Returns:
            List of reviewer usernames
        """
        reviewers = set()

        # Try to read CODEOWNERS file
        codeowners_path = os.path.join(self.context.workspace_path, "CODEOWNERS")
        if not os.path.exists(codeowners_path):
            codeowners_path = os.path.join(self.context.workspace_path, ".github", "CODEOWNERS")

        if os.path.exists(codeowners_path):
            try:
                with open(codeowners_path) as f:
                    content = f.read()

                # Parse CODEOWNERS
                for change in changes.changes:
                    file_path = change.path

                    # Find matching patterns
                    for line in content.split('\n'):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue

                        parts = line.split()
                        if len(parts) < 2:
                            continue

                        pattern = parts[0]
                        owners = parts[1:]

                        # Simple pattern matching
                        if self._matches_pattern(file_path, pattern):
                            for owner in owners:
                                # Remove @ prefix
                                if owner.startswith('@'):
                                    reviewers.add(owner[1:])

            except Exception as e:
                self.log_warning(f"Failed to parse CODEOWNERS: {e}")

        return list(reviewers)

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Simple pattern matching for CODEOWNERS"""
        # Convert glob pattern to regex
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        return bool(re.match(regex_pattern, file_path))

    async def _create_github_pr(
        self,
        title: str,
        description: str,
        branch: str,
        reviewers: List[str],
        base_branch: str = "main"
    ) -> tuple[Optional[str], Optional[int]]:
        """
        Create GitHub PR using API.

        Args:
            title: PR title
            description: PR description
            branch: Source branch
            reviewers: List of reviewer usernames
            base_branch: Target branch

        Returns:
            Tuple of (PR URL, PR number)
        """
        if not self.github_token:
            self.log_warning("No GitHub token found - cannot create PR via API")
            return None, None

        try:
            # Get repo info
            repo_info = await self._get_repo_info()
            if not repo_info:
                return None, None

            owner, repo_name = repo_info

            # Create PR using GitHub API
            import aiohttp
            import json

            url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            data = {
                "title": title,
                "body": description,
                "head": branch,
                "base": base_branch,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 201:
                        result = await response.json()
                        pr_url = result.get("html_url")
                        pr_number = result.get("number")

                        # Add reviewers if provided
                        if reviewers and pr_number:
                            await self._add_reviewers(owner, repo_name, pr_number, reviewers)

                        self.log_info(f"Created GitHub PR: {pr_url}")
                        return pr_url, pr_number
                    else:
                        error_text = await response.text()
                        self.log_error(f"Failed to create PR: {response.status} - {error_text}")
                        return None, None

        except ImportError:
            self.log_warning("aiohttp not installed - cannot create PR via API")
            return None, None

        except Exception as e:
            self.log_error(f"Failed to create GitHub PR: {e}", exc_info=True)
            return None, None

    async def _add_reviewers(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        reviewers: List[str]
    ) -> None:
        """Add reviewers to PR"""
        try:
            import aiohttp
            import json

            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            data = {"reviewers": reviewers}

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 201:
                        self.log_info(f"Added reviewers: {reviewers}")
                    else:
                        self.log_warning(f"Failed to add reviewers: {response.status}")

        except Exception as e:
            self.log_warning(f"Failed to add reviewers: {e}")

    async def _get_repo_info(self) -> Optional[tuple[str, str]]:
        """
        Get GitHub repo owner and name from git remote.

        Returns:
            Tuple of (owner, repo_name) or None
        """
        try:
            # Get remote URL
            result = await self._run_git_command(["git", "remote", "get-url", "origin"])
            remote_url = result.strip()

            # Parse GitHub URL
            # Examples:
            # - https://github.com/owner/repo.git
            # - git@github.com:owner/repo.git
            match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$', remote_url)
            if match:
                owner = match.group(1)
                repo_name = match.group(2)
                return owner, repo_name

        except Exception as e:
            self.log_warning(f"Failed to get repo info: {e}")

        return None

    async def _run_git_command(self, cmd: List[str]) -> str:
        """
        Run git command.

        Args:
            cmd: Command and arguments

        Returns:
            Command output
        """
        result = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.context.workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await result.communicate()

        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {stderr.decode()}")

        return stdout.decode()

    def _generate_labels(self, changes: CodeChanges, review: ReviewFeedback) -> List[str]:
        """Generate labels for PR"""
        labels = []

        # Add language label
        if changes.language:
            labels.append(changes.language.lower())

        # Add review status label
        if review.approved:
            labels.append("approved")
        else:
            labels.append("needs-review")

        # Add security label if issues found
        if review.security_score < 100:
            labels.append("security")

        # Add performance label if issues found
        if review.performance_score < 100:
            labels.append("performance")

        # Add automated label
        labels.append("automated")

        return labels
