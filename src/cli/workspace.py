"""
Workspace Management CLI Commands

Provides CLI commands for managing multi-project workspaces with Click.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from src.workspace.config import WorkspaceConfig, ProjectConfig, IndexingConfig
from src.workspace.manager import WorkspaceManager


console = Console()


def handle_async(coro):
    """Helper to run async functions in sync Click commands"""
    return asyncio.run(coro)


def success(message: str) -> None:
    """Print success message"""
    console.print(f"[green]✓[/green] {message}")


def error(message: str, exit_code: int = 1) -> None:
    """Print error message and exit"""
    console.print(f"[red]✗[/red] {message}", style="red")
    sys.exit(exit_code)


def warning(message: str) -> None:
    """Print warning message"""
    console.print(f"[yellow]⚠[/yellow] {message}", style="yellow")


@click.group(name="workspace")
def workspace_cli():
    """Manage multi-project workspaces"""
    pass


@workspace_cli.command(name="init")
@click.option("--name", required=True, help="Workspace name")
@click.option("--output", default=".context-workspace.json", help="Output file path")
def init(name: str, output: str) -> None:
    """Initialize a new workspace configuration file"""
    try:
        output_path = Path(output)

        # Check if file already exists
        if output_path.exists():
            if not click.confirm(f"File {output} already exists. Overwrite?"):
                error("Aborted", exit_code=0)

        # Create minimal workspace config
        config = WorkspaceConfig(
            version="2.0.0",
            name=name,
            projects=[],
            relationships=[],
        )

        # Save to file
        config.save(output_path)

        success(f"Created workspace configuration: {output_path.absolute()}")
        console.print(f"\nNext steps:")
        console.print(f"  1. Add projects: [cyan]context workspace add-project[/cyan]")
        console.print(f"  2. Index projects: [cyan]context workspace index[/cyan]")
        console.print(f"  3. Search workspace: [cyan]context workspace search 'query'[/cyan]")

    except Exception as e:
        error(f"Failed to initialize workspace: {e}")


@workspace_cli.command(name="add-project")
@click.option("--id", "project_id", required=True, help="Unique project identifier")
@click.option("--name", required=True, help="Human-readable project name")
@click.option("--path", required=True, help="Path to project directory (absolute or relative)")
@click.option("--type", "project_type", default="application", help="Project type (e.g., web_frontend, api_server, library)")
@click.option("--language", multiple=True, help="Programming languages (can be specified multiple times)")
@click.option("--depends-on", help="Comma-separated list of project IDs this project depends on")
@click.option("--exclude", multiple=True, help="Patterns to exclude from indexing (can be specified multiple times)")
@click.option("--priority", type=click.Choice(["critical", "high", "medium", "low"]), default="medium", help="Indexing priority")
@click.option("--workspace", default=".context-workspace.json", help="Path to workspace config file")
def add_project(
    project_id: str,
    name: str,
    path: str,
    project_type: str,
    language: tuple,
    depends_on: Optional[str],
    exclude: tuple,
    priority: str,
    workspace: str,
) -> None:
    """Add a new project to the workspace"""
    try:
        workspace_path = Path(workspace)

        # Check if workspace exists
        if not workspace_path.exists():
            error(f"Workspace configuration not found: {workspace_path}\nRun 'context workspace init' first.")

        # Load existing config
        config = WorkspaceConfig.load(workspace_path, validate_paths=False)

        # Check if project ID already exists
        if config.get_project(project_id):
            error(f"Project with ID '{project_id}' already exists in workspace")

        # Parse dependencies
        dependencies = []
        if depends_on:
            dependencies = [d.strip() for d in depends_on.split(",") if d.strip()]

        # Create indexing config
        indexing_config = IndexingConfig(
            enabled=True,
            priority=priority,
            exclude=list(exclude) if exclude else [],
        )

        # Create project config
        project_config = ProjectConfig(
            id=project_id,
            name=name,
            path=path,
            type=project_type,
            language=list(language) if language else [],
            dependencies=dependencies,
            indexing=indexing_config,
        )

        # Add project to workspace config
        config.projects.append(project_config)

        # Validate the updated config
        config.resolve_paths(workspace_path.parent)
        config.validate(check_paths=True)

        # Save updated config
        config.save(workspace_path)

        success(f"Added project '{project_id}' to workspace")

        # Show project info
        table = Table(title=f"Project: {name}", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("ID", project_id)
        table.add_row("Name", name)
        table.add_row("Path", path)
        table.add_row("Type", project_type)
        table.add_row("Languages", ", ".join(language) if language else "N/A")
        table.add_row("Dependencies", ", ".join(dependencies) if dependencies else "None")
        table.add_row("Priority", priority)

        console.print(table)
        console.print(f"\n[dim]Run 'context workspace index --project {project_id}' to index this project[/dim]")

    except Exception as e:
        error(f"Failed to add project: {e}")


@workspace_cli.command(name="list")
@click.option("--workspace", default=".context-workspace.json", help="Path to workspace config file")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option("--json-output", "--json", is_flag=True, help="Output as JSON")
def list_projects(workspace: str, verbose: bool, json_output: bool) -> None:
    """List all projects in the workspace"""
    try:
        workspace_path = Path(workspace)

        # Check if workspace exists
        if not workspace_path.exists():
            error(f"Workspace configuration not found: {workspace_path}\nRun 'context workspace init' first.")

        # Load config
        config = WorkspaceConfig.load(workspace_path, validate_paths=False)

        if json_output:
            # JSON output
            output = {
                "workspace": config.name,
                "projects": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "path": p.path,
                        "type": p.type,
                        "languages": p.language,
                        "dependencies": p.dependencies,
                        "indexing_enabled": p.indexing.enabled,
                        "priority": p.indexing.priority,
                    }
                    for p in config.projects
                ],
            }
            print(json.dumps(output, indent=2))
            return

        # Rich output
        console.print(Panel(
            f"[bold]{config.name}[/bold]\n"
            f"Version: {config.version}\n"
            f"Projects: {len(config.projects)}",
            title="Workspace",
            border_style="blue"
        ))

        if not config.projects:
            warning("No projects in workspace. Add projects with 'context workspace add-project'")
            return

        # Create table
        table = Table(title="Projects", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Type", style="magenta")

        if verbose:
            table.add_column("Path", style="dim")
            table.add_column("Languages", style="yellow")
            table.add_column("Dependencies", style="blue")
            table.add_column("Priority", style="green")

        for project in config.projects:
            row = [
                project.id,
                project.name,
                project.type,
            ]

            if verbose:
                row.extend([
                    project.path,
                    ", ".join(project.language) if project.language else "—",
                    ", ".join(project.dependencies) if project.dependencies else "—",
                    project.indexing.priority,
                ])

            table.add_row(*row)

        console.print(table)

        # Show relationship summary if verbose
        if verbose and config.relationships:
            console.print(f"\n[bold]Relationships:[/bold] {len(config.relationships)}")
            for rel in config.relationships:
                console.print(f"  • {rel.from_project} → {rel.to_project} ({rel.type})")

    except Exception as e:
        error(f"Failed to list projects: {e}")


@workspace_cli.command(name="index")
@click.option("--workspace", default=".context-workspace.json", help="Path to workspace config file")
@click.option("--project", help="Index specific project by ID (default: all projects)")
@click.option("--parallel/--no-parallel", default=True, help="Index projects in parallel")
@click.option("--force", is_flag=True, help="Force re-indexing even if already indexed")
def index(workspace: str, project: Optional[str], parallel: bool, force: bool) -> None:
    """Index workspace projects"""
    async def _index():
        try:
            workspace_path = Path(workspace)

            # Check if workspace exists
            if not workspace_path.exists():
                error(f"Workspace configuration not found: {workspace_path}")

            # Initialize workspace manager
            manager = WorkspaceManager(str(workspace_path))

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                # Initialize workspace
                init_task = progress.add_task("Initializing workspace...", total=None)
                success_init = await manager.initialize()
                progress.update(init_task, completed=True)

                if not success_init:
                    error("Failed to initialize workspace")

                if project:
                    # Index specific project
                    if project not in manager.projects:
                        error(f"Project '{project}' not found in workspace")

                    index_task = progress.add_task(f"Indexing project '{project}'...", total=None)
                    success_idx = await manager.reload_project(project)
                    progress.update(index_task, completed=True)

                    if success_idx:
                        proj = manager.get_project(project)
                        stats = proj.stats
                        success(
                            f"Indexed project '{project}': "
                            f"{stats.files_indexed}/{stats.total_files} files "
                            f"({stats.errors} errors) "
                            f"in {stats.indexing_duration_seconds:.2f}s"
                        )
                    else:
                        error(f"Failed to index project '{project}'")
                else:
                    # Index all projects
                    index_task = progress.add_task(
                        f"Indexing {len(manager.projects)} projects...",
                        total=len(manager.projects)
                    )

                    results = await manager.index_all_projects(parallel=parallel)
                    progress.update(index_task, completed=len(manager.projects))

                    success_count = sum(1 for v in results.values() if v)
                    failed_count = len(results) - success_count

                    if failed_count == 0:
                        success(f"Indexed all {success_count} projects successfully")
                    else:
                        warning(f"Indexed {success_count}/{len(results)} projects ({failed_count} failed)")

                    # Show stats table
                    table = Table(title="Indexing Results", show_header=True, header_style="bold cyan")
                    table.add_column("Project", style="cyan")
                    table.add_column("Status", style="white")
                    table.add_column("Files", style="yellow", justify="right")
                    table.add_column("Errors", style="red", justify="right")
                    table.add_column("Duration", style="green", justify="right")

                    for project_id, result in results.items():
                        proj = manager.get_project(project_id)
                        stats = proj.stats
                        status = "✓ Success" if result else "✗ Failed"
                        status_style = "green" if result else "red"

                        table.add_row(
                            project_id,
                            f"[{status_style}]{status}[/{status_style}]",
                            f"{stats.files_indexed}/{stats.total_files}",
                            str(stats.errors),
                            f"{stats.indexing_duration_seconds:.2f}s" if stats.indexing_duration_seconds else "—",
                        )

                    console.print(table)

        except Exception as e:
            error(f"Failed to index: {e}")

    handle_async(_index())


@workspace_cli.command(name="search")
@click.argument("query")
@click.option("--workspace", default=".context-workspace.json", help="Path to workspace config file")
@click.option("--project", help="Search specific project by ID")
@click.option("--scope", type=click.Choice(["project", "dependencies", "workspace", "related"]), help="Search scope")
@click.option("--limit", type=int, default=10, help="Maximum number of results")
@click.option("--json-output", "--json", is_flag=True, help="Output as JSON")
def search(query: str, workspace: str, project: Optional[str], scope: Optional[str], limit: int, json_output: bool) -> None:
    """Search across workspace projects"""
    async def _search():
        try:
            workspace_path = Path(workspace)

            # Check if workspace exists
            if not workspace_path.exists():
                error(f"Workspace configuration not found: {workspace_path}")

            # Initialize workspace manager
            manager = WorkspaceManager(str(workspace_path))
            await manager.initialize()

            # Determine which projects to search
            project_ids = None
            if project:
                if project not in manager.projects:
                    error(f"Project '{project}' not found in workspace")
                project_ids = [project]
            elif scope == "project":
                error("--scope=project requires --project option")

            # Perform search
            results = await manager.search_workspace(
                query=query,
                project_ids=project_ids,
                limit=limit,
                score_threshold=0.0,
                use_relationship_boost=True,
            )

            if json_output:
                # JSON output
                output = {
                    "query": query,
                    "results": results,
                }
                print(json.dumps(output, indent=2, default=str))
                return

            # Rich output
            if not results:
                warning(f"No results found for query: '{query}'")
                return

            console.print(Panel(
                f"[bold]Query:[/bold] {query}\n"
                f"[bold]Results:[/bold] {len(results)}",
                title="Search Results",
                border_style="blue"
            ))

            for idx, result in enumerate(results, 1):
                project_id = result.get("project_id", "unknown")
                file_path = result.get("file_path", "unknown")
                score = result.get("score", 0.0)
                content = result.get("content", "")

                console.print(f"\n[bold cyan]{idx}.[/bold cyan] {file_path}")
                console.print(f"   [dim]Project: {project_id} | Score: {score:.3f}[/dim]")

                # Show content snippet
                if content:
                    snippet = content[:200] + "..." if len(content) > 200 else content
                    console.print(f"   {snippet}")

        except Exception as e:
            error(f"Failed to search: {e}")

    handle_async(_search())


@workspace_cli.command(name="status")
@click.option("--workspace", default=".context-workspace.json", help="Path to workspace config file")
@click.option("--project", help="Show status for specific project")
@click.option("--json-output", "--json", is_flag=True, help="Output as JSON")
def status(workspace: str, project: Optional[str], json_output: bool) -> None:
    """Get workspace or project status"""
    async def _status():
        try:
            workspace_path = Path(workspace)

            # Check if workspace exists
            if not workspace_path.exists():
                error(f"Workspace configuration not found: {workspace_path}")

            # Initialize workspace manager
            manager = WorkspaceManager(str(workspace_path))
            await manager.initialize()

            # Get status
            if project:
                # Project-specific status
                if project not in manager.projects:
                    error(f"Project '{project}' not found in workspace")

                proj = manager.get_project(project)
                status_data = await proj.get_status()

                if json_output:
                    print(json.dumps(status_data, indent=2, default=str))
                    return

                # Rich output
                console.print(Panel(
                    f"[bold]{status_data['name']}[/bold]\n"
                    f"ID: {status_data['id']}\n"
                    f"Type: {status_data['type']}\n"
                    f"Status: {status_data['status']}\n"
                    f"Path: {status_data['path']}",
                    title="Project Status",
                    border_style="blue"
                ))

                # Indexing stats
                idx = status_data['indexing']
                table = Table(title="Indexing Statistics", show_header=False)
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="white")

                table.add_row("Enabled", "Yes" if idx['enabled'] else "No")
                table.add_row("Priority", idx['priority'])
                table.add_row("Files Indexed", f"{idx['files_indexed']}/{idx['total_files']}")
                table.add_row("Errors", str(idx['errors']))
                table.add_row("Last Indexed", idx['last_indexed'] or "Never")
                table.add_row("Duration", f"{idx['duration_seconds']:.2f}s" if idx['duration_seconds'] else "—")

                console.print(table)
            else:
                # Workspace-wide status
                status_data = await manager.get_workspace_status()

                if json_output:
                    print(json.dumps(status_data, indent=2, default=str))
                    return

                # Rich output
                ws = status_data['workspace']
                console.print(Panel(
                    f"[bold]{ws['name']}[/bold]\n"
                    f"Version: {ws['version']}\n"
                    f"Config: {ws['config_path']}\n"
                    f"Projects: {len(status_data['projects'])}",
                    title="Workspace Status",
                    border_style="blue"
                ))

                # Projects table
                table = Table(title="Projects", show_header=True, header_style="bold cyan")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="white")
                table.add_column("Status", style="white")
                table.add_column("Files", style="yellow", justify="right")
                table.add_column("Errors", style="red", justify="right")

                for proj_id, proj_data in status_data['projects'].items():
                    idx = proj_data['indexing']
                    status_emoji = {
                        "ready": "✓",
                        "pending": "⏳",
                        "indexing": "🔄",
                        "failed": "✗",
                        "stopped": "⏸",
                    }.get(proj_data['status'], "?")

                    table.add_row(
                        proj_id,
                        proj_data['name'],
                        f"{status_emoji} {proj_data['status']}",
                        f"{idx['files_indexed']}/{idx['total_files']}",
                        str(idx['errors']),
                    )

                console.print(table)

        except Exception as e:
            error(f"Failed to get status: {e}")

    handle_async(_status())


@workspace_cli.command(name="validate")
@click.option("--file", "workspace_file", default=".context-workspace.json", help="Path to workspace config file")
def validate(workspace_file: str) -> None:
    """Validate workspace configuration"""
    try:
        workspace_path = Path(workspace_file)

        # Check if workspace exists
        if not workspace_path.exists():
            error(f"Workspace configuration not found: {workspace_path}")

        console.print(f"Validating workspace configuration: {workspace_path}")

        # Load and validate config
        config = WorkspaceConfig.load(workspace_path, validate_paths=True)

        # Additional validations
        errors = []
        warnings = []

        # Check for cycles in dependencies
        try:
            config._detect_circular_dependencies()
        except ValueError as e:
            errors.append(str(e))

        # Check if project paths exist
        path_errors = config.validate_paths()
        errors.extend(path_errors)

        # Check for unused projects (no dependencies, not depended upon)
        for project in config.projects:
            is_dependency = any(
                project.id in p.dependencies
                for p in config.projects
            )
            has_dependencies = len(project.dependencies) > 0

            if not is_dependency and not has_dependencies and len(config.projects) > 1:
                warnings.append(
                    f"Project '{project.id}' has no dependencies and is not depended upon"
                )

        # Display results
        if errors:
            console.print("\n[bold red]Validation Errors:[/bold red]")
            for err in errors:
                console.print(f"  ✗ {err}", style="red")
            error(f"\n{len(errors)} validation error(s) found", exit_code=1)

        if warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warn in warnings:
                console.print(f"  ⚠ {warn}", style="yellow")

        # Success
        success(f"Workspace configuration is valid")

        # Show summary
        table = Table(title="Workspace Summary", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Name", config.name)
        table.add_row("Version", config.version)
        table.add_row("Projects", str(len(config.projects)))
        table.add_row("Relationships", str(len(config.relationships)))

        console.print("\n")
        console.print(table)

    except Exception as e:
        error(f"Validation failed: {e}")


@workspace_cli.command(name="discover")
@click.argument("path", required=False, default=".")
@click.option("--workspace", default=".context-workspace.json", help="Path to workspace config file")
@click.option("--max-depth", type=int, default=10, help="Maximum directory depth to scan")
@click.option("--name", help="Workspace name (auto-generated if not provided)")
@click.option("--interactive/--no-interactive", default=True, help="Interactive confirmation")
@click.option("--json-output", "--json", is_flag=True, help="Output as JSON")
def discover(
    path: str,
    workspace: str,
    max_depth: int,
    name: Optional[str],
    interactive: bool,
    json_output: bool,
) -> None:
    """Auto-discover projects in directory and generate workspace configuration"""
    try:
        from src.workspace.auto_discovery import (
            ProjectScanner,
            TypeClassifier,
            DependencyAnalyzer,
            ConfigGenerator,
        )

        search_path = Path(path).resolve()
        workspace_path = Path(workspace)

        # Validate path
        if not search_path.exists():
            error(f"Path does not exist: {path}")
        if not search_path.is_dir():
            error(f"Path is not a directory: {path}")

        # Check if workspace file already exists
        if workspace_path.exists() and not json_output:
            if not click.confirm(
                f"Workspace configuration already exists at {workspace}. Overwrite?"
            ):
                error("Aborted", exit_code=0)

        console.print(f"\n[bold blue]🔍 Scanning {search_path} for projects...[/bold blue]\n")

        # Step 1: Scan for projects
        with console.status("[bold green]Scanning directories..."):
            scanner = ProjectScanner(max_depth=max_depth)
            discovered = scanner.scan(str(search_path))
            stats = scanner.get_stats()

        if not discovered:
            warning(f"No projects found in {search_path}")
            console.print("\nTry:")
            console.print("  - Increasing max depth: --max-depth 15")
            console.print("  - Scanning a different directory")
            return

        console.print(
            f"[green]✓[/green] Found {len(discovered)} project(s) "
            f"({stats['directories_scanned']} directories scanned "
            f"in {stats['scan_duration_seconds']:.2f}s)\n"
        )

        # Step 2: Classify projects
        with console.status("[bold green]Classifying project types..."):
            classifier = TypeClassifier()
            for project in discovered:
                classifier.classify(project)

        # Step 3: Analyze dependencies
        with console.status("[bold green]Analyzing dependencies..."):
            analyzer = DependencyAnalyzer()
            discovered, relations = analyzer.analyze(discovered)

        # Step 4: Generate configuration
        generator = ConfigGenerator()
        config = generator.generate(
            projects=discovered,
            relations=relations,
            workspace_name=name,
            base_path=str(search_path),
        )

        # Output results
        if json_output:
            output = {
                "workspace_name": config.name,
                "projects_found": len(discovered),
                "projects": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "path": p.path,
                        "type": p.type,
                        "confidence": discovered[idx].confidence,
                        "framework": discovered[idx].framework,
                        "languages": p.language,
                        "dependencies": p.dependencies,
                    }
                    for idx, p in enumerate(config.projects)
                ],
                "relationships": [
                    {
                        "from": r.from_project,
                        "to": r.to_project,
                        "type": r.type,
                        "description": r.description,
                    }
                    for r in config.relationships
                ],
            }
            print(json.dumps(output, indent=2))
            return

        # Display discovered projects
        console.print(Panel(
            f"[bold]{config.name}[/bold]\n"
            f"Discovered [cyan]{len(discovered)}[/cyan] projects",
            title="Workspace Discovery",
            border_style="blue"
        ))

        # Create projects table
        table = Table(title="Discovered Projects", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=3)
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Confidence", style="yellow", justify="right")
        table.add_column("Framework", style="green")
        table.add_column("Languages", style="blue")
        table.add_column("Dependencies", style="white")

        for idx, (project, config_proj) in enumerate(zip(discovered, config.projects), 1):
            confidence_str = f"{project.confidence * 100:.0f}%"
            confidence_color = "green" if project.confidence >= 0.8 else "yellow" if project.confidence >= 0.6 else "red"

            table.add_row(
                str(idx),
                config_proj.id,
                project.type.value,
                f"[{confidence_color}]{confidence_str}[/{confidence_color}]",
                project.framework or "—",
                ", ".join(project.detected_languages[:3]) if project.detected_languages else "—",
                ", ".join(project.detected_dependencies[:3]) if project.detected_dependencies else "—",
            )

        console.print("\n")
        console.print(table)

        # Show relationships if any
        if config.relationships:
            console.print(f"\n[bold]Relationships Detected:[/bold] {len(config.relationships)}")
            for rel in config.relationships[:5]:  # Show first 5
                console.print(f"  • {rel.from_project} → {rel.to_project} ([dim]{rel.type}[/dim])")
            if len(config.relationships) > 5:
                console.print(f"  ... and {len(config.relationships) - 5} more")

        # Interactive confirmation
        if interactive:
            console.print("\n")
            if not click.confirm(f"Save workspace configuration to {workspace_path}?", default=True):
                error("Aborted", exit_code=0)

        # Save configuration
        config.save(workspace_path)
        success(f"Workspace configuration saved to {workspace_path.absolute()}")

        # Show next steps
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Review configuration: [cyan]context workspace list --verbose[/cyan]")
        console.print("  2. Adjust if needed: Edit .context-workspace.json")
        console.print("  3. Index projects: [cyan]context workspace index[/cyan]")
        console.print("  4. Search workspace: [cyan]context workspace search 'your query'[/cyan]")

    except Exception as e:
        import traceback
        error(f"Discovery failed: {e}\n{traceback.format_exc()}")


@workspace_cli.command(name="migrate")
@click.option("--from", "from_path", required=True, help="Path to old single-folder project")
@click.option("--name", required=True, help="Name for the project in workspace")
@click.option("--workspace", default=".context-workspace.json", help="Path to workspace config file")
@click.option("--project-id", help="Project ID (defaults to sanitized name)")
@click.option("--type", "project_type", default="application", help="Project type")
def migrate(from_path: str, name: str, workspace: str, project_id: Optional[str], project_type: str) -> None:
    """Migrate from single-folder v1 setup to workspace v2"""
    try:
        from_path_obj = Path(from_path)
        workspace_path = Path(workspace)

        # Validate source path
        if not from_path_obj.exists():
            error(f"Source path does not exist: {from_path}")

        if not from_path_obj.is_dir():
            error(f"Source path is not a directory: {from_path}")

        # Generate project ID if not provided
        if not project_id:
            # Sanitize name to create ID
            project_id = name.lower().replace(" ", "_").replace("-", "_")
            project_id = "".join(c for c in project_id if c.isalnum() or c == "_")

        console.print(f"Migrating project from: {from_path_obj}")
        console.print(f"Project ID: {project_id}")
        console.print(f"Project Name: {name}\n")

        # Check if workspace config exists
        if workspace_path.exists():
            # Load existing workspace
            config = WorkspaceConfig.load(workspace_path, validate_paths=False)
            console.print(f"Adding to existing workspace: {config.name}")

            # Check if project ID already exists
            if config.get_project(project_id):
                error(f"Project with ID '{project_id}' already exists in workspace")
        else:
            # Create new workspace
            console.print("Creating new workspace configuration")
            config = WorkspaceConfig(
                version="2.0.0",
                name=f"{name} Workspace",
                projects=[],
                relationships=[],
            )

        # Detect languages by scanning directory
        languages = []
        language_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust",
        }

        for ext, lang in language_extensions.items():
            if list(from_path_obj.rglob(f"*{ext}")):
                if lang not in languages:
                    languages.append(lang)

        # Detect common exclusion patterns
        exclude_patterns = []
        common_excludes = ["node_modules", "dist", "build", ".next", "__pycache__", ".git", "venv"]
        for pattern in common_excludes:
            if (from_path_obj / pattern).exists():
                exclude_patterns.append(pattern)

        # Create project config
        project_config = ProjectConfig(
            id=project_id,
            name=name,
            path=str(from_path_obj.absolute()),
            type=project_type,
            language=languages,
            dependencies=[],
            indexing=IndexingConfig(
                enabled=True,
                priority="medium",
                exclude=exclude_patterns,
            ),
        )

        # Add to workspace
        config.projects.append(project_config)

        # Resolve and validate paths
        config.resolve_paths(workspace_path.parent)
        config.validate(check_paths=True)

        # Save workspace config
        config.save(workspace_path)

        success(f"Migrated project '{name}' to workspace")

        # Show migration summary
        table = Table(title="Migration Summary", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Project ID", project_id)
        table.add_row("Project Name", name)
        table.add_row("Path", str(from_path_obj))
        table.add_row("Type", project_type)
        table.add_row("Languages Detected", ", ".join(languages) if languages else "None")
        table.add_row("Exclusions", ", ".join(exclude_patterns) if exclude_patterns else "None")
        table.add_row("Workspace File", str(workspace_path.absolute()))

        console.print("\n")
        console.print(table)

        console.print(f"\n[dim]Next steps:[/dim]")
        console.print(f"  1. Review workspace: [cyan]context workspace list --verbose[/cyan]")
        console.print(f"  2. Index project: [cyan]context workspace index --project {project_id}[/cyan]")

    except Exception as e:
        error(f"Migration failed: {e}")


if __name__ == "__main__":
    workspace_cli()
