#!/usr/bin/env python3
"""
Workspace Migration Script

Migrates single-folder v1 setups to multi-project workspace v2.
Handles Qdrant collection migration, workspace config generation, and validation.
"""

import asyncio
import json
import shutil
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import logging

import click
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.workspace.config import WorkspaceConfig, ProjectConfig, IndexingConfig
from src.config.settings import settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migration.log')
    ]
)
logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Migration-specific errors"""
    pass


class WorkspaceMigrator:
    """
    Handles migration from v1 single-folder to v2 workspace setup
    """

    def __init__(
        self,
        project_path: str,
        project_name: str,
        workspace_output: str = ".context-workspace.json",
        dry_run: bool = False,
        no_backup: bool = False
    ):
        self.project_path = Path(project_path).resolve()
        self.project_name = project_name
        self.workspace_output = Path(workspace_output)
        self.dry_run = dry_run
        self.no_backup = no_backup

        # Migration state
        self.detected_languages: List[str] = []
        self.detected_type: str = "application"
        self.existing_collections: List[str] = []
        self.backup_dir: Optional[Path] = None
        self.qdrant_client: Optional[QdrantClient] = None

        logger.info(f"Migrator initialized: project={project_path}, dry_run={dry_run}")

    async def migrate(self) -> bool:
        """
        Execute full migration workflow

        Returns:
            bool: True if migration successful
        """
        try:
            logger.info("=" * 80)
            logger.info("Starting workspace migration...")
            logger.info("=" * 80)

            # Step 1: Pre-flight checks
            click.echo("🔍 Step 1/7: Running pre-flight checks...")
            await self._preflight_checks()

            # Step 2: Detect current setup
            click.echo("\n🔍 Step 2/7: Analyzing current setup...")
            await self._detect_setup()

            # Step 3: Create backups
            if not self.no_backup and not self.dry_run:
                click.echo("\n💾 Step 3/7: Creating backups...")
                await self._create_backups()
            else:
                click.echo("\n⏭️  Step 3/7: Skipping backups (dry-run or --no-backup)")

            # Step 4: Generate workspace config
            click.echo("\n📝 Step 4/7: Generating workspace configuration...")
            workspace_config = await self._generate_workspace_config()

            # Step 5: Migrate Qdrant collections
            click.echo("\n🔄 Step 5/7: Migrating Qdrant collections...")
            collection_migrations = await self._plan_collection_migrations()

            if self.dry_run:
                click.echo("\n" + "=" * 80)
                click.echo("🔍 DRY RUN - No changes will be made")
                click.echo("=" * 80)
                await self._print_dry_run_summary(workspace_config, collection_migrations)
                return True

            # Execute migrations
            await self._execute_collection_migrations(collection_migrations)

            # Step 6: Write workspace config
            click.echo("\n💾 Step 6/7: Writing workspace configuration...")
            workspace_config.save(self.workspace_output)
            click.echo(f"✅ Created {self.workspace_output}")

            # Step 7: Validate migration
            click.echo("\n✅ Step 7/7: Validating migration...")
            await self._validate_migration()

            click.echo("\n" + "=" * 80)
            click.echo("🎉 Migration completed successfully!")
            click.echo("=" * 80)
            self._print_next_steps()

            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            click.echo(f"\n❌ Migration failed: {e}", err=True)

            if self.backup_dir and not self.dry_run:
                click.echo(f"\n💡 Backups are available in: {self.backup_dir}")
                click.echo("   You can restore using: --rollback")

            return False

    async def _preflight_checks(self) -> None:
        """Run pre-flight checks before migration"""
        errors = []

        # Check if workspace config already exists
        if self.workspace_output.exists():
            errors.append(
                f"Workspace config already exists: {self.workspace_output}\n"
                f"   Already in workspace mode or migration was already run."
            )

        # Check if project path exists
        if not self.project_path.exists():
            errors.append(f"Project path does not exist: {self.project_path}")
        elif not self.project_path.is_dir():
            errors.append(f"Project path is not a directory: {self.project_path}")

        # Check Qdrant connection
        try:
            self.qdrant_client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
                timeout=10.0,
            )
            # Test connection
            self.qdrant_client.get_collections()
            click.echo(f"   ✓ Connected to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")
        except Exception as e:
            errors.append(f"Cannot connect to Qdrant: {e}")

        if errors:
            raise MigrationError(
                "Pre-flight checks failed:\n" +
                "\n".join(f"  ❌ {error}" for error in errors)
            )

        click.echo("   ✓ All pre-flight checks passed")

    async def _detect_setup(self) -> None:
        """Detect current project setup"""
        click.echo(f"   📁 Project path: {self.project_path}")

        # Detect languages by file extensions
        language_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.hpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
        }

        detected_langs = set()
        file_count = 0

        for ext, lang in language_extensions.items():
            files = list(self.project_path.rglob(f"*{ext}"))
            if files:
                detected_langs.add(lang)
                file_count += len(files)

        self.detected_languages = sorted(list(detected_langs))
        click.echo(f"   📚 Detected languages: {', '.join(self.detected_languages) or 'none'}")
        click.echo(f"   📄 Total files: {file_count}")

        # Detect project type
        self.detected_type = self._detect_project_type()
        click.echo(f"   🏷️  Project type: {self.detected_type}")

        # Detect existing Qdrant collections
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            # Look for v1 collections
            v1_collections = [
                'context_vectors',
                'context_symbols',
                'context_classes',
                'context_imports'
            ]

            self.existing_collections = [
                name for name in v1_collections if name in collection_names
            ]

            if self.existing_collections:
                click.echo(f"   🗂️  Found v1 collections: {', '.join(self.existing_collections)}")
            else:
                click.echo("   ℹ️  No v1 collections found (will start fresh)")

        except Exception as e:
            logger.error(f"Error detecting collections: {e}")
            click.echo(f"   ⚠️  Could not detect collections: {e}", err=True)

    def _detect_project_type(self) -> str:
        """
        Detect project type based on file patterns and structure

        Returns:
            Project type string
        """
        # Check for common framework/project indicators
        if (self.project_path / "package.json").exists():
            package_json = json.loads((self.project_path / "package.json").read_text())
            deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}

            if "react" in deps or "next" in deps:
                return "web_frontend"
            elif "express" in deps or "fastify" in deps:
                return "api_server"

        if (self.project_path / "pyproject.toml").exists() or (self.project_path / "setup.py").exists():
            # Check for common Python frameworks
            if (self.project_path / "manage.py").exists():
                return "web_backend"  # Django
            elif list(self.project_path.rglob("*fastapi*")):
                return "api_server"
            elif list(self.project_path.rglob("*flask*")):
                return "web_backend"

        if (self.project_path / "Cargo.toml").exists():
            return "library"

        if (self.project_path / "go.mod").exists():
            return "application"

        # Default
        return "application"

    async def _create_backups(self) -> None:
        """Create backups of settings and Qdrant collections"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.backup_dir = Path(f"migration_backup_{timestamp}")
        self.backup_dir.mkdir(exist_ok=True)

        click.echo(f"   📦 Backup directory: {self.backup_dir}")

        # Backup settings.py if it exists
        settings_path = PROJECT_ROOT / "src" / "config" / "settings.py"
        if settings_path.exists():
            backup_settings = self.backup_dir / "settings.py.backup"
            shutil.copy2(settings_path, backup_settings)
            click.echo(f"   ✓ Backed up settings.py")

        # Backup Qdrant collections (export metadata)
        if self.existing_collections:
            collections_backup = self.backup_dir / "qdrant_collections.json"
            backup_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "collections": {}
            }

            for collection_name in self.existing_collections:
                try:
                    collection_info = self.qdrant_client.get_collection(collection_name)
                    backup_data["collections"][collection_name] = {
                        "vectors_count": collection_info.vectors_count,
                        "points_count": collection_info.points_count,
                    }
                except Exception as e:
                    logger.error(f"Error backing up collection {collection_name}: {e}")

            collections_backup.write_text(json.dumps(backup_data, indent=2))
            click.echo(f"   ✓ Backed up Qdrant collection metadata")

        click.echo(f"   ✅ Backups completed in: {self.backup_dir}")

    async def _generate_workspace_config(self) -> WorkspaceConfig:
        """
        Generate workspace configuration

        Returns:
            WorkspaceConfig instance
        """
        project_config = ProjectConfig(
            id="default",
            name=self.project_name,
            path=str(self.project_path),
            type=self.detected_type,
            language=self.detected_languages,
            dependencies=[],
            indexing=IndexingConfig(
                enabled=True,
                priority="high",
                exclude=[
                    ".git",
                    ".venv",
                    "venv",
                    "node_modules",
                    "__pycache__",
                    ".pytest_cache",
                    "dist",
                    "build",
                    ".next"
                ]
            ),
            metadata={
                "migrated_from_v1": True,
                "migration_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        workspace_config = WorkspaceConfig(
            version="2.0.0",
            name=self.project_name,
            projects=[project_config],
            relationships=[],
        )

        # Resolve paths
        workspace_config.resolve_paths(self.workspace_output.parent.resolve())

        click.echo(f"   ✓ Generated workspace config")
        click.echo(f"     - Project ID: {project_config.id}")
        click.echo(f"     - Project name: {project_config.name}")
        click.echo(f"     - Project type: {project_config.type}")
        click.echo(f"     - Languages: {', '.join(project_config.language) or 'none'}")

        return workspace_config

    async def _plan_collection_migrations(self) -> List[Dict[str, str]]:
        """
        Plan collection migrations (old name -> new name)

        Returns:
            List of migration plans
        """
        migrations = []

        collection_mappings = {
            'context_vectors': 'project_default_vectors',
            'context_symbols': 'project_default_symbols',
            'context_classes': 'project_default_classes',
            'context_imports': 'project_default_imports',
        }

        for old_name in self.existing_collections:
            new_name = collection_mappings.get(old_name)
            if new_name:
                migrations.append({
                    "old_name": old_name,
                    "new_name": new_name,
                    "action": "rename"
                })

        if migrations:
            click.echo(f"   📋 Planned {len(migrations)} collection migrations:")
            for migration in migrations:
                click.echo(f"      • {migration['old_name']} → {migration['new_name']}")
        else:
            click.echo("   ℹ️  No collections to migrate")

        return migrations

    async def _execute_collection_migrations(self, migrations: List[Dict[str, str]]) -> None:
        """
        Execute Qdrant collection migrations

        Args:
            migrations: List of migration plans
        """
        if not migrations:
            click.echo("   ⏭️  No collections to migrate")
            return

        click.echo(f"   🔄 Migrating {len(migrations)} collections...")

        for i, migration in enumerate(migrations, 1):
            old_name = migration["old_name"]
            new_name = migration["new_name"]

            try:
                click.echo(f"   [{i}/{len(migrations)}] Migrating {old_name}...")

                # Get collection info
                old_collection = self.qdrant_client.get_collection(old_name)

                # Create new collection with same config
                self.qdrant_client.create_collection(
                    collection_name=new_name,
                    vectors_config=old_collection.config.params.vectors
                )

                # Copy all points from old to new collection
                # Note: For large collections, this should be done in batches
                offset = None
                batch_size = 100
                total_copied = 0

                while True:
                    # Scroll through old collection
                    records, offset = self.qdrant_client.scroll(
                        collection_name=old_name,
                        limit=batch_size,
                        offset=offset,
                        with_payload=True,
                        with_vectors=True,
                    )

                    if not records:
                        break

                    # Upsert to new collection
                    points = [
                        {
                            "id": record.id,
                            "vector": record.vector,
                            "payload": record.payload,
                        }
                        for record in records
                    ]

                    self.qdrant_client.upsert(
                        collection_name=new_name,
                        points=points
                    )

                    total_copied += len(records)

                    if offset is None:
                        break

                click.echo(f"      ✓ Copied {total_copied} vectors to {new_name}")

                # Delete old collection
                self.qdrant_client.delete_collection(old_name)
                click.echo(f"      ✓ Deleted old collection {old_name}")

            except Exception as e:
                logger.error(f"Error migrating collection {old_name}: {e}", exc_info=True)
                raise MigrationError(f"Failed to migrate collection {old_name}: {e}")

        click.echo(f"   ✅ All collections migrated successfully")

    async def _validate_migration(self) -> None:
        """Validate migration was successful"""
        errors = []

        # Check workspace config exists
        if not self.workspace_output.exists():
            errors.append(f"Workspace config not found: {self.workspace_output}")

        # Try to load workspace config
        try:
            config = WorkspaceConfig.load(self.workspace_output, validate_paths=True)
            click.echo(f"   ✓ Workspace config is valid")
            click.echo(f"     - Version: {config.version}")
            click.echo(f"     - Projects: {len(config.projects)}")
        except Exception as e:
            errors.append(f"Workspace config invalid: {e}")

        # Check new collections exist
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            expected_collections = [
                'project_default_vectors',
                'project_default_symbols',
                'project_default_classes',
                'project_default_imports',
            ]

            found_collections = [name for name in expected_collections if name in collection_names]
            if found_collections:
                click.echo(f"   ✓ Found {len(found_collections)} migrated collections")
            else:
                click.echo(f"   ℹ️  No v2 collections found (empty migration)")

        except Exception as e:
            errors.append(f"Could not verify collections: {e}")

        if errors:
            raise MigrationError(
                "Validation failed:\n" +
                "\n".join(f"  ❌ {error}" for error in errors)
            )

        click.echo("   ✅ Migration validated successfully")

    async def _print_dry_run_summary(
        self,
        workspace_config: WorkspaceConfig,
        collection_migrations: List[Dict[str, str]]
    ) -> None:
        """Print dry-run summary"""
        click.echo("\n📋 Workspace Configuration:")
        click.echo(json.dumps(workspace_config.model_dump(mode="json"), indent=2))

        click.echo("\n📋 Qdrant Collection Migrations:")
        if collection_migrations:
            for migration in collection_migrations:
                click.echo(f"   • {migration['old_name']} → {migration['new_name']}")
        else:
            click.echo("   (no migrations needed)")

        click.echo(f"\n📋 Output Files:")
        click.echo(f"   • {self.workspace_output}")

        click.echo("\n💡 To execute migration, run without --dry-run flag")

    def _print_next_steps(self) -> None:
        """Print next steps after successful migration"""
        click.echo("\n📖 Next Steps:")
        click.echo("")
        click.echo("  1. Review the generated workspace config:")
        click.echo(f"     cat {self.workspace_output}")
        click.echo("")
        click.echo("  2. Set WORKSPACE_MODE=true in your environment:")
        click.echo("     export WORKSPACE_MODE=true")
        click.echo("")
        click.echo("  3. Start the Context server:")
        click.echo("     python -m src.main")
        click.echo("")
        click.echo("  4. (Optional) Index your workspace:")
        click.echo("     # This will be done automatically on startup")
        click.echo("")
        click.echo("  5. Test workspace search:")
        click.echo("     # Use the MCP tools or API endpoints")
        click.echo("")

        if self.backup_dir:
            click.echo(f"📦 Backups saved in: {self.backup_dir}")
            click.echo("")


async def rollback_migration(backup_dir: str) -> bool:
    """
    Rollback a migration using backup directory

    Args:
        backup_dir: Path to backup directory

    Returns:
        bool: True if rollback successful
    """
    backup_path = Path(backup_dir)

    if not backup_path.exists():
        click.echo(f"❌ Backup directory not found: {backup_dir}", err=True)
        return False

    click.echo(f"🔄 Rolling back migration from: {backup_dir}")

    try:
        # Restore settings.py
        backup_settings = backup_path / "settings.py.backup"
        if backup_settings.exists():
            settings_path = PROJECT_ROOT / "src" / "config" / "settings.py"
            shutil.copy2(backup_settings, settings_path)
            click.echo("   ✓ Restored settings.py")

        # Note: Collection rollback would need to restore from actual data backup
        # which is more complex and not implemented here
        click.echo("   ⚠️  Qdrant collections cannot be automatically restored")
        click.echo("      Manual intervention may be required")

        # Remove workspace config
        workspace_config = Path(".context-workspace.json")
        if workspace_config.exists():
            workspace_config.unlink()
            click.echo("   ✓ Removed .context-workspace.json")

        click.echo("\n✅ Rollback completed")
        click.echo("⚠️  Please verify your setup before continuing")

        return True

    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        click.echo(f"\n❌ Rollback failed: {e}", err=True)
        return False


@click.command()
@click.option(
    '--from', 'project_path',
    required=True,
    type=click.Path(exists=True),
    help='Path to the project directory to migrate'
)
@click.option(
    '--name',
    required=True,
    help='Project name for workspace configuration'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be done without making changes'
)
@click.option(
    '--no-backup',
    is_flag=True,
    help='Skip creating backups (not recommended)'
)
@click.option(
    '--output',
    default='.context-workspace.json',
    help='Output path for workspace configuration file'
)
@click.option(
    '--rollback',
    type=click.Path(exists=True),
    help='Rollback migration using backup directory'
)
def migrate_command(
    project_path: str,
    name: str,
    dry_run: bool,
    no_backup: bool,
    output: str,
    rollback: Optional[str]
):
    """
    Migrate single-folder v1 setup to workspace v2

    Examples:

    \b
    # Dry-run to see what would happen
    python scripts/migrate_to_workspace.py \\
        --from /path/to/project \\
        --name "My Project" \\
        --dry-run

    \b
    # Execute migration
    python scripts/migrate_to_workspace.py \\
        --from /path/to/project \\
        --name "My Project"

    \b
    # Rollback migration
    python scripts/migrate_to_workspace.py \\
        --rollback migration_backup_20231110_120000
    """
    # Handle rollback
    if rollback:
        success = asyncio.run(rollback_migration(rollback))
        sys.exit(0 if success else 1)

    # Execute migration
    migrator = WorkspaceMigrator(
        project_path=project_path,
        project_name=name,
        workspace_output=output,
        dry_run=dry_run,
        no_backup=no_backup
    )

    success = asyncio.run(migrator.migrate())
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    migrate_command()
