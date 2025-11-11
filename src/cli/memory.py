"""CLI commands for Memory System.

Provides commands to interact with conversation, pattern, solution, and preference memory.
"""

import click
import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from src.memory import ConversationStore, PatternStore, SolutionStore, PreferenceStore
from src.memory.database import init_database


console = Console()


@click.group()
def memory():
    """Memory system commands for conversations, patterns, solutions, and preferences."""
    pass


# ===== Conversation Memory Commands =====

@memory.group()
def conversations():
    """Manage conversation memory."""
    pass


@conversations.command()
@click.option('--query', required=True, help='Search query')
@click.option('--user-id', help='Filter by user ID')
@click.option('--intent', help='Filter by intent type')
@click.option('--limit', default=5, help='Maximum number of results')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table')
def search(query, user_id, intent, limit, output_format):
    """Search for similar conversations."""
    store = ConversationStore()

    results = store.get_similar_conversations(
        query=query,
        user_id=user_id,
        limit=limit,
        intent_filter=intent,
    )

    if output_format == 'json':
        output = []
        for result in results:
            conv = result['conversation']
            output.append({
                'id': str(conv.id),
                'user_id': conv.user_id,
                'timestamp': conv.timestamp.isoformat(),
                'prompt': conv.prompt,
                'intent': conv.intent,
                'similarity_score': result['similarity_score'],
            })
        click.echo(json.dumps(output, indent=2))
    else:
        if not results:
            console.print("[yellow]No conversations found[/yellow]")
            return

        table = Table(title=f"Similar Conversations for: {query}")
        table.add_column("Score", style="cyan")
        table.add_column("Intent", style="magenta")
        table.add_column("Prompt", style="green")
        table.add_column("Date", style="blue")

        for result in results:
            conv = result['conversation']
            table.add_row(
                f"{result['similarity_score']:.3f}",
                conv.intent or "unknown",
                conv.prompt[:60] + "..." if len(conv.prompt) > 60 else conv.prompt,
                conv.timestamp.strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)


@conversations.command()
@click.option('--user-id', help='Filter by user ID')
def stats(user_id):
    """Show conversation statistics."""
    store = ConversationStore()
    statistics = store.get_statistics(user_id=user_id)

    table = Table(title="Conversation Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Conversations", str(statistics['total_conversations']))
    table.add_row("Resolution Rate", f"{statistics['resolution_rate']:.1%}")
    table.add_row("Resolved Count", str(statistics['resolved_count']))

    if statistics['avg_latency_ms']:
        table.add_row("Avg Latency", f"{statistics['avg_latency_ms']:.0f}ms")
    if statistics['avg_token_count']:
        table.add_row("Avg Token Count", f"{statistics['avg_token_count']:.0f}")

    console.print(table)

    # Intent distribution
    if statistics['intent_distribution']:
        intent_table = Table(title="Intent Distribution")
        intent_table.add_column("Intent", style="magenta")
        intent_table.add_column("Count", style="green")

        for intent, count in statistics['intent_distribution'].items():
            if intent:
                intent_table.add_row(intent, str(count))

        console.print(intent_table)


# ===== Pattern Memory Commands =====

@memory.group()
def patterns():
    """Manage code pattern memory."""
    pass


