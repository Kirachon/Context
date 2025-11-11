"""
Multi-File Editing Module

Provides atomic multi-file editing, conflict detection, validation,
and rollback capabilities for coordinated changes across repositories.
"""

from .editor import MultiFileEditor, FileChange, ChangeSet
from .pr_generator import PRGenerator, PullRequest

__all__ = [
    'MultiFileEditor',
    'FileChange',
    'ChangeSet',
    'PRGenerator',
    'PullRequest',
]
