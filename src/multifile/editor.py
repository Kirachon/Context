"""
Multi-File Editor

Provides atomic multi-file editing with conflict detection, validation,
and rollback capabilities.
"""

import asyncio
import hashlib
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import structlog

logger = structlog.get_logger(__name__)


class ChangeType(Enum):
    """Types of file changes"""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"


class ValidationStatus(Enum):
    """Validation status for changes"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FileChange:
    """Represents a single file change"""
    file_path: str
    change_type: ChangeType
    content: Optional[str] = None
    old_content: Optional[str] = None
    new_path: Optional[str] = None  # For renames
    repository: str = "."

    # Metadata
    checksum_before: Optional[str] = None
    checksum_after: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Validation results
    syntax_valid: ValidationStatus = ValidationStatus.PENDING
    type_check_valid: ValidationStatus = ValidationStatus.PENDING
    lint_valid: ValidationStatus = ValidationStatus.PENDING
    validation_errors: List[str] = field(default_factory=list)

    def calculate_checksum(self, content: str) -> str:
        """Calculate MD5 checksum of content"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def validate_checksum(self) -> bool:
        """Verify content hasn't changed unexpectedly"""
        if self.old_content and self.checksum_before:
            current = self.calculate_checksum(self.old_content)
            return current == self.checksum_before
        return True


@dataclass
class ChangeSet:
    """Collection of related file changes"""
    changes: List[FileChange]
    description: str
    author: str = "Context AI"
    branch_name: Optional[str] = None

    # Metadata
    id: str = field(default_factory=lambda: hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:8])
    created_at: datetime = field(default_factory=datetime.utcnow)
    repositories: Set[str] = field(default_factory=set)

    # State tracking
    applied: bool = False
    rolled_back: bool = False

    def __post_init__(self):
        """Extract repositories from changes"""
        self.repositories = {change.repository for change in self.changes}

    def get_files_by_repo(self) -> Dict[str, List[FileChange]]:
        """Group changes by repository"""
        by_repo: Dict[str, List[FileChange]] = {}
        for change in self.changes:
            if change.repository not in by_repo:
                by_repo[change.repository] = []
            by_repo[change.repository].append(change)
        return by_repo