@patterns.command()
@click.option('--type', 'pattern_type', help='Filter by pattern type')
@click.option('--project', help='Filter by project ID')
@click.option('--limit', default=20, help='Maximum number of results')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table')
def list(pattern_type, project, limit, output_format):
    """List code patterns."""
    store = PatternStore()

    patterns_list = store.get_patterns(
        pattern_type=pattern_type,
        project_id=project,
        limit=limit,
    )

    if output_format == 'json':
        output = []
        for pattern in patterns_list:
            output.append({
                'id': str(pattern.id),
                'type': pattern.pattern_type,
                'name': pattern.name,
                'usage_count': pattern.usage_count,
                'language': pattern.language,
            })
        click.echo(json.dumps(output, indent=2))
    else:
        if not patterns_list:
            console.print("[yellow]No patterns found[/yellow]")
            return

        table = Table(title="Code Patterns")
        table.add_column("Type", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Usage", style="magenta")
        table.add_column("Language", style="blue")

        for pattern in patterns_list:
            table.add_row(
                pattern.pattern_type,
                pattern.name or "unnamed",
                str(pattern.usage_count),
                pattern.language or "unknown",
            )

        console.print(table)


@patterns.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--project', help='Project ID')
def extract(directory, project):
    """Extract patterns from a directory."""
    store = PatternStore()

    console.print(f"[cyan]Extracting patterns from {directory}...[/cyan]")

    pattern_counts = store.extract_patterns_from_directory(
        directory=directory,
        project_id=project,
    )

    table = Table(title="Extracted Patterns")
    table.add_column("Pattern Type", style="cyan")
    table.add_column("Count", style="green")

    for pattern_type, count in pattern_counts.items():
        table.add_row(pattern_type, str(count))

    console.print(table)
    console.print(f"[green]✓ Extraction complete![/green]")


@patterns.command()
@click.option('--project', help='Filter by project ID')
def stats(project):
    """Show pattern statistics."""
    store = PatternStore()
    statistics = store.get_pattern_statistics(project_id=project)

    table = Table(title="Pattern Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Patterns", str(statistics['total_patterns']))

    console.print(table)

    # Type distribution
    if statistics['pattern_types']:
        type_table = Table(title="Pattern Type Distribution")
        type_table.add_column("Type", style="magenta")
        type_table.add_column("Count", style="green")

        for ptype, count in statistics['pattern_types'].items():
            if ptype:
                type_table.add_row(ptype, str(count))

        console.print(type_table)


# ===== Solution Memory Commands =====

@memory.group()
def solutions():
    """Manage solution memory."""
    pass


@solutions.command()
@click.option('--problem', required=True, help='Problem description')
@click.option('--project', help='Filter by project ID')
@click.option('--limit', default=3, help='Maximum number of results')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table')
def search(problem, project, limit, output_format):
    """Search for similar solutions."""
    store = SolutionStore()

    results = store.get_similar_solutions(
        problem=problem,
        project_id=project,
        limit=limit,
    )

    if output_format == 'json':
        output = []
        for result in results:
            sol = result['solution']
            output.append({
                'id': str(sol.id),
                'problem_type': sol.problem_type,
                'success_rate': sol.success_rate,
                'usage_count': sol.usage_count,
                'similarity_score': result['similarity_score'],
            })
        click.echo(json.dumps(output, indent=2))
    else:
        if not results:
            console.print("[yellow]No solutions found[/yellow]")
            return

        table = Table(title=f"Similar Solutions for: {problem[:50]}...")
        table.add_column("Score", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Success Rate", style="green")
        table.add_column("Usage", style="blue")

        for result in results:
            sol = result['solution']
            table.add_row(
                f"{result['similarity_score']:.3f}",
                sol.problem_type or "unknown",
                f"{sol.success_rate:.1%}",
                str(sol.usage_count),
            )

        console.print(table)


@solutions.command()
@click.option('--project', help='Filter by project ID')
def stats(project):
    """Show solution statistics."""
    store = SolutionStore()
    statistics = store.get_solution_statistics(project_id=project)

    table = Table(title="Solution Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Solutions", str(statistics['total_solutions']))
    table.add_row("Avg Success Rate", f"{statistics['avg_success_rate']:.1%}")
    table.add_row("Cluster Count", str(statistics['cluster_count']))

    console.print(table)


@solutions.command()
@click.option('--project', help='Filter by project ID')
def recluster(project):
    """Recluster all solutions."""
    store = SolutionStore()

    console.print("[cyan]Reclustering solutions...[/cyan]")

    result = store.recluster_solutions(project_id=project)

    console.print(f"[green]✓ Clustering complete![/green]")
    console.print(f"Clusters: {result['clusters']}")
    console.print(f"Solutions: {result['solutions']}")
    console.print(f"Outliers: {result['outliers']}")


# ===== Preference Memory Commands =====

@memory.group()
def preferences():
    """Manage user preference memory."""
    pass


@preferences.command()
@click.argument('user_id')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table')
def show(user_id, output_format):
    """Show user preferences."""
    store = PreferenceStore()
    prefs = store.get_user_preferences(user_id)

    if not prefs:
        console.print(f"[yellow]No preferences found for user {user_id}[/yellow]")
        return

    if output_format == 'json':
        output = {
            'user_id': prefs.user_id,
            'code_style': prefs.code_style,
            'preferred_libraries': prefs.preferred_libraries,
            'testing_approach': prefs.testing_approach,
            'documentation_level': prefs.documentation_level,
            'confidence_score': prefs.confidence_score,
            'sample_size': prefs.sample_size,
        }
        click.echo(json.dumps(output, indent=2))
    else:
        table = Table(title=f"Preferences for {user_id}")
        table.add_column("Preference", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Confidence Score", f"{prefs.confidence_score:.2f}")
        table.add_row("Sample Size", str(prefs.sample_size))

        if prefs.code_style:
            table.add_row("Indentation", prefs.code_style.get('indentation', 'unknown'))
            table.add_row("Quote Style", prefs.code_style.get('quote_style', 'unknown'))

        if prefs.testing_approach:
            table.add_row("Testing Approach", prefs.testing_approach)

        if prefs.documentation_level:
            table.add_row("Documentation Level", prefs.documentation_level)

        console.print(table)

        if prefs.preferred_libraries:
            lib_table = Table(title="Preferred Libraries")
            lib_table.add_column("Category", style="magenta")
            lib_table.add_column("Library", style="green")

            for category, library in prefs.preferred_libraries.items():
                lib_table.add_row(category, library)

            console.print(lib_table)


@preferences.command()
@click.argument('user_id')
@click.argument('repo_path', type=click.Path(exists=True))
@click.option('--max-commits', default=100, help='Maximum commits to analyze')
def learn(user_id, repo_path, max_commits):
    """Learn preferences from git history."""
    store = PreferenceStore()

    console.print(f"[cyan]Analyzing git history for {user_id}...[/cyan]")

    result = store.learn_from_git_history(
        user_id=user_id,
        repo_path=repo_path,
        max_commits=max_commits,
    )

    if 'error' in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        return

    console.print(f"[green]✓ Learning complete![/green]")
    console.print(f"Commits analyzed: {result['commits_analyzed']}")
    console.print(f"Confidence score: {result['confidence_score']:.2f}")


# ===== Database Commands =====

@memory.command()
def init():
    """Initialize memory database (create tables)."""
    console.print("[cyan]Initializing memory database...[/cyan]")
    init_database()
    console.print("[green]✓ Database initialized![/green]")


if __name__ == '__main__':
    memory()
