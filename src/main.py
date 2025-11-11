"""
Context Workspace v3.0 - Main Integration Module

Wires all components together:
- Prompt Enhancement → Memory → Agents → Multi-file Editing
- End-to-end workflow orchestration
- Error handling and logging
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from src.config.settings import Settings
from src.multifile.editor import ChangeSet, FileChange, MultiFileEditor
from src.multifile.pr_generator import PRGenerator, PullRequest

logger = structlog.get_logger(__name__)


@dataclass
class WorkflowResult:
    """Result of complete v3.0 workflow"""
    success: bool
    changeset: Optional[ChangeSet] = None
    pull_requests: List[PullRequest] = None
    execution_time_ms: float = 0.0
    error: Optional[str] = None

    # Stage results
    prompt_enhanced: bool = False
    memory_retrieved: bool = False
    changes_applied: bool = False
    prs_created: bool = False

    # Metadata
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.pull_requests is None:
            self.pull_requests = []


class ContextWorkspace:
    """
    Main Context Workspace v3.0 Integration Class

    Provides unified interface to all v3.0 components:
    - Multi-file editing
    - PR generation
    - (Future) Prompt enhancement
    - (Future) Memory system
    - (Future) Autonomous agents
    """

    def __init__(
        self,
        workspace_root: str = ".",
        config: Optional[Settings] = None,
    ):
        """
        Initialize Context Workspace.

        Args:
            workspace_root: Root directory of workspace
            config: Settings object (loads from env if None)
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.config = config or Settings()

        self.logger = logger.bind(
            component="context_workspace",
            workspace=str(self.workspace_root)
        )

        # Initialize components
        self.editor = MultiFileEditor(
            workspace_root=str(self.workspace_root),
            enable_syntax_check=True,
            enable_type_check=True,
            enable_lint=True,
        )

        self.pr_generator = PRGenerator(
            workspace_root=str(self.workspace_root),
            auto_assign_reviewers=True,
        )

        self.logger.info(
            "Context Workspace initialized",
            version="3.0.0",
            workspace=str(self.workspace_root)
        )

    async def execute_workflow(
        self,
        changeset: ChangeSet,
        create_pr: bool = True,
        pr_title: Optional[str] = None,
        base_branch: str = "main",
        draft_pr: bool = False,
    ) -> WorkflowResult:
        """
        Execute complete v3.0 workflow.

        Workflow:
        1. (Future) Enhance prompt with context
        2. (Future) Query memory for patterns/solutions
        3. (Future) Generate code with agents
        4. Apply multi-file changes
        5. Generate pull request(s)

        Args:
            changeset: ChangeSet with file changes
            create_pr: Whether to create PR after applying changes
            pr_title: PR title (auto-generated if None)
            base_branch: Base branch for PR
            draft_pr: Create as draft PR

        Returns:
            WorkflowResult with execution details
        """
        start_time = datetime.utcnow()

        self.logger.info(
            "Starting v3.0 workflow",
            changeset_id=changeset.id,
            num_changes=len(changeset.changes),
            create_pr=create_pr
        )

        result = WorkflowResult(success=False)

        try:
            # Stage 1: (Future) Prompt Enhancement
            # For now, skip - will be implemented in future PRs
            result.prompt_enhanced = True

            # Stage 2: (Future) Memory Retrieval
            # For now, skip - will be implemented in future PRs
            result.memory_retrieved = True

            # Stage 3: Apply Changes
            self.logger.info("Applying multi-file changes")
            changes_success, updated_changeset = await self.editor.edit_files(changeset)

            if not changes_success:
                error_msg = "Failed to apply changes"
                if updated_changeset.changes:
                    errors = []
                    for change in updated_changeset.changes:
                        if change.validation_errors:
                            errors.extend(change.validation_errors)
                    if errors:
                        error_msg += f": {', '.join(errors)}"

                result.error = error_msg
                self.logger.error(error_msg, changeset_id=changeset.id)
                return result

            result.changes_applied = True
            result.changeset = updated_changeset

            # Stage 4: Generate PR
            if create_pr:
                self.logger.info("Generating pull request(s)")
                try:
                    prs = await self.pr_generator.generate_pr(
                        changeset=updated_changeset,
                        title=pr_title,
                        base_branch=base_branch,
                        draft=draft_pr,
                    )

                    result.pull_requests = prs
                    result.prs_created = True

                    self.logger.info(
                        "PRs created successfully",
                        num_prs=len(prs),
                        pr_urls=[pr.pr_url for pr in prs if pr.pr_url]
                    )

                except Exception as e:
                    self.logger.error(
                        "Failed to generate PR",
                        error=str(e),
                        changeset_id=changeset.id
                    )
                    # Continue even if PR generation fails
                    result.error = f"PR generation failed: {str(e)}"

            # Success!
            result.success = True

            # Calculate execution time
            end_time = datetime.utcnow()
            result.execution_time_ms = (end_time - start_time).total_seconds() * 1000

            self.logger.info(
                "Workflow completed successfully",
                changeset_id=changeset.id,
                execution_time_ms=result.execution_time_ms,
                prs_created=len(result.pull_requests)
            )

            return result

        except Exception as e:
            self.logger.error(
                "Workflow failed with unexpected error",
                error=str(e),
                changeset_id=changeset.id
            )
            result.error = f"Unexpected error: {str(e)}"
            return result

    async def rollback(self, changeset_id: str) -> bool:
        """
        Rollback a changeset by ID.

        Args:
            changeset_id: ID of changeset to rollback

        Returns:
            True if rollback successful
        """
        self.logger.info("Rolling back changeset", changeset_id=changeset_id)

        try:
            success = await self.editor.rollback(changeset_id)

            if success:
                self.logger.info("Rollback successful", changeset_id=changeset_id)
            else:
                self.logger.error("Rollback failed", changeset_id=changeset_id)

            return success

        except Exception as e:
            self.logger.error(
                "Rollback error",
                changeset_id=changeset_id,
                error=str(e)
            )
            return False

    async def close(self):
        """Cleanup resources"""
        await self.pr_generator.close()
        self.logger.info("Context Workspace closed")


