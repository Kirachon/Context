"""User Preference Learning: Learn coding preferences from git history.

Epic 8: User Preference Learning
- Extract coding style from git history
- Learn naming conventions and formatting preferences
- Track preferred libraries and frameworks
- Support active learning from user feedback
"""

import ast
import re
import subprocess
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Optional, Set

from sqlalchemy import func

from src.memory.database import get_db_manager
from src.memory.models import UserPreference


class PreferenceStore:
    """Store and learn user coding preferences."""

    def __init__(self):
        """Initialize preference store."""
        self.db_manager = get_db_manager()

    def get_user_preferences(self, user_id: str) -> Optional[UserPreference]:
        """Retrieve user preferences.

        Args:
            user_id: User identifier

        Returns:
            UserPreference object or None
        """
        with self.db_manager.get_session() as session:
            return session.query(UserPreference).filter(
                UserPreference.user_id == user_id
            ).first()

    def learn_from_git_history(
        self,
        user_id: str,
        repo_path: str,
        max_commits: int = 100,
    ) -> Dict:
        """Learn user preferences from git commit history.

        Args:
            user_id: User identifier (typically git email or name)
            repo_path: Path to git repository
            max_commits: Maximum number of commits to analyze

        Returns:
            Dictionary with learned preferences
        """
        # Get user's commits
        commits = self._get_user_commits(repo_path, user_id, max_commits)

        if not commits:
            return {"error": "No commits found for user"}

        # Analyze code style from commits
        code_style = self._analyze_code_style(repo_path, commits)
        preferred_libraries = self._analyze_library_preferences(repo_path, commits)
        testing_approach = self._analyze_testing_approach(repo_path, commits)
        documentation_level = self._analyze_documentation_level(repo_path, commits)
        language_prefs = self._analyze_language_preferences(repo_path, commits)

        # Calculate confidence based on sample size
        confidence_score = min(1.0, len(commits) / 50.0)  # Full confidence at 50+ commits

        # Store or update preferences
        with self.db_manager.get_session() as session:
            prefs = session.query(UserPreference).filter(
                UserPreference.user_id == user_id
            ).first()

            if prefs:
                # Update existing preferences
                prefs.code_style = code_style
                prefs.preferred_libraries = preferred_libraries
                prefs.testing_approach = testing_approach
                prefs.documentation_level = documentation_level
                prefs.language_preferences = language_prefs
                prefs.confidence_score = confidence_score
                prefs.sample_size = len(commits)
            else:
                # Create new preferences
                prefs = UserPreference(
                    user_id=user_id,
                    code_style=code_style,
                    preferred_libraries=preferred_libraries,
                    testing_approach=testing_approach,
                    documentation_level=documentation_level,
                    language_preferences=language_prefs,
                    confidence_score=confidence_score,
                    sample_size=len(commits),
                )
                session.add(prefs)

            session.commit()

        return {
            "user_id": user_id,
            "commits_analyzed": len(commits),
            "confidence_score": confidence_score,
            "code_style": code_style,
            "preferred_libraries": preferred_libraries,
            "testing_approach": testing_approach,
            "documentation_level": documentation_level,
        }

    def _get_user_commits(
        self,
        repo_path: str,
        user_id: str,
        max_commits: int
    ) -> List[Dict]:
        """Get commits by a specific user.

        Args:
            repo_path: Repository path
            user_id: User identifier (email or name)
            max_commits: Maximum commits to retrieve

        Returns:
            List of commit dictionaries
        """
        try:
            # Try matching by email first
            cmd = [
                'git', 'log',
                f'--author={user_id}',
                f'-n', str(max_commits),
                '--pretty=format:%H|%an|%ae|%s',
                '--name-only'
            ]

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return []

            # Parse output
            commits = []
            current_commit = None

            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    if current_commit:
                        commits.append(current_commit)
                        current_commit = None
                    continue

                if '|' in line:
                    # Commit header
                    parts = line.split('|')
                    current_commit = {
                        'hash': parts[0],
                        'author_name': parts[1],
                        'author_email': parts[2],
                        'subject': parts[3] if len(parts) > 3 else '',
                        'files': []
                    }
                elif current_commit:
                    # File name
                    current_commit['files'].append(line)

            if current_commit:
                commits.append(current_commit)

            return commits

        except Exception as e:
            print(f"Error getting commits: {e}")
            return []

    def _analyze_code_style(self, repo_path: str, commits: List[Dict]) -> Dict:
        """Analyze code style preferences from commits.

        Args:
            repo_path: Repository path
            commits: List of commits

        Returns:
            Dictionary with code style preferences
        """
        indentation_styles = []
        naming_conventions = defaultdict(list)
        quote_styles = []
        line_lengths = []

        for commit in commits[:20]:  # Analyze first 20 commits
            for file_path in commit['files']:
                if not file_path.endswith('.py'):
                    continue

                try:
                    # Get file content at this commit
                    cmd = ['git', 'show', f"{commit['hash']}:{file_path}"]
                    result = subprocess.run(
                        cmd,
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )

                    if result.returncode == 0:
                        content = result.stdout
                        indentation_styles.append(self._detect_indentation(content))
                        naming_conventions['functions'].extend(
                            self._extract_function_names(content)
                        )
                        naming_conventions['variables'].extend(
                            self._extract_variable_names(content)
                        )
                        quote_styles.append(self._detect_quote_style(content))
                        line_lengths.extend(self._analyze_line_lengths(content))

                except Exception:
                    continue

        # Aggregate preferences
        indent_style = max(set(indentation_styles), key=indentation_styles.count) if indentation_styles else "4_spaces"

        # Determine naming convention (snake_case vs camelCase)
        function_style = self._determine_naming_style(naming_conventions['functions'])
        variable_style = self._determine_naming_style(naming_conventions['variables'])

        quote_style = max(set(quote_styles), key=quote_styles.count) if quote_styles else "double"

        avg_line_length = sum(line_lengths) / len(line_lengths) if line_lengths else 80

        return {
            "indentation": indent_style,
            "naming_convention": {
                "functions": function_style,
                "variables": variable_style,
            },
            "quote_style": quote_style,
            "max_line_length": int(avg_line_length),
        }

    def _detect_indentation(self, content: str) -> str:
        """Detect indentation style (tabs vs spaces, and size)."""
        lines = content.split('\n')
        indents = []

        for line in lines:
            if line and line[0] in [' ', '\t']:
                if line[0] == '\t':
                    return "tabs"
                else:
                    # Count leading spaces
                    spaces = len(line) - len(line.lstrip(' '))
                    if spaces > 0:
                        indents.append(spaces)

        if indents:
            # Find most common indentation level
            common_indent = Counter(indents).most_common(1)[0][0]
            return f"{common_indent}_spaces"

        return "4_spaces"  # Default

    def _extract_function_names(self, content: str) -> List[str]:
        """Extract function names from Python code."""
        try:
            tree = ast.parse(content)
            names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    names.append(node.name)
            return names
        except:
            return []

    def _extract_variable_names(self, content: str) -> List[str]:
        """Extract variable names from Python code."""
        try:
            tree = ast.parse(content)
            names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            names.append(target.id)
            return names
        except:
            return []

    def _determine_naming_style(self, names: List[str]) -> str:
        """Determine if names use snake_case or camelCase."""
        if not names:
            return "snake_case"

        snake_case_count = sum(1 for name in names if '_' in name and name.islower())
        camel_case_count = sum(1 for name in names if any(c.isupper() for c in name[1:]))

        return "snake_case" if snake_case_count >= camel_case_count else "camelCase"

    def _detect_quote_style(self, content: str) -> str:
        """Detect preference for single vs double quotes."""
        single_quotes = content.count("'") - content.count("\\'")
        double_quotes = content.count('"') - content.count('\\"')

        return "single" if single_quotes > double_quotes else "double"

    def _analyze_line_lengths(self, content: str) -> List[int]:
        """Analyze line length distribution."""
        lines = content.split('\n')
        return [len(line) for line in lines if line.strip()]

    def _analyze_library_preferences(
        self,
        repo_path: str,
        commits: List[Dict]
    ) -> Dict:
        """Analyze preferred libraries from imports.

        Args:
            repo_path: Repository path
            commits: List of commits

        Returns:
            Dictionary mapping categories to preferred libraries
        """
        library_usage = defaultdict(int)

        for commit in commits[:20]:
            for file_path in commit['files']:
                if not file_path.endswith('.py'):
                    continue

                try:
                    cmd = ['git', 'show', f"{commit['hash']}:{file_path}"]
                    result = subprocess.run(
                        cmd,
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )

                    if result.returncode == 0:
                        # Extract imports
                        for line in result.stdout.split('\n'):
                            if line.strip().startswith('import ') or line.strip().startswith('from '):
                                # Extract library name
                                match = re.match(r'(?:from|import)\s+([a-zA-Z0-9_]+)', line)
                                if match:
                                    library_usage[match.group(1)] += 1

                except Exception:
                    continue

        # Categorize libraries
        categories = {
            "testing": ["pytest", "unittest", "mock", "nose"],
            "web": ["flask", "django", "fastapi", "requests", "httpx"],
            "async": ["asyncio", "aiohttp", "trio"],
            "data": ["pandas", "numpy", "sqlalchemy"],
            "ml": ["tensorflow", "pytorch", "sklearn", "transformers"],
        }

        preferences = {}
        for category, libs in categories.items():
            for lib in libs:
                if lib in library_usage:
                    preferences[category] = lib
                    break

        return preferences

    def _analyze_testing_approach(self, repo_path: str, commits: List[Dict]) -> str:
        """Determine testing approach (unit, integration, TDD, etc.)."""
        test_patterns = {
            "unit": ["test_", "Test", "unittest"],
            "integration": ["integration", "e2e", "end_to_end"],
            "pytest": ["pytest", "conftest.py"],
            "tdd": ["test_"],  # If tests come before implementation
        }

        pattern_counts = defaultdict(int)

        for commit in commits[:20]:
            for file_path in commit['files']:
                for approach, patterns in test_patterns.items():
                    for pattern in patterns:
                        if pattern in file_path or pattern in commit['subject']:
                            pattern_counts[approach] += 1

        if pattern_counts:
            return max(pattern_counts, key=pattern_counts.get)

        return "unit"  # Default

    def _analyze_documentation_level(self, repo_path: str, commits: List[Dict]) -> str:
        """Determine documentation level (minimal, moderate, extensive)."""
        doc_indicators = {
            "docstring": 0,
            "comments": 0,
            "markdown": 0,
        }

        for commit in commits[:10]:
            for file_path in commit['files']:
                try:
                    if file_path.endswith('.py'):
                        cmd = ['git', 'show', f"{commit['hash']}:{file_path}"]
                        result = subprocess.run(
                            cmd,
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )

                        if result.returncode == 0:
                            content = result.stdout
                            doc_indicators["docstring"] += content.count('"""') + content.count("'''")
                            doc_indicators["comments"] += content.count('#')

                    elif file_path.endswith('.md'):
                        doc_indicators["markdown"] += 1

                except Exception:
                    continue

        # Determine level based on indicators
        total_indicators = sum(doc_indicators.values())
        if total_indicators > 50:
            return "extensive"
        elif total_indicators > 20:
            return "moderate"
        else:
            return "minimal"

    def _analyze_language_preferences(
        self,
        repo_path: str,
        commits: List[Dict]
    ) -> Dict:
        """Analyze preferences by programming language."""
        language_stats = defaultdict(lambda: {
            "file_count": 0,
            "patterns": [],
        })

        for commit in commits[:20]:
            for file_path in commit['files']:
                # Determine language by extension
                ext = Path(file_path).suffix
                lang_map = {
                    ".py": "python",
                    ".js": "javascript",
                    ".ts": "typescript",
                    ".java": "java",
                    ".go": "go",
                    ".rs": "rust",
                }

                lang = lang_map.get(ext)
                if lang:
                    language_stats[lang]["file_count"] += 1

        return dict(language_stats)

    def update_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: any,
        project_id: Optional[str] = None,
    ) -> bool:
        """Update a specific user preference (active learning).

        Args:
            user_id: User identifier
            preference_key: Key to update (e.g., "code_style.indentation")
            preference_value: New value
            project_id: Optional project-specific override

        Returns:
            True if updated successfully
        """
        with self.db_manager.get_session() as session:
            prefs = session.query(UserPreference).filter(
                UserPreference.user_id == user_id
            ).first()

            if not prefs:
                # Create new preferences
                prefs = UserPreference(
                    user_id=user_id,
                    code_style={},
                    preferred_libraries={},
                    language_preferences={},
                    project_preferences={},
                )
                session.add(prefs)

            # Update preference
            if project_id:
                # Project-specific override
                if not prefs.project_preferences:
                    prefs.project_preferences = {}
                if project_id not in prefs.project_preferences:
                    prefs.project_preferences[project_id] = {}
                prefs.project_preferences[project_id][preference_key] = preference_value
            else:
                # Global preference
                keys = preference_key.split('.')
                if keys[0] == "code_style":
                    if not prefs.code_style:
                        prefs.code_style = {}
                    prefs.code_style[keys[1] if len(keys) > 1 else preference_key] = preference_value
                elif keys[0] == "preferred_libraries":
                    if not prefs.preferred_libraries:
                        prefs.preferred_libraries = {}
                    prefs.preferred_libraries[keys[1] if len(keys) > 1 else preference_key] = preference_value

            session.commit()
            return True

    def get_all_preferences(self) -> List[UserPreference]:
        """Get all user preferences.

        Returns:
            List of all UserPreference objects
        """
        with self.db_manager.get_session() as session:
            return session.query(UserPreference).all()
