"""
Context Gathering Engine - Epic 2

Gathers context from 6 sources in parallel:
1. Current Context (current file, selection, open files)
2. Code Context (related code, dependencies, tests)
3. Architectural Context (schemas, configs, dependency graph)
4. Historical Context (git log, blame, recent commits)
5. Team Context (CODEOWNERS, experts, patterns)
6. External Context (GitHub issues, Jira tickets - optional)

Components:
- CurrentContextGatherer
- CodeContextGatherer
- ArchitecturalContextGatherer
- HistoricalContextGatherer
- TeamContextGatherer
- ExternalContextGatherer
- ContextGatherer (orchestrator)
- ContextCache
"""

import asyncio
import hashlib
import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class UserContext:
    """User's current context"""
    workspace_path: str
    current_file: Optional[str] = None
    selected_region: Optional[dict] = None  # {'text': str, 'lines': tuple}
    open_files: List[str] = field(default_factory=list)
    active_project: Optional[str] = None


@dataclass
class ContextItem:
    """Individual piece of context"""
    type: str  # 'file', 'selection', 'dependency', 'commit', etc.
    content: Any
    priority: float  # 0.0-10.0
    source: str  # 'current', 'code', 'architecture', 'history', 'team', 'external'
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ContextChunk:
    """Collection of context items from one source"""
    source: str
    items: List[ContextItem] = field(default_factory=list)

    def add(self, type: str, content: Any, priority: float, **metadata):
        """Add a context item"""
        self.items.append(ContextItem(
            type=type,
            content=content,
            priority=priority,
            source=self.source,
            metadata=metadata
        ))


@dataclass
class RawContext:
    """All gathered context before ranking/selection"""
    chunks: List[ContextChunk] = field(default_factory=list)
    total_items: int = 0

    def merge(self, chunk: ContextChunk):
        """Merge a context chunk"""
        self.chunks.append(chunk)
        self.total_items += len(chunk.items)


class CurrentContextGatherer:
    """
    Gather context about what user is currently working on

    Returns:
    - Current file content
    - Selected region
    - Open files in IDE
    """

    async def gather(self, user_context: UserContext) -> ContextChunk:
        """
        Gather current context

        Args:
            user_context: Current user context

        Returns:
            ContextChunk with current context items
        """
        context = ContextChunk(source='current')

        # Current file
        if user_context.current_file:
            file_content = await self._read_file(
                user_context.workspace_path,
                user_context.current_file
            )
            if file_content:
                context.add(
                    type='file',
                    content=file_content,
                    priority=10.0,  # HIGHEST priority
                    path=user_context.current_file
                )

        # Selected region
        if user_context.selected_region:
            context.add(
                type='selection',
                content=user_context.selected_region.get('text', ''),
                priority=10.0,
                lines=user_context.selected_region.get('lines', (0, 0))
            )

        # Open files in IDE
        for open_file in user_context.open_files:
            file_content = await self._read_file(
                user_context.workspace_path,
                open_file
            )
            if file_content:
                context.add(
                    type='open_file',
                    content=file_content,
                    priority=5.0,  # HIGH priority
                    path=open_file
                )

        return context

    async def _read_file(self, workspace_path: str, file_path: str) -> Optional[str]:
        """Read file content"""
        try:
            full_path = os.path.join(workspace_path, file_path)
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return None


