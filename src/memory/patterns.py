"""Pattern Memory: Extract and store code patterns from codebase.

Epic 6: Pattern Memory
- Extract common coding patterns from codebase
- Store patterns with usage statistics
- Retrieve patterns by type and project
- Track pattern prevalence across files
"""

import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from sqlalchemy import desc

from src.memory.database import get_db_manager
from src.memory.models import CodePattern


class PatternStore:
    """Store and retrieve code patterns extracted from codebase."""

    # Pattern types we recognize
    PATTERN_TYPES = {
        "api_design": "API endpoint design patterns",
        "error_handling": "Error handling and exception patterns",
        "testing": "Testing patterns (fixtures, mocks, assertions)",
        "data_validation": "Data validation patterns",
        "async_patterns": "Async/await patterns",
        "class_design": "Class and inheritance patterns",
        "function_signature": "Function signature patterns",
        "import_style": "Import organization patterns",
        "logging": "Logging patterns",
        "configuration": "Configuration management patterns",
    }

    def __init__(self):
        """Initialize pattern store."""
        self.db_manager = get_db_manager()

    def store_pattern(
        self,
        pattern_type: str,
        name: str,
        example_code: str,
        description: Optional[str] = None,
        signature: Optional[str] = None,
        language: str = "python",
        project_id: Optional[str] = None,
    ) -> UUID:
        """Store a code pattern.

        Args:
            pattern_type: Type of pattern (api_design, error_handling, etc.)
            name: Pattern name
            example_code: Example code demonstrating the pattern
            description: Optional description
            signature: Pattern signature/template
            language: Programming language
            project_id: Optional project identifier

        Returns:
            UUID of the created pattern
        """
        with self.db_manager.get_session() as session:
            # Check if similar pattern exists
            existing = session.query(CodePattern).filter(
                CodePattern.pattern_type == pattern_type,
                CodePattern.name == name,
                CodePattern.project_id == project_id,
            ).first()

            if existing:
                # Update usage count
                existing.usage_count += 1
                existing.example_code = example_code  # Update with latest example
                session.commit()
                return existing.id

            # Create new pattern
            pattern = CodePattern(
                id=uuid4(),
                pattern_type=pattern_type,
                name=name,
                description=description,
                example_code=example_code,
                signature=signature,
                language=language,
                project_id=project_id,
                usage_count=1,
                files_using=[],
                user_preference_score=0.0,
            )

            session.add(pattern)
            session.commit()
            return pattern.id

    def get_pattern(self, pattern_id: UUID) -> Optional[CodePattern]:
        """Retrieve a pattern by ID.

        Args:
            pattern_id: UUID of the pattern

        Returns:
            CodePattern object or None
        """
        with self.db_manager.get_session() as session:
            return session.query(CodePattern).filter(
                CodePattern.id == pattern_id
            ).first()

    def get_patterns(
        self,
        pattern_type: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 50,
        min_usage_count: int = 1,
    ) -> List[CodePattern]:
        """Get patterns with optional filtering.

        Args:
            pattern_type: Optional pattern type filter
            project_id: Optional project filter
            limit: Maximum number of patterns to return
            min_usage_count: Minimum usage count filter

        Returns:
            List of CodePattern objects
        """
        with self.db_manager.get_session() as session:
            q = session.query(CodePattern)

            if pattern_type:
                q = q.filter(CodePattern.pattern_type == pattern_type)
            if project_id:
                q = q.filter(CodePattern.project_id == project_id)
            if min_usage_count > 1:
                q = q.filter(CodePattern.usage_count >= min_usage_count)

            return q.order_by(desc(CodePattern.usage_count)).limit(limit).all()

    def update_pattern_usage(
        self,
        pattern_id: UUID,
        file_path: str,
        increment_count: bool = True
    ) -> bool:
        """Update pattern usage statistics.

        Args:
            pattern_id: UUID of the pattern
            file_path: File using this pattern
            increment_count: Whether to increment usage count

        Returns:
            True if updated successfully
        """
        with self.db_manager.get_session() as session:
            pattern = session.query(CodePattern).filter(
                CodePattern.id == pattern_id
            ).first()

            if not pattern:
                return False

            # Update files_using
            files_using = pattern.files_using or []
            if file_path not in files_using:
                files_using.append(file_path)
                pattern.files_using = files_using

            if increment_count:
                pattern.usage_count += 1

            session.commit()
            return True

    def extract_patterns_from_file(
        self,
        file_path: str,
        content: str,
        project_id: Optional[str] = None,
    ) -> List[UUID]:
        """Extract patterns from a Python file.

        Args:
            file_path: Path to the file
            content: File content
            project_id: Optional project identifier

        Returns:
            List of pattern UUIDs extracted
        """
        pattern_ids = []

        try:
            tree = ast.parse(content)

            # Extract different pattern types
            pattern_ids.extend(self._extract_function_patterns(tree, content, file_path, project_id))
            pattern_ids.extend(self._extract_class_patterns(tree, content, file_path, project_id))
            pattern_ids.extend(self._extract_error_handling_patterns(tree, content, file_path, project_id))
            pattern_ids.extend(self._extract_import_patterns(tree, content, file_path, project_id))

        except SyntaxError:
            pass  # Skip files with syntax errors

        return pattern_ids

    def _extract_function_patterns(
        self,
        tree: ast.AST,
        content: str,
        file_path: str,
        project_id: Optional[str]
    ) -> List[UUID]:
        """Extract function signature patterns."""
        pattern_ids = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Extract function signature
                args = [arg.arg for arg in node.args.args]
                returns = ast.unparse(node.returns) if node.returns else "None"

                signature = f"{node.name}({', '.join(args)}) -> {returns}"

                # Check for async patterns
                if isinstance(node, ast.AsyncFunctionDef):
                    pattern_id = self.store_pattern(
                        pattern_type="async_patterns",
                        name=f"async_{node.name}",
                        example_code=ast.unparse(node),
                        signature=signature,
                        project_id=project_id,
                    )
                    pattern_ids.append(pattern_id)

                # Check for common function patterns
                if node.name.startswith("test_"):
                    pattern_id = self.store_pattern(
                        pattern_type="testing",
                        name="test_function",
                        example_code=ast.unparse(node)[:500],
                        signature=signature,
                        project_id=project_id,
                    )
                    pattern_ids.append(pattern_id)

        return pattern_ids

    def _extract_class_patterns(
        self,
        tree: ast.AST,
        content: str,
        file_path: str,
        project_id: Optional[str]
    ) -> List[UUID]:
        """Extract class design patterns."""
        pattern_ids = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for common class patterns
                base_classes = [ast.unparse(base) for base in node.bases]

                if base_classes:
                    pattern_id = self.store_pattern(
                        pattern_type="class_design",
                        name=f"{node.name}_inheritance",
                        example_code=ast.unparse(node)[:500],
                        description=f"Class inheriting from {', '.join(base_classes)}",
                        project_id=project_id,
                    )
                    pattern_ids.append(pattern_id)

                # Check for dataclass pattern
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                        pattern_id = self.store_pattern(
                            pattern_type="class_design",
                            name="dataclass_pattern",
                            example_code=ast.unparse(node)[:500],
                            project_id=project_id,
                        )
                        pattern_ids.append(pattern_id)

        return pattern_ids

    def _extract_error_handling_patterns(
        self,
        tree: ast.AST,
        content: str,
        file_path: str,
        project_id: Optional[str]
    ) -> List[UUID]:
        """Extract error handling patterns."""
        pattern_ids = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                # Extract try-except pattern
                exception_types = []
                for handler in node.handlers:
                    if handler.type:
                        exception_types.append(ast.unparse(handler.type))

                pattern_id = self.store_pattern(
                    pattern_type="error_handling",
                    name="try_except_pattern",
                    example_code=ast.unparse(node)[:500],
                    description=f"Handles: {', '.join(exception_types)}",
                    project_id=project_id,
                )
                pattern_ids.append(pattern_id)

        return pattern_ids

    def _extract_import_patterns(
        self,
        tree: ast.AST,
        content: str,
        file_path: str,
        project_id: Optional[str]
    ) -> List[UUID]:
        """Extract import organization patterns."""
        pattern_ids = []

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        if imports:
            # Detect import style (group by standard lib, third-party, local)
            import_groups = {
                "stdlib": [],
                "third_party": [],
                "local": [],
            }

            for imp in imports:
                if imp.startswith("."):
                    import_groups["local"].append(imp)
                elif imp in ["os", "sys", "re", "json", "datetime"]:
                    import_groups["stdlib"].append(imp)
                else:
                    import_groups["third_party"].append(imp)

            if any(import_groups.values()):
                pattern_id = self.store_pattern(
                    pattern_type="import_style",
                    name="import_organization",
                    example_code="\n".join(imports[:10]),
                    description=f"Import groups: {', '.join([k for k, v in import_groups.items() if v])}",
                    project_id=project_id,
                )
                pattern_ids.append(pattern_id)

        return pattern_ids

    def extract_patterns_from_directory(
        self,
        directory: str,
        project_id: Optional[str] = None,
        extensions: List[str] = [".py"],
    ) -> Dict[str, int]:
        """Extract patterns from all files in a directory.

        Args:
            directory: Directory to scan
            project_id: Optional project identifier
            extensions: File extensions to process

        Returns:
            Dictionary mapping pattern types to counts
        """
        pattern_counts = defaultdict(int)
        directory_path = Path(directory)

        for ext in extensions:
            for file_path in directory_path.rglob(f"*{ext}"):
                if file_path.is_file():
                    try:
                        content = file_path.read_text()
                        pattern_ids = self.extract_patterns_from_file(
                            str(file_path),
                            content,
                            project_id,
                        )

                        # Count by type
                        for pattern_id in pattern_ids:
                            pattern = self.get_pattern(pattern_id)
                            if pattern:
                                pattern_counts[pattern.pattern_type] += 1

                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")

        return dict(pattern_counts)

    def get_pattern_statistics(self, project_id: Optional[str] = None) -> Dict:
        """Get pattern statistics.

        Args:
            project_id: Optional project filter

        Returns:
            Dictionary with statistics
        """
        with self.db_manager.get_session() as session:
            from sqlalchemy import func

            q = session.query(CodePattern)
            if project_id:
                q = q.filter(CodePattern.project_id == project_id)

            total_patterns = q.count()

            # Pattern type distribution
            type_stats = session.query(
                CodePattern.pattern_type,
                func.count(CodePattern.id)
            ).group_by(CodePattern.pattern_type)

            if project_id:
                type_stats = type_stats.filter(CodePattern.project_id == project_id)

            type_distribution = dict(type_stats.all())

            # Most used patterns
            most_used = q.order_by(desc(CodePattern.usage_count)).limit(10).all()

            return {
                "total_patterns": total_patterns,
                "pattern_types": type_distribution,
                "most_used_patterns": [
                    {
                        "id": str(p.id),
                        "type": p.pattern_type,
                        "name": p.name,
                        "usage_count": p.usage_count,
                    }
                    for p in most_used
                ],
            }

    def delete_unused_patterns(self, min_usage_count: int = 1) -> int:
        """Delete patterns with low usage.

        Args:
            min_usage_count: Minimum usage count to keep

        Returns:
            Number of patterns deleted
        """
        with self.db_manager.get_session() as session:
            deleted_count = session.query(CodePattern).filter(
                CodePattern.usage_count < min_usage_count
            ).delete()

            session.commit()
            return deleted_count