class WorkflowBuilder:
    """
    Fluent builder for creating and executing workflows.

    Example:
        result = await (
            WorkflowBuilder(workspace)
            .add_file_change("src/file.py", content="...")
            .with_pr_title("Add feature")
            .with_draft_pr(True)
            .execute()
        )
    """

    def __init__(self, workspace: ContextWorkspace):
        self.workspace = workspace
        self._changes: List[FileChange] = []
        self._description: str = ""
        self._author: str = "Context AI"
        self._branch_name: Optional[str] = None
        self._create_pr: bool = True
        self._pr_title: Optional[str] = None
        self._base_branch: str = "main"
        self._draft_pr: bool = False

    def add_file_change(
        self,
        file_path: str,
        content: str,
        change_type=None,
        repository: str = ".",
    ) -> 'WorkflowBuilder':
        """Add a file change to the workflow"""
        from src.multifile.editor import ChangeType

        if change_type is None:
            # Auto-detect change type
            full_path = self.workspace.workspace_root / repository / file_path
            change_type = ChangeType.MODIFY if full_path.exists() else ChangeType.CREATE

        change = FileChange(
            file_path=file_path,
            change_type=change_type,
            content=content,
            repository=repository,
        )
        self._changes.append(change)
        return self

    def add_changes(self, changes: List[FileChange]) -> 'WorkflowBuilder':
        """Add multiple file changes"""
        self._changes.extend(changes)
        return self

    def with_description(self, description: str) -> 'WorkflowBuilder':
        """Set changeset description"""
        self._description = description
        return self

    def with_author(self, author: str) -> 'WorkflowBuilder':
        """Set author name"""
        self._author = author
        return self

    def with_branch_name(self, branch_name: str) -> 'WorkflowBuilder':
        """Set git branch name"""
        self._branch_name = branch_name
        return self

    def with_pr_title(self, title: str) -> 'WorkflowBuilder':
        """Set PR title"""
        self._pr_title = title
        return self

    def with_base_branch(self, base_branch: str) -> 'WorkflowBuilder':
        """Set base branch for PR"""
        self._base_branch = base_branch
        return self

    def with_draft_pr(self, draft: bool = True) -> 'WorkflowBuilder':
        """Create as draft PR"""
        self._draft_pr = draft
        return self

    def skip_pr(self) -> 'WorkflowBuilder':
        """Skip PR creation"""
        self._create_pr = False
        return self

    async def execute(self) -> WorkflowResult:
        """Execute the workflow"""
        if not self._changes:
            raise ValueError("No changes to apply")

        changeset = ChangeSet(
            changes=self._changes,
            description=self._description,
            author=self._author,
            branch_name=self._branch_name,
        )

        return await self.workspace.execute_workflow(
            changeset=changeset,
            create_pr=self._create_pr,
            pr_title=self._pr_title,
            base_branch=self._base_branch,
            draft_pr=self._draft_pr,
        )