class CodeContextGatherer:
    """
    Gather related code context using intelligent search

    Returns:
    - File dependencies (imports)
    - Reverse dependencies (who imports this file)
    - Test files
    - Similar code patterns
    """

    async def gather(self, entities: List, user_context: UserContext) -> ContextChunk:
        """
        Gather code context

        Args:
            entities: Extracted entities from prompt
            user_context: Current user context

        Returns:
            ContextChunk with code context items
        """
        context = ContextChunk(source='code')

        for entity in entities:
            # Import EntityType if available
            try:
                from src.prompt.analyzer import EntityType
                is_file = entity.type == EntityType.FILE
                is_identifier = entity.type == EntityType.IDENTIFIER
            except ImportError:
                is_file = entity.type == "FILE"
                is_identifier = entity.type == "IDENTIFIER"

            if is_file:
                # Get file content
                file_content = await self._read_file(
                    user_context.workspace_path,
                    entity.text
                )
                if file_content:
                    context.add(
                        type='file',
                        content=file_content,
                        priority=8.0,
                        path=entity.text
                    )

                # Get dependencies
                dependencies = await self._get_dependencies(
                    user_context.workspace_path,
                    entity.text
                )
                for dep_path, dep_content in dependencies:
                    context.add(
                        type='dependency',
                        content=dep_content,
                        priority=6.0,
                        path=dep_path
                    )

                # Get test files
                test_files = await self._find_test_files(
                    user_context.workspace_path,
                    entity.text
                )
                for test_path, test_content in test_files:
                    context.add(
                        type='test',
                        content=test_content,
                        priority=7.0,
                        path=test_path
                    )

            elif is_identifier:
                # Search for identifier in codebase
                search_results = await self._search_identifier(
                    user_context.workspace_path,
                    entity.text
                )
                for result in search_results[:5]:  # Top 5 results
                    context.add(
                        type='search_result',
                        content=result['snippet'],
                        priority=6.0,
                        path=result['file'],
                        line=result.get('line', 0)
                    )

        return context

    async def _read_file(self, workspace_path: str, file_path: str) -> Optional[str]:
        """Read file content"""
        try:
            full_path = os.path.join(workspace_path, file_path)
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return None

    async def _get_dependencies(self, workspace_path: str, file_path: str) -> List[tuple]:
        """Get file dependencies by parsing imports"""
        dependencies = []

        try:
            full_path = os.path.join(workspace_path, file_path)
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Simple import parsing (works for Python)
            import_patterns = [
                r'from\s+([\w.]+)\s+import',
                r'import\s+([\w.]+)',
            ]

            import re
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Convert module name to file path
                    dep_path = match.replace('.', '/') + '.py'
                    dep_content = await self._read_file(workspace_path, dep_path)
                    if dep_content:
                        dependencies.append((dep_path, dep_content))

        except Exception:
            pass

        return dependencies[:5]  # Limit to top 5 dependencies

    async def _find_test_files(self, workspace_path: str, file_path: str) -> List[tuple]:
        """Find test files for a given file"""
        test_files = []

        try:
            # Common test file naming patterns
            base_name = os.path.basename(file_path)
            name_without_ext = os.path.splitext(base_name)[0]

            test_patterns = [
                f'test_{name_without_ext}.py',
                f'{name_without_ext}_test.py',
                f'tests/test_{name_without_ext}.py',
                f'tests/{name_without_ext}_test.py',
            ]

            for pattern in test_patterns:
                test_path = os.path.join(os.path.dirname(file_path), pattern)
                test_content = await self._read_file(workspace_path, test_path)
                if test_content:
                    test_files.append((test_path, test_content))

        except Exception:
            pass

        return test_files

    async def _search_identifier(self, workspace_path: str, identifier: str) -> List[dict]:
        """Search for identifier in codebase using grep"""
        results = []

        try:
            # Use ripgrep if available, fallback to grep
            try:
                cmd = ['rg', '-n', '-i', identifier, workspace_path]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                output = stdout.decode('utf-8', errors='ignore')
            except FileNotFoundError:
                # Fallback to grep
                cmd = ['grep', '-rn', '-i', identifier, workspace_path]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                output = stdout.decode('utf-8', errors='ignore')

            # Parse results
            for line in output.split('\n')[:20]:  # Limit to 20 lines
                if ':' in line:
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        file_path = parts[0].replace(workspace_path + '/', '')
                        line_num = parts[1]
                        snippet = parts[2].strip()
                        results.append({
                            'file': file_path,
                            'line': line_num,
                            'snippet': snippet
                        })

        except Exception:
            pass

        return results


class ArchitecturalContextGatherer:
    """
    Gather architectural context

    Returns:
    - Project dependency graph (from package files)
    - API schemas (OpenAPI, GraphQL)
    - Database schemas
    - Configuration files
    """

    CONFIG_FILES = [
        'package.json', 'requirements.txt', 'Pipfile', 'pyproject.toml',
        'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
        'docker-compose.yml', '.env.example', 'config.yaml', 'config.json'
    ]

    async def gather(self, entities: List, user_context: UserContext) -> ContextChunk:
        """Gather architectural context"""
        context = ContextChunk(source='architecture')

        # Find and include configuration files
        for config_file in self.CONFIG_FILES:
            content = await self._read_file(
                user_context.workspace_path,
                config_file
            )
            if content:
                context.add(
                    type='config',
                    content=content,
                    priority=5.0,
                    path=config_file
                )

        # Look for schema files
        schema_files = await self._find_schema_files(user_context.workspace_path)
        for schema_path, schema_content in schema_files[:3]:  # Top 3 schemas
            context.add(
                type='schema',
                content=schema_content,
                priority=6.0,
                path=schema_path
            )

        return context

    async def _read_file(self, workspace_path: str, file_path: str) -> Optional[str]:
        """Read file content"""
        try:
            full_path = os.path.join(workspace_path, file_path)
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return None

    async def _find_schema_files(self, workspace_path: str) -> List[tuple]:
        """Find schema files (OpenAPI, GraphQL, DB schemas)"""
        schema_files = []
        schema_patterns = ['*.graphql', '*.schema.json', 'openapi.yaml', 'swagger.yaml']

        try:
            for pattern in schema_patterns:
                for file_path in Path(workspace_path).rglob(pattern):
                    if file_path.is_file() and os.path.getsize(file_path) < 100000:  # < 100KB
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            rel_path = str(file_path.relative_to(workspace_path))
                            schema_files.append((rel_path, content))
        except Exception:
            pass

        return schema_files


