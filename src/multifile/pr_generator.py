"""
Pull Request Generator

Generates pull requests across multiple files and repositories with
GitHub API integration and PR template support.
"""

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import structlog

from .editor import ChangeSet, ChangeType

logger = structlog.get_logger(__name__)


@dataclass
class PullRequest:
    """Represents a pull request"""
    title: str
    body: str
    branch_name: str
    base_branch: str = "main"
    repository: str = "."

    # GitHub metadata
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    status: str = "draft"

    # Changes
    changeset: Optional[ChangeSet] = None
    files_changed: List[str] = field(default_factory=list)
    commits: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    author: str = "Context AI"
    reviewers: List[str] = field(default_factory=list)

    # Cross-repo linking
    related_prs: List['PullRequest'] = field(default_factory=list)


class PRGenerator:
    """
    Pull Request Generator

    Features:
    - Generate PRs from changesets
    - Cross-repository PR linking
    - PR template support
    - GitHub API integration
    - Automatic reviewer assignment
    """

    def __init__(
        self,
        workspace_root: str = ".",
        github_token: Optional[str] = None,
        pr_template_path: Optional[str] = None,
        auto_assign_reviewers: bool = True,
    ):
        """
        Initialize PRGenerator.

        Args:
            workspace_root: Root directory of workspace
            github_token: GitHub API token (from env if not provided)
            pr_template_path: Path to PR template file
            auto_assign_reviewers: Automatically assign reviewers from CODEOWNERS
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.pr_template_path = pr_template_path
        self.auto_assign_reviewers = auto_assign_reviewers

        self.logger = logger.bind(
            component="pr_generator",
            workspace=str(self.workspace_root)
        )

        # GitHub API client
        if self.github_token:
            self.github_client = httpx.AsyncClient(
                base_url="https://api.github.com",
                headers={
                    "Authorization": f"Bearer {self.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=30.0
            )
        else:
            self.github_client = None
            self.logger.warning(
                "GitHub token not provided, PR creation via API will be disabled"
            )

    async def generate_pr(
        self,
        changeset: ChangeSet,
        title: Optional[str] = None,
        base_branch: str = "main",
        draft: bool = False,
    ) -> List[PullRequest]:
        """
        Generate pull request(s) from changeset.

        For multi-repository changesets, creates one PR per repository
        and links them together.

        Args:
            changeset: ChangeSet with changes
            title: PR title (auto-generated if None)
            base_branch: Base branch for PR
            draft: Create as draft PR

        Returns:
            List of PullRequest objects (one per repository)
        """
        self.logger.info(
            "Generating PR",
            changeset_id=changeset.id,
            repositories=list(changeset.repositories)
        )

        prs: List[PullRequest] = []

        # Group changes by repository
        by_repo = changeset.get_files_by_repo()

        for repo, repo_changes in by_repo.items():
            pr = await self._generate_single_pr(
                repo=repo,
                changeset=changeset,
                changes=repo_changes,
                title=title,
                base_branch=base_branch,
                draft=draft
            )
            prs.append(pr)

        # Link related PRs
        if len(prs) > 1:
            self._link_related_prs(prs)

        return prs

    async def _generate_single_pr(
        self,
        repo: str,
        changeset: ChangeSet,
        changes: List,
        title: Optional[str],
        base_branch: str,
        draft: bool,
    ) -> PullRequest:
        """Generate a single PR for one repository"""

        # Generate branch name
        branch_name = changeset.branch_name or f"context-ai/{changeset.id}"

        # Generate PR title
        if not title:
            title = self._generate_title(changeset, changes)

        # Generate PR body
        body = await self._generate_body(changeset, changes)

        # Create PR object
        pr = PullRequest(
            title=title,
            body=body,
            branch_name=branch_name,
            base_branch=base_branch,
            repository=repo,
            changeset=changeset,
            files_changed=[c.file_path for c in changes],
            status="draft" if draft else "open",
        )

        # Assign reviewers
        if self.auto_assign_reviewers:
            pr.reviewers = await self._get_reviewers(repo, changes)

        # Create git branch and commit
        try:
            await self._create_git_branch(repo, branch_name, base_branch)
            commit_sha = await self._commit_changes(repo, changeset, changes)
            pr.commits.append(commit_sha)

            # Push to remote
            await self._push_branch(repo, branch_name)

            # Create PR via GitHub API
            if self.github_client:
                await self._create_github_pr(pr)

            self.logger.info(
                "PR generated successfully",
                repository=repo,
                branch=branch_name,
                pr_url=pr.pr_url
            )

        except Exception as e:
            self.logger.error(
                "Error generating PR",
                repository=repo,
                error=str(e)
            )
            raise

        return pr

    def _generate_title(self, changeset: ChangeSet, changes: List) -> str:
        """Generate PR title from changeset"""
        if changeset.description:
            return changeset.description

        # Auto-generate based on changes
        num_files = len(changes)
        change_types = {c.change_type for c in changes}

        if len(change_types) == 1:
            change_type = list(change_types)[0]
            if change_type == ChangeType.CREATE:
                return f"Add {num_files} new file(s)"
            elif change_type == ChangeType.MODIFY:
                return f"Update {num_files} file(s)"
            elif change_type == ChangeType.DELETE:
                return f"Remove {num_files} file(s)"
            elif change_type == ChangeType.RENAME:
                return f"Rename {num_files} file(s)"

        return f"Multi-file changes ({num_files} files)"

    async def _generate_body(self, changeset: ChangeSet, changes: List) -> str:
        """Generate PR body from template or default"""

        # Load template if provided
        template = None
        if self.pr_template_path:
            template_path = Path(self.pr_template_path)
            if template_path.exists():
                template = template_path.read_text()

        if not template:
            # Use default template
            template = self._get_default_template()

        # Populate template
        body = template.format(
            description=changeset.description or "Automated changes by Context AI",
            num_files=len(changes),
            files=self._format_file_list(changes),
            changeset_id=changeset.id,
            author=changeset.author,
            timestamp=changeset.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

        return body

    def _get_default_template(self) -> str:
        """Get default PR template"""
        return """## Summary
{description}