# Convenience functions for CLI/API usage

async def quick_edit(
    workspace_root: str,
    file_changes: Dict[str, str],
    description: str = "Multi-file changes",
    create_pr: bool = False,
) -> WorkflowResult:
    """
    Quick multi-file edit without full workflow setup.

    Args:
        workspace_root: Workspace root directory
        file_changes: Dict mapping file_path to new content
        description: Description of changes
        create_pr: Whether to create PR

    Returns:
        WorkflowResult

    Example:
        result = await quick_edit(
            workspace_root="/path/to/project",
            file_changes={
                "src/main.py": "# New content",
                "tests/test_main.py": "# Test content",
            },
            description="Add feature",
            create_pr=True
        )
    """
    workspace = ContextWorkspace(workspace_root=workspace_root)

    try:
        builder = WorkflowBuilder(workspace).with_description(description)

        for file_path, content in file_changes.items():
            builder.add_file_change(file_path, content)

        if not create_pr:
            builder.skip_pr()

        return await builder.execute()

    finally:
        await workspace.close()


async def create_pr_from_changes(
    workspace_root: str,
    file_changes: Dict[str, str],
    pr_title: str,
    base_branch: str = "main",
    draft: bool = False,
) -> WorkflowResult:
    """
    Create PR from file changes.

    Args:
        workspace_root: Workspace root directory
        file_changes: Dict mapping file_path to new content
        pr_title: PR title
        base_branch: Base branch
        draft: Create as draft

    Returns:
        WorkflowResult with PR details

    Example:
        result = await create_pr_from_changes(
            workspace_root="/path/to/project",
            file_changes={"src/main.py": "# New content"},
            pr_title="Add feature",
            base_branch="develop",
            draft=True
        )
    """
    workspace = ContextWorkspace(workspace_root=workspace_root)

    try:
        builder = (
            WorkflowBuilder(workspace)
            .with_pr_title(pr_title)
            .with_base_branch(base_branch)
            .with_draft_pr(draft)
        )

        for file_path, content in file_changes.items():
            builder.add_file_change(file_path, content)

        return await builder.execute()

    finally:
        await workspace.close()


# Main entry point for testing
async def main():
    """Main entry point for testing"""
    logging.basicConfig(level=logging.INFO)

    # Example workflow
    workspace = ContextWorkspace(workspace_root=".")

    try:
        result = await (
            WorkflowBuilder(workspace)
            .add_file_change(
                "example.py",
                content='print("Hello from Context v3.0!")\n',
            )
            .with_description("Add example file")
            .with_pr_title("Add example file")
            .with_draft_pr(True)
            .execute()
        )

        print(f"Workflow completed: {result.success}")
        print(f"Execution time: {result.execution_time_ms:.2f}ms")

        if result.pull_requests:
            print(f"PRs created: {len(result.pull_requests)}")
            for pr in result.pull_requests:
                print(f"  - {pr.pr_url or pr.branch_name}")

    finally:
        await workspace.close()


if __name__ == "__main__":
    asyncio.run(main())