class HistoricalContextGatherer:
    """
    Gather historical context from git

    Returns:
    - Recent commits (last 24 hours)
    - Git blame for files
    - Related commits (same files)
    """

    async def gather(self, entities: List, user_context: UserContext) -> ContextChunk:
        """Gather historical context"""
        context = ContextChunk(source='history')

        # Get recent commits
        recent_commits = await self._get_recent_commits(
            user_context.workspace_path,
            hours=24
        )
        for commit in recent_commits[:10]:  # Top 10 commits
            context.add(
                type='recent_commit',
                content=commit,
                priority=6.0,
                commit_hash=commit.get('hash'),
                author=commit.get('author'),
                message=commit.get('message')
            )

        # Get git blame for file entities
        for entity in entities:
            try:
                from src.prompt.analyzer import EntityType
                is_file = entity.type == EntityType.FILE
            except ImportError:
                is_file = entity.type == "FILE"

            if is_file:
                blame = await self._get_git_blame(
                    user_context.workspace_path,
                    entity.text
                )
                if blame:
                    context.add(
                        type='git_blame',
                        content=blame,
                        priority=5.0,
                        path=entity.text
                    )

        return context

    async def _get_recent_commits(self, workspace_path: str, hours: int = 24) -> List[dict]:
        """Get commits from last N hours"""
        commits = []

        try:
            since = datetime.now() - timedelta(hours=hours)
            since_str = since.strftime('%Y-%m-%d %H:%M:%S')

            cmd = [
                'git', '-C', workspace_path, 'log',
                f'--since={since_str}',
                '--pretty=format:%H|%an|%ae|%s|%ar',
                '--max-count=20'
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                for line in output.split('\n'):
                    if line.strip():
                        parts = line.split('|')
                        if len(parts) >= 4:
                            commits.append({
                                'hash': parts[0],
                                'author': parts[1],
                                'email': parts[2],
                                'message': parts[3],
                                'time_ago': parts[4] if len(parts) > 4 else ''
                            })

        except Exception:
            pass

        return commits

    async def _get_git_blame(self, workspace_path: str, file_path: str) -> Optional[str]:
        """Get git blame for a file"""
        try:
            cmd = ['git', '-C', workspace_path, 'blame', '--line-porcelain', file_path]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                return stdout.decode('utf-8', errors='ignore')[:5000]  # Limit to 5KB

        except Exception:
            pass

        return None


class TeamContextGatherer:
    """
    Gather team context

    Returns:
    - Code owners (CODEOWNERS file)
    - Expert developers (by commit frequency)
    - Team patterns (stub for now)
    """

    async def gather(self, entities: List, user_context: UserContext) -> ContextChunk:
        """Gather team context"""
        context = ContextChunk(source='team')

        # Parse CODEOWNERS file
        codeowners = await self._parse_codeowners(user_context.workspace_path)
        if codeowners:
            context.add(
                type='codeowners',
                content=codeowners,
                priority=5.0
            )

        # Find expert developers for file entities
        for entity in entities:
            try:
                from src.prompt.analyzer import EntityType
                is_file = entity.type == EntityType.FILE
            except ImportError:
                is_file = entity.type == "FILE"

            if is_file:
                experts = await self._find_experts(
                    user_context.workspace_path,
                    entity.text
                )
                if experts:
                    context.add(
                        type='experts',
                        content=experts,
                        priority=4.0,
                        path=entity.text
                    )

        return context

    async def _parse_codeowners(self, workspace_path: str) -> Optional[dict]:
        """Parse CODEOWNERS file"""
        try:
            codeowners_paths = [
                '.github/CODEOWNERS',
                'CODEOWNERS',
                'docs/CODEOWNERS'
            ]

            for path in codeowners_paths:
                full_path = os.path.join(workspace_path, path)
                if os.path.exists(full_path):
                    with open(full_path, 'r') as f:
                        content = f.read()
                        return {'path': path, 'content': content}

        except Exception:
            pass

        return None

    async def _find_experts(self, workspace_path: str, file_path: str) -> Optional[List[dict]]:
        """Find expert developers for a file (by commit frequency)"""
        try:
            cmd = [
                'git', '-C', workspace_path, 'log',
                '--pretty=format:%an|%ae',
                '--', file_path
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                author_counts = defaultdict(int)
                author_emails = {}

                for line in output.split('\n'):
                    if '|' in line:
                        name, email = line.split('|', 1)
                        author_counts[name] += 1
                        author_emails[name] = email

                # Get top 3 contributors
                top_authors = sorted(
                    author_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]

                return [
                    {
                        'name': name,
                        'email': author_emails[name],
                        'commits': count
                    }
                    for name, count in top_authors
                ]

        except Exception:
            pass

        return None


class ExternalContextGatherer:
    """
    Gather external context (GitHub issues, Jira tickets - optional)

    NOTE: This is a stub implementation. External integrations are optional
    and can be disabled via config.
    """

    async def gather(self, entities: List, user_context: UserContext) -> ContextChunk:
        """Gather external context"""
        context = ContextChunk(source='external')

        # Stub: External context gathering would go here
        # This could include:
        # - GitHub issues mentioning files
        # - Jira tickets linked to code
        # - Confluence documentation
        # - Stack Overflow similar errors

        # For now, return empty context
        return context


class ContextCache:
    """
    Cache for gathered context with TTL

    Caches context for 5 minutes to avoid redundant gathering
    """

    def __init__(self, ttl: int = 300):
        """
        Initialize cache

        Args:
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.ttl = ttl
        self.cache: Dict[str, tuple] = {}  # key -> (data, timestamp)

    async def get(self, key: str) -> Optional[RawContext]:
        """Get cached context if not expired"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            age = (datetime.now() - timestamp).total_seconds()
            if age < self.ttl:
                return data

            # Expired, remove from cache
            del self.cache[key]

        return None

    async def set(self, key: str, data: RawContext):
        """Set cached context"""
        self.cache[key] = (data, datetime.now())

    def _make_key(self, prompt_intent, user_context: UserContext) -> str:
        """Generate cache key"""
        # Combine prompt, current file, and workspace
        key_parts = [
            prompt_intent.original_prompt,
            user_context.current_file or '',
            user_context.workspace_path
        ]
        key_str = '|'.join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()


class ContextGatherer:
    """
    Main orchestrator for context gathering

    Coordinates parallel gathering from all 6 sources:
    1. Current context
    2. Code context
    3. Architectural context
    4. Historical context
    5. Team context
    6. External context (optional)
    """

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize context gatherer

        Args:
            config: Optional configuration dict
        """
        self.config = config or {}

        # Initialize all gatherers
        self.current_gatherer = CurrentContextGatherer()
        self.code_gatherer = CodeContextGatherer()
        self.arch_gatherer = ArchitecturalContextGatherer()
        self.history_gatherer = HistoricalContextGatherer()
        self.team_gatherer = TeamContextGatherer()
        self.external_gatherer = ExternalContextGatherer()

        # Initialize cache
        self.cache = ContextCache(ttl=self.config.get('cache_ttl', 300))

    async def gather(self, prompt_intent, user_context: UserContext) -> RawContext:
        """
        Gather context from all relevant sources in parallel

        Args:
            prompt_intent: Analyzed prompt intent
            user_context: Current user context

        Returns:
            RawContext with all gathered context chunks
        """
        # Check cache first
        cache_key = self._make_cache_key(prompt_intent, user_context)
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # Determine which gatherers to use based on context types
        tasks = []

        # Always gather current context
        tasks.append(('current', self.current_gatherer.gather(user_context)))

        # Gather based on selected context types
        if 'code' in prompt_intent.context_types:
            tasks.append((
                'code',
                self.code_gatherer.gather(prompt_intent.entities, user_context)
            ))

        if 'architecture' in prompt_intent.context_types:
            tasks.append((
                'architecture',
                self.arch_gatherer.gather(prompt_intent.entities, user_context)
            ))

        if 'history' in prompt_intent.context_types:
            tasks.append((
                'history',
                self.history_gatherer.gather(prompt_intent.entities, user_context)
            ))

        if 'team' in prompt_intent.context_types:
            tasks.append((
                'team',
                self.team_gatherer.gather(prompt_intent.entities, user_context)
            ))

        if 'external' in prompt_intent.context_types:
            external_enabled = self.config.get('external_enabled', False)
            if external_enabled:
                tasks.append((
                    'external',
                    self.external_gatherer.gather(prompt_intent.entities, user_context)
                ))

        # Gather all in parallel with timeout
        try:
            # Create task list
            gather_tasks = [task for _, task in tasks]

            # Run with 2 second timeout
            results = await asyncio.wait_for(
                asyncio.gather(*gather_tasks, return_exceptions=True),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            # Timeout - return partial results
            results = [None] * len(tasks)

        # Merge results
        raw_context = RawContext()
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Log warning but continue
                continue
            if result:
                raw_context.merge(result)

        # Cache result
        await self.cache.set(cache_key, raw_context)

        return raw_context

    def _make_cache_key(self, prompt_intent, user_context: UserContext) -> str:
        """Generate cache key"""
        key_parts = [
            prompt_intent.original_prompt,
            user_context.current_file or '',
            user_context.workspace_path
        ]
        key_str = '|'.join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
