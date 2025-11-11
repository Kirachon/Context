"""
Context CLI - Main Entry Point

Command-line interface for the Context codebase intelligence platform.
"""

from __future__ import annotations

import click

from src.cli.multifile import multifile_cli
from src.cli.workspace import workspace_cli


@click.group()
@click.version_option(version="3.0.0", prog_name="context")
def cli():
    """
    Context - Codebase Intelligence Platform v3.0

    Manage multi-project workspaces with intelligent indexing,
    relationship tracking, cross-project search, multi-file editing,
    and automated PR generation.
    """
    pass


# Register subcommands
cli.add_command(workspace_cli, name="workspace")
cli.add_command(multifile_cli, name="edit")


def main():
    """Entry point for console script"""
    cli()


if __name__ == "__main__":
    main()