## Changes
This PR modifies **{num_files}** file(s):

{files}

## Details
- **Changeset ID:** `{changeset_id}`
- **Author:** {author}
- **Generated:** {timestamp}

## Testing
- [ ] All existing tests pass
- [ ] New tests added (if applicable)
- [ ] Manual testing completed

## Review Checklist
- [ ] Code follows project conventions
- [ ] No security vulnerabilities introduced
- [ ] Documentation updated (if needed)
- [ ] Breaking changes documented

---
*Generated automatically by Context AI*
"""

    def _format_file_list(self, changes: List) -> str:
        """Format list of changed files for PR body"""
        lines = []
        for change in changes:
            icon = {
                ChangeType.CREATE: "✨",
                ChangeType.MODIFY: "📝",
                ChangeType.DELETE: "🗑️",
                ChangeType.RENAME: "📋",
            }.get(change.change_type, "📄")

            line = f"- {icon} `{change.file_path}`"
            if change.change_type == ChangeType.RENAME and change.new_path:
                line += f" → `{change.new_path}`"

            lines.append(line)

        return "\n".join(lines)

    async def _get_reviewers(self, repo: str, changes: List) -> List[str]:
        """Get reviewers from CODEOWNERS file"""
        reviewers = []

        # Read CODEOWNERS file
        codeowners_paths = [
            self.workspace_root / repo / ".github" / "CODEOWNERS",
            self.workspace_root / repo / "CODEOWNERS",
        ]

        for path in codeowners_paths:
            if path.exists():
                content = path.read_text()
                reviewers = self._parse_codeowners(content, changes)
                break

        if not reviewers:
            self.logger.debug("No reviewers found in CODEOWNERS", repository=repo)

        return reviewers

    def _parse_codeowners(self, content: str, changes: List) -> List[str]:
        """Parse CODEOWNERS file and match files"""
        reviewers = set()

        # Simple parser for CODEOWNERS format
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            pattern = parts[0]
            owners = parts[1:]

            # Check if any changed file matches pattern
            for change in changes:
                if self._matches_pattern(change.file_path, pattern):
                    # Extract GitHub usernames (remove @ prefix)
                    for owner in owners:
                        if owner.startswith('@'):
                            reviewers.add(owner[1:])

        return list(reviewers)

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches CODEOWNERS pattern"""
        # Simple glob matching (could use fnmatch for more complex patterns)
        if pattern == "*":
            return True

        if pattern.startswith("*"):
            return file_path.endswith(pattern[1:])

        if pattern.endswith("*"):
            return file_path.startswith(pattern[:-1])

        return file_path == pattern

    async def _create_git_branch(self, repo: str, branch_name: str, base_branch: str):
        """Create git branch"""
        repo_path = self.workspace_root / repo

        # Ensure we're on base branch
        subprocess.run(
            ['git', 'checkout', base_branch],
            cwd=repo_path,
            check=True,
            capture_output=True
        )

        # Pull latest
        subprocess.run(
            ['git', 'pull'],
            cwd=repo_path,
            check=True,
            capture_output=True
        )

        # Create new branch
        subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            cwd=repo_path,
            check=True,
            capture_output=True
        )

        self.logger.info(
            "Created git branch",
            repository=repo,
            branch=branch_name
        )

    async def _commit_changes(
        self,
        repo: str,
        changeset: ChangeSet,
        changes: List
    ) -> str:
        """Commit changes to git"""
        repo_path = self.workspace_root / repo

        # Stage all changed files
        for change in changes:
            subprocess.run(
                ['git', 'add', change.file_path],
                cwd=repo_path,
                check=True,
                capture_output=True
            )

        # Create commit message
        commit_message = self._generate_commit_message(changeset, changes)

        # Commit
        result = subprocess.run(
            ['git', 'commit', '-m', commit_message],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True
        )

        # Get commit SHA
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True
        )
        commit_sha = result.stdout.strip()

        self.logger.info(
            "Committed changes",
            repository=repo,
            commit=commit_sha
        )

        return commit_sha

    def _generate_commit_message(self, changeset: ChangeSet, changes: List) -> str:
        """Generate commit message"""
        title = changeset.description or "Multi-file changes"

        # Add details
        details = [f"\nChangeset ID: {changeset.id}"]
        details.append(f"Files changed: {len(changes)}")

        for change in changes:
            icon = {
                ChangeType.CREATE: "Add",
                ChangeType.MODIFY: "Update",
                ChangeType.DELETE: "Remove",
                ChangeType.RENAME: "Rename",
            }.get(change.change_type, "Change")
            details.append(f"- {icon}: {change.file_path}")

        return title + "\n" + "\n".join(details)

    async def _push_branch(self, repo: str, branch_name: str):
        """Push branch to remote"""
        repo_path = self.workspace_root / repo

        subprocess.run(
            ['git', 'push', '-u', 'origin', branch_name],
            cwd=repo_path,
            check=True,
            capture_output=True
        )

        self.logger.info(
            "Pushed branch to remote",
            repository=repo,
            branch=branch_name
        )

    async def _create_github_pr(self, pr: PullRequest):
        """Create PR via GitHub API"""
        if not self.github_client:
            self.logger.warning("GitHub client not available, skipping PR creation")
            return

        # Get repository owner and name from git remote
        repo_path = self.workspace_root / pr.repository
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True
        )
        remote_url = result.stdout.strip()

        # Parse owner/repo from URL
        # Examples:
        # - https://github.com/owner/repo.git
        # - git@github.com:owner/repo.git
        if 'github.com' in remote_url:
            parts = remote_url.replace('.git', '').split('/')
            repo_name = parts[-1]
            owner = parts[-2].split(':')[-1]
        else:
            self.logger.error("Could not parse GitHub repository from remote URL")
            return

        # Create PR
        try:
            response = await self.github_client.post(
                f"/repos/{owner}/{repo_name}/pulls",
                json={
                    "title": pr.title,
                    "body": pr.body,
                    "head": pr.branch_name,
                    "base": pr.base_branch,
                    "draft": pr.status == "draft",
                }
            )

            if response.status_code == 201:
                data = response.json()
                pr.pr_number = data['number']
                pr.pr_url = data['html_url']

                # Assign reviewers
                if pr.reviewers:
                    await self._assign_reviewers(owner, repo_name, pr.pr_number, pr.reviewers)

                self.logger.info(
                    "Created GitHub PR",
                    repository=pr.repository,
                    pr_number=pr.pr_number,
                    pr_url=pr.pr_url
                )
            else:
                self.logger.error(
                    "Failed to create GitHub PR",
                    status=response.status_code,
                    response=response.text
                )

        except Exception as e:
            self.logger.error(
                "Error creating GitHub PR",
                error=str(e)
            )

    async def _assign_reviewers(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        reviewers: List[str]
    ):
        """Assign reviewers to PR"""
        try:
            response = await self.github_client.post(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers",
                json={"reviewers": reviewers}
            )

            if response.status_code == 201:
                self.logger.info(
                    "Assigned reviewers",
                    pr_number=pr_number,
                    reviewers=reviewers
                )
            else:
                self.logger.warning(
                    "Failed to assign reviewers",
                    status=response.status_code
                )

        except Exception as e:
            self.logger.warning(
                "Error assigning reviewers",
                error=str(e)
            )

    def _link_related_prs(self, prs: List[PullRequest]):
        """Link related PRs in their descriptions"""
        for pr in prs:
            pr.related_prs = [p for p in prs if p != pr]

            # Add links to PR body
            if pr.related_prs:
                links = "\n\n## Related PRs\n"
                for related_pr in pr.related_prs:
                    if related_pr.pr_url:
                        links += f"- {related_pr.repository}: {related_pr.pr_url}\n"
                    else:
                        links += f"- {related_pr.repository}: {related_pr.branch_name}\n"

                pr.body += links

    async def close(self):
        """Close GitHub API client"""
        if self.github_client:
            await self.github_client.aclose()
