"""
Context CLI - Main Entry Point

Command-line interface for the Context codebase intelligence platform.
"""

from __future__ import annotations

import click

from src.cli.workspace import workspace_cli


@click.group()
@click.version_option(version="2.0.0", prog_name="context")
def cli():
    """
    Context - Codebase Intelligence Platform

    Manage multi-project workspaces with intelligent indexing,
    relationship tracking, and cross-project search.
    """
    pass


# Register subcommands
cli.add_command(workspace_cli, name="workspace")


def main():
    """Entry point for console script"""
    cli()


if __name__ == "__main__":
    main()