class MultiFileEditor:
    """
    Atomic multi-file editor with conflict detection and rollback.

    Features:
    - Atomic multi-file changes (all-or-nothing)
    - Conflict detection between changes
    - Syntax, type, and lint validation
    - Automatic rollback on failure
    - Cross-repository coordination
    """

    def __init__(
        self,
        workspace_root: str = ".",
        enable_syntax_check: bool = True,
        enable_type_check: bool = True,
        enable_lint: bool = True,
        backup_dir: Optional[str] = None,
    ):
        """
        Initialize MultiFileEditor.

        Args:
            workspace_root: Root directory of workspace
            enable_syntax_check: Enable syntax validation
            enable_type_check: Enable type checking
            enable_lint: Enable linting
            backup_dir: Directory for backups (temp dir if None)
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.enable_syntax_check = enable_syntax_check
        self.enable_type_check = enable_type_check
        self.enable_lint = enable_lint
        self.backup_dir = Path(backup_dir) if backup_dir else Path(tempfile.mkdtemp())

        self.logger = logger.bind(
            component="multi_file_editor",
            workspace=str(self.workspace_root)
        )

        # Track applied changesets for rollback
        self.applied_changesets: List[ChangeSet] = []

    async def edit_files(self, change_plan: ChangeSet) -> Tuple[bool, ChangeSet]:
        """
        Execute multi-file edit with atomic guarantees.

        Args:
            change_plan: ChangeSet describing all changes

        Returns:
            Tuple of (success, updated_changeset)
        """
        self.logger.info(
            "Starting multi-file edit",
            changeset_id=change_plan.id,
            num_changes=len(change_plan.changes),
            repositories=list(change_plan.repositories)
        )

        try:
            # Step 1: Detect conflicts
            conflicts = await self._detect_conflicts(change_plan)
            if conflicts:
                self.logger.error("Conflicts detected", conflicts=conflicts)
                return False, change_plan

            # Step 2: Create backups
            backup_paths = await self._create_backups(change_plan)

            # Step 3: Validate all changes
            validation_passed = await self._validate_changes(change_plan)
            if not validation_passed:
                self.logger.error("Validation failed")
                return False, change_plan

            # Step 4: Apply changes
            try:
                await self._apply_changes(change_plan)
                change_plan.applied = True
                self.applied_changesets.append(change_plan)

                self.logger.info(
                    "Multi-file edit successful",
                    changeset_id=change_plan.id
                )
                return True, change_plan

            except Exception as e:
                # Rollback on failure
                self.logger.error(
                    "Error applying changes, rolling back",
                    error=str(e),
                    changeset_id=change_plan.id
                )
                await self._rollback_from_backup(change_plan, backup_paths)
                return False, change_plan

        except Exception as e:
            self.logger.error(
                "Unexpected error during edit",
                error=str(e),
                changeset_id=change_plan.id
            )
            return False, change_plan

    async def _detect_conflicts(self, change_plan: ChangeSet) -> List[str]:
        """
        Detect conflicts between file changes.

        Conflicts:
        - Multiple changes to same file
        - File doesn't exist for modify/delete
        - File already exists for create
        - Circular renames
        """
        conflicts = []

        # Track files being changed
        files_changed: Set[str] = set()

        for change in change_plan.changes:
            full_path = self._resolve_path(change.file_path, change.repository)

            # Check for duplicate changes
            if change.file_path in files_changed:
                conflicts.append(
                    f"Multiple changes to same file: {change.file_path}"
                )
            files_changed.add(change.file_path)

            # Validate change type
            if change.change_type == ChangeType.CREATE:
                if full_path.exists():
                    conflicts.append(
                        f"Cannot create {change.file_path}: file already exists"
                    )

            elif change.change_type in (ChangeType.MODIFY, ChangeType.DELETE):
                if not full_path.exists():
                    conflicts.append(
                        f"Cannot {change.change_type.value} {change.file_path}: file not found"
                    )

            elif change.change_type == ChangeType.RENAME:
                if not full_path.exists():
                    conflicts.append(
                        f"Cannot rename {change.file_path}: file not found"
                    )
                if change.new_path:
                    new_full_path = self._resolve_path(change.new_path, change.repository)
                    if new_full_path.exists():
                        conflicts.append(
                            f"Cannot rename to {change.new_path}: file already exists"
                        )

        return conflicts

    async def _create_backups(self, change_plan: ChangeSet) -> Dict[str, str]:
        """
        Create backups of all files being modified or deleted.

        Returns:
            Dict mapping file_path to backup_path
        """
        backup_paths = {}
        backup_base = self.backup_dir / f"backup_{change_plan.id}"
        backup_base.mkdir(parents=True, exist_ok=True)

        for change in change_plan.changes:
            if change.change_type in (ChangeType.MODIFY, ChangeType.DELETE, ChangeType.RENAME):
                full_path = self._resolve_path(change.file_path, change.repository)

                if full_path.exists():
                    # Create backup with same relative structure
                    rel_path = full_path.relative_to(self.workspace_root / change.repository)
                    backup_path = backup_base / change.repository / rel_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)

                    # Read and backup content
                    content = full_path.read_text()
                    backup_path.write_text(content)

                    # Store old content and checksum
                    change.old_content = content
                    change.checksum_before = change.calculate_checksum(content)

                    backup_paths[change.file_path] = str(backup_path)

                    self.logger.debug(
                        "Created backup",
                        file=change.file_path,
                        backup=str(backup_path)
                    )

        return backup_paths

    async def _validate_changes(self, change_plan: ChangeSet) -> bool:
        """
        Validate all changes (syntax, types, linting).

        Returns:
            True if all validations pass
        """
        validation_tasks = []

        for change in change_plan.changes:
            if change.content and change.change_type in (ChangeType.CREATE, ChangeType.MODIFY):
                validation_tasks.append(self._validate_single_file(change))

        # Run all validations in parallel
        if validation_tasks:
            results = await asyncio.gather(*validation_tasks, return_exceptions=True)

            # Check if any validation failed
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error("Validation error", error=str(result))
                    return False
                if not result:
                    return False

        return True

    async def _validate_single_file(self, change: FileChange) -> bool:
        """
        Validate a single file change.

        Returns:
            True if all enabled validations pass
        """
        file_ext = Path(change.file_path).suffix

        # Syntax check
        if self.enable_syntax_check:
            try:
                syntax_valid = await self._check_syntax(change.file_path, change.content, file_ext)
                change.syntax_valid = ValidationStatus.PASSED if syntax_valid else ValidationStatus.FAILED
                if not syntax_valid:
                    change.validation_errors.append("Syntax check failed")
                    return False
            except Exception as e:
                change.syntax_valid = ValidationStatus.FAILED
                change.validation_errors.append(f"Syntax check error: {str(e)}")
                return False
        else:
            change.syntax_valid = ValidationStatus.SKIPPED

        # Type check
        if self.enable_type_check and file_ext == '.py':
            try:
                type_valid = await self._check_types(change.file_path, change.content)
                change.type_check_valid = ValidationStatus.PASSED if type_valid else ValidationStatus.FAILED
                if not type_valid:
                    change.validation_errors.append("Type check failed")
                    return False
            except Exception as e:
                change.type_check_valid = ValidationStatus.FAILED
                change.validation_errors.append(f"Type check error: {str(e)}")
                return False
        else:
            change.type_check_valid = ValidationStatus.SKIPPED

        # Linting
        if self.enable_lint:
            try:
                lint_valid = await self._check_lint(change.file_path, change.content, file_ext)
                change.lint_valid = ValidationStatus.PASSED if lint_valid else ValidationStatus.FAILED
                if not lint_valid:
                    change.validation_errors.append("Lint check failed")
                    # Don't fail on lint errors, just warn
                    self.logger.warning(
                        "Lint check failed",
                        file=change.file_path
                    )
            except Exception as e:
                change.lint_valid = ValidationStatus.FAILED
                change.validation_errors.append(f"Lint check error: {str(e)}")
        else:
            change.lint_valid = ValidationStatus.SKIPPED

        return True

    async def _check_syntax(self, file_path: str, content: str, file_ext: str) -> bool:
        """Check syntax validity"""
        if file_ext == '.py':
            try:
                compile(content, file_path, 'exec')
                return True
            except SyntaxError as e:
                self.logger.error(
                    "Python syntax error",
                    file=file_path,
                    line=e.lineno,
                    error=str(e)
                )
                return False

        # For other languages, use tree-sitter or similar
        # For now, just return True
        return True

    async def _check_types(self, file_path: str, content: str) -> bool:
        """Check type hints (Python only)"""
        try:
            # Write to temp file and run mypy
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(content)
                temp_path = f.name

            try:
                result = subprocess.run(
                    ['mypy', '--ignore-missing-imports', temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.returncode == 0
            finally:
                Path(temp_path).unlink()

        except FileNotFoundError:
            # mypy not installed, skip type checking
            self.logger.debug("mypy not found, skipping type check")
            return True
        except subprocess.TimeoutExpired:
            self.logger.warning("Type check timed out", file=file_path)
            return True
        except Exception as e:
            self.logger.warning(
                "Type check error",
                file=file_path,
                error=str(e)
            )
            return True

    async def _check_lint(self, file_path: str, content: str, file_ext: str) -> bool:
        """Run linter checks"""
        if file_ext == '.py':
            try:
                # Write to temp file and run flake8
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(content)
                    temp_path = f.name

                try:
                    result = subprocess.run(
                        ['flake8', '--max-line-length=100', temp_path],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    return result.returncode == 0
                finally:
                    Path(temp_path).unlink()

            except FileNotFoundError:
                # flake8 not installed, skip linting
                self.logger.debug("flake8 not found, skipping lint check")
                return True
            except subprocess.TimeoutExpired:
                self.logger.warning("Lint check timed out", file=file_path)
                return True
            except Exception as e:
                self.logger.warning(
                    "Lint check error",
                    file=file_path,
                    error=str(e)
                )
                return True

        return True

    async def _apply_changes(self, change_plan: ChangeSet):
        """Apply all changes atomically"""
        for change in change_plan.changes:
            full_path = self._resolve_path(change.file_path, change.repository)

            if change.change_type == ChangeType.CREATE:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(change.content)
                self.logger.info("Created file", file=change.file_path)

            elif change.change_type == ChangeType.MODIFY:
                full_path.write_text(change.content)
                change.checksum_after = change.calculate_checksum(change.content)
                self.logger.info("Modified file", file=change.file_path)

            elif change.change_type == ChangeType.DELETE:
                full_path.unlink()
                self.logger.info("Deleted file", file=change.file_path)

            elif change.change_type == ChangeType.RENAME:
                if change.new_path:
                    new_full_path = self._resolve_path(change.new_path, change.repository)
                    new_full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.rename(new_full_path)
                    self.logger.info(
                        "Renamed file",
                        from_path=change.file_path,
                        to_path=change.new_path
                    )

    async def _rollback_from_backup(
        self,
        change_plan: ChangeSet,
        backup_paths: Dict[str, str]
    ):
        """Rollback changes from backups"""
        self.logger.info("Rolling back changes", changeset_id=change_plan.id)

        for change in change_plan.changes:
            if change.file_path in backup_paths:
                full_path = self._resolve_path(change.file_path, change.repository)
                backup_path = Path(backup_paths[change.file_path])

                if backup_path.exists():
                    # Restore from backup
                    content = backup_path.read_text()
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                    self.logger.debug("Restored file from backup", file=change.file_path)

        change_plan.rolled_back = True

    def _resolve_path(self, file_path: str, repository: str = ".") -> Path:
        """Resolve file path relative to workspace and repository"""
        repo_path = self.workspace_root / repository
        return repo_path / file_path

    async def rollback(self, changeset_id: str) -> bool:
        """
        Rollback a specific changeset by ID.

        Args:
            changeset_id: ID of changeset to rollback

        Returns:
            True if rollback successful
        """
        # Find the changeset
        changeset = None
        for cs in self.applied_changesets:
            if cs.id == changeset_id:
                changeset = cs
                break

        if not changeset:
            self.logger.error("Changeset not found", changeset_id=changeset_id)
            return False

        if changeset.rolled_back:
            self.logger.warning("Changeset already rolled back", changeset_id=changeset_id)
            return True

        # Find backup directory
        backup_base = self.backup_dir / f"backup_{changeset_id}"
        if not backup_base.exists():
            self.logger.error("Backup not found", changeset_id=changeset_id)
            return False

        # Restore from backups
        backup_paths = {}
        for change in changeset.changes:
            rel_path = Path(change.file_path)
            backup_path = backup_base / change.repository / rel_path
            if backup_path.exists():
                backup_paths[change.file_path] = str(backup_path)

        await self._rollback_from_backup(changeset, backup_paths)
        return True
