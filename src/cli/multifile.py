"""
Multi-File Editing CLI Commands

Commands for multi-file editing and PR generation.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.main import ContextWorkspace, WorkflowBuilder
from src.multifile.editor import ChangeSet, ChangeType, FileChange

console = Console()


@click.group(name="edit")
def multifile_cli():
    """Multi-file editing and PR generation commands"""
    pass


@multifile_cli.command(name="apply")
@click.argument("changeset_file", type=click.Path(exists=True))
@click.option(
    "--workspace",
    "-w",
    default=".",
    help="Workspace root directory",
    type=click.Path(exists=True)
)
@click.option(
    "--no-validate",
    is_flag=True,
    help="Skip validation (syntax, type, lint checks)"
)
@click.option(
    "--create-pr",
    is_flag=True,
    help="Create pull request after applying changes"
)
@click.option(
    "--pr-title",
    help="Pull request title (auto-generated if not provided)"
)
@click.option(
    "--base-branch",
    default="main",
    help="Base branch for PR"
)
@click.option(
    "--draft",
    is_flag=True,
    help="Create as draft PR"
)
def apply_changeset(
    changeset_file: str,
    workspace: str,
    no_validate: bool,
    create_pr: bool,
    pr_title: Optional[str],
    base_branch: str,
    draft: bool,
):
    """
    Apply multi-file changeset from JSON file.

    CHANGESET_FILE format:
    {
        "description": "Add new feature",
        "author": "Developer Name",
        "changes": [
            {
                "file_path": "src/module.py",
                "change_type": "modify",
                "content": "# New content",
                "repository": "."
            }
        ]
    }
    """
    asyncio.run(_apply_changeset_async(
        changeset_file=changeset_file,
        workspace=workspace,
        no_validate=no_validate,
        create_pr=create_pr,
        pr_title=pr_title,
        base_branch=base_branch,
        draft=draft,
    ))


async def _apply_changeset_async(
    changeset_file: str,
    workspace: str,
    no_validate: bool,
    create_pr: bool,
    pr_title: Optional[str],
    base_branch: str,
    draft: bool,
):
    """Apply changeset asynchronously"""

    # Load changeset from file
    with open(changeset_file) as f:
        data = json.load(f)

    # Parse changes
    changes = []
    for change_data in data.get("changes", []):
        change = FileChange(
            file_path=change_data["file_path"],
            change_type=ChangeType(change_data.get("change_type", "modify")),
            content=change_data.get("content"),
            repository=change_data.get("repository", "."),
        )
        changes.append(change)

    # Create changeset
    changeset = ChangeSet(
        changes=changes,
        description=data.get("description", "Multi-file changes"),
        author=data.get("author", "Context AI"),
        branch_name=data.get("branch_name"),
    )

    console.print(Panel.fit(
        f"[bold cyan]Applying Changeset[/bold cyan]\n\n"
        f"Description: {changeset.description}\n"
        f"Changes: {len(changes)} file(s)\n"
        f"Repositories: {len(changeset.repositories)}",
        title="Multi-File Edit"
    ))

    # Initialize workspace
    workspace_obj = ContextWorkspace(
        workspace_root=workspace,
    )

    # Override validation settings if requested
    if no_validate:
        workspace_obj.editor.enable_syntax_check = False
        workspace_obj.editor.enable_type_check = False
        workspace_obj.editor.enable_lint = False

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Apply changes
            task1 = progress.add_task("Validating changes...", total=None)
            task2 = progress.add_task("Applying changes...", total=None)

            result = await workspace_obj.execute_workflow(
                changeset=changeset,
                create_pr=create_pr,
                pr_title=pr_title,
                base_branch=base_branch,
                draft_pr=draft,
            )

            progress.update(task1, completed=True)
            progress.update(task2, completed=True)

        # Display results
        if result.success:
            console.print("[bold green]✓[/bold green] Changes applied successfully!")

            # Show details
            table = Table(title="Changeset Details")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Changeset ID", result.changeset.id)
            table.add_row("Files Changed", str(len(result.changeset.changes)))
            table.add_row("Execution Time", f"{result.execution_time_ms:.2f}ms")

            if result.pull_requests:
                table.add_row("PRs Created", str(len(result.pull_requests)))
                for pr in result.pull_requests:
                    if pr.pr_url:
                        table.add_row(f"  PR ({pr.repository})", pr.pr_url)

            console.print(table)

        else:
            console.print(f"[bold red]✗[/bold red] Failed to apply changes")
            if result.error:
                console.print(f"[red]Error:[/red] {result.error}")

    finally:
        await workspace_obj.close()


@multifile_cli.command(name="create-pr")
@click.option(
    "--workspace",
    "-w",
    default=".",
    help="Workspace root directory",
    type=click.Path(exists=True)
)
@click.option(
    "--title",
    "-t",
    required=True,
    help="PR title"
)
@click.option(
    "--description",
    "-d",
    help="PR description"
)
@click.option(
    "--branch",
    "-b",
    help="Branch name (auto-generated if not provided)"
)
@click.option(
    "--base-branch",
    default="main",
    help="Base branch"
)
@click.option(
    "--draft",
    is_flag=True,
    help="Create as draft PR"
)
@click.argument("files", nargs=-1, type=click.Path(exists=True))
def create_pr(
    workspace: str,
    title: str,
    description: Optional[str],
    branch: Optional[str],
    base_branch: str,
    draft: bool,
    files: tuple,
):
    """
    Create PR from current uncommitted changes.

    FILES: List of files to include (all uncommitted if not specified)

    Example:
        context edit create-pr -t "Add feature" src/module.py tests/test_module.py
    """
    asyncio.run(_create_pr_async(
        workspace=workspace,
        title=title,
        description=description,
        branch=branch,
        base_branch=base_branch,
        draft=draft,
        files=files,
    ))


async def _create_pr_async(
    workspace: str,
    title: str,
    description: Optional[str],
    branch: Optional[str],
    base_branch: str,
    draft: bool,
    files: tuple,
):
    """Create PR asynchronously"""
    workspace_obj = ContextWorkspace(workspace_root=workspace)

    try:
        # Get file changes
        changes = []
        for file_path in files:
            path = Path(file_path)
            if path.exists():
                content = path.read_text()
                change = FileChange(
                    file_path=str(path),
                    change_type=ChangeType.MODIFY,
                    content=content,
                )
                changes.append(change)

        if not changes:
            console.print("[yellow]Warning:[/yellow] No files specified or found")
            return

        # Create changeset
        changeset = ChangeSet(
            changes=changes,
            description=description or title,
            branch_name=branch,
        )

        console.print(f"[cyan]Creating PR with {len(changes)} file(s)[/cyan]")

        # Generate PR
        result = await workspace_obj.execute_workflow(
            changeset=changeset,
            create_pr=True,
            pr_title=title,
            base_branch=base_branch,
            draft_pr=draft,
        )

        if result.success and result.pull_requests:
            console.print("[bold green]✓[/bold green] PR(s) created successfully!")
            for pr in result.pull_requests:
                console.print(f"[cyan]{pr.repository}:[/cyan] {pr.pr_url or pr.branch_name}")
        else:
            console.print("[bold red]✗[/bold red] Failed to create PR")
            if result.error:
                console.print(f"[red]Error:[/red] {result.error}")

    finally:
        await workspace_obj.close()


@multifile_cli.command(name="rollback")
@click.argument("changeset_id")
@click.option(
    "--workspace",
    "-w",
    default=".",
    help="Workspace root directory",
    type=click.Path(exists=True)
)
def rollback(changeset_id: str, workspace: str):
    """
    Rollback a changeset by ID.

    CHANGESET_ID: The ID of the changeset to rollback
    """
    asyncio.run(_rollback_async(changeset_id=changeset_id, workspace=workspace))


async def _rollback_async(changeset_id: str, workspace: str):
    """Rollback asynchronously"""
    workspace_obj = ContextWorkspace(workspace_root=workspace)

    try:
        console.print(f"[cyan]Rolling back changeset {changeset_id}...[/cyan]")

        success = await workspace_obj.rollback(changeset_id)

        if success:
            console.print("[bold green]✓[/bold green] Rollback successful!")
        else:
            console.print("[bold red]✗[/bold red] Rollback failed")
            console.print("[yellow]Changeset may not exist or backup not found[/yellow]")

    finally:
        await workspace_obj.close()


@multifile_cli.command(name="validate")
@click.argument("changeset_file", type=click.Path(exists=True))
@click.option(
    "--workspace",
    "-w",
    default=".",
    help="Workspace root directory",
    type=click.Path(exists=True)
)
def validate(changeset_file: str, workspace: str):
    """
    Validate changeset without applying changes.

    CHANGESET_FILE: JSON file with changeset definition
    """
    asyncio.run(_validate_async(changeset_file=changeset_file, workspace=workspace))


async def _validate_async(changeset_file: str, workspace: str):
    """Validate asynchronously"""

    # Load changeset
    with open(changeset_file) as f:
        data = json.load(f)

    changes = []
    for change_data in data.get("changes", []):
        change = FileChange(
            file_path=change_data["file_path"],
            change_type=ChangeType(change_data.get("change_type", "modify")),
            content=change_data.get("content"),
            repository=change_data.get("repository", "."),
        )
        changes.append(change)

    changeset = ChangeSet(
        changes=changes,
        description=data.get("description", ""),
        author=data.get("author", "Context AI"),
    )

    # Initialize editor
    workspace_obj = ContextWorkspace(workspace_root=workspace)
    editor = workspace_obj.editor

    try:
        console.print(f"[cyan]Validating {len(changes)} change(s)...[/cyan]")

        # Detect conflicts
        conflicts = await editor._detect_conflicts(changeset)

        # Validate changes
        validation_passed = await editor._validate_changes(changeset)

        # Display results
        if conflicts:
            console.print("\n[bold red]Conflicts Detected:[/bold red]")
            for conflict in conflicts:
                console.print(f"  • {conflict}")

        if not validation_passed:
            console.print("\n[bold red]Validation Failures:[/bold red]")
            for change in changeset.changes:
                if change.validation_errors:
                    console.print(f"\n[yellow]{change.file_path}:[/yellow]")
                    for error in change.validation_errors:
                        console.print(f"  • {error}")

        if not conflicts and validation_passed:
            console.print("[bold green]✓[/bold green] All validations passed!")

            # Show validation details
            table = Table(title="Validation Results")
            table.add_column("File", style="cyan")
            table.add_column("Syntax", style="white")
            table.add_column("Types", style="white")
            table.add_column("Lint", style="white")

            for change in changeset.changes:
                table.add_row(
                    change.file_path,
                    _status_icon(change.syntax_valid),
                    _status_icon(change.type_check_valid),
                    _status_icon(change.lint_valid),
                )

            console.print(table)

    finally:
        await workspace_obj.close()


def _status_icon(status) -> str:
    """Get status icon for validation result"""
    from src.multifile.editor import ValidationStatus

    if status == ValidationStatus.PASSED:
        return "[green]✓[/green]"
    elif status == ValidationStatus.FAILED:
        return "[red]✗[/red]"
    elif status == ValidationStatus.SKIPPED:
        return "[yellow]-[/yellow]"
    else:
        return "[dim]?[/dim]"


if __name__ == "__main__":
    multifile_cli()
