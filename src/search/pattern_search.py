"""
Pattern Search Service (Production)

Provides high-level APIs for Tree-sitter pattern search over code, with
caching and multi-language support.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import hashlib

from src.research.query_patterns import TreeSitterQueryEngine, QueryPattern
from src.parsing.parser import detect_language

logger = logging.getLogger(__name__)


@dataclass
class PatternSearchRequest:
    directory: Optional[Path] = None
    code: Optional[str] = None
    language: Optional[str] = None
    patterns: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    include_globs: Optional[List[str]] = None
    exclude_globs: Optional[List[str]] = None
    max_files: int = 500


@dataclass
class PatternSearchResult:
    pattern_name: str
    language: str
    file_path: str
    start_line: int
    end_line: int
    snippet: str
    captures: Dict[str, str]


class PatternSearchService:
    def __init__(self):
        self.engine = TreeSitterQueryEngine(max_result_cache=512)
        self._compiled_by_lang: Dict[str, List[QueryPattern]] = {}
        self._file_cache: Dict[Tuple[str, str, str], List[PatternSearchResult]] = {}
        self._max_file_cache = 1024

    def _hash(self, s: str) -> str:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def _list_files(
        self,
        root: Path,
        include: Optional[List[str]],
        exclude: Optional[List[str]],
        max_files: int,
    ) -> List[Path]:
        import fnmatch

        files: List[Path] = []
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            lang = detect_language(p)
            if not lang:
                continue
            # include/exclude filters
            rel = str(p.relative_to(root))
            if include and not any(fnmatch.fnmatch(rel, pat) for pat in include):
                continue
            if exclude and any(fnmatch.fnmatch(rel, pat) for pat in exclude):
                continue
            files.append(p)
            if len(files) >= max_files:
                break
        return files

    def _get_patterns(
        self, languages: Optional[List[str]], names: Optional[List[str]]
    ) -> Dict[str, List[QueryPattern]]:
        patterns_by_lang: Dict[str, List[QueryPattern]] = {}
        selected_langs = languages or list(self.engine.get_all_patterns().keys())
        for lang in selected_langs:
            pats = self.engine.get_patterns_for_language(lang)
            if names:
                pats = [p for p in pats if p.name in names]
            if pats:
                patterns_by_lang[lang] = pats
        return patterns_by_lang

    def search_code(
        self, language: str, code: str, patterns: Optional[List[str]] = None
    ) -> List[PatternSearchResult]:
        results: List[PatternSearchResult] = []
        patterns_by_lang = self._get_patterns([language], patterns)
        for lang, pats in patterns_by_lang.items():
            for pat in pats:
                matches = self.engine.execute_query(pat, code, file_path="snippet")
                for m in matches:
                    results.append(
                        PatternSearchResult(
                            pattern_name=m.pattern_name,
                            language=lang,
                            file_path=m.file_path,
                            start_line=m.start_line,
                            end_line=m.end_line,
                            snippet=m.matched_text,
                            captures=m.captures,
                        )
                    )
        return results

    def search_directory(
        self,
        root: Path,
        patterns: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        include_globs: Optional[List[str]] = None,
        exclude_globs: Optional[List[str]] = None,
        max_files: int = 500,
    ) -> List[PatternSearchResult]:
        results: List[PatternSearchResult] = []
        root = root.resolve()
        files = self._list_files(root, include_globs, exclude_globs, max_files)
        patterns_by_lang = self._get_patterns(languages, patterns)

        for path in files:
            try:
                code = path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Skip unreadable file {path}: {e}")
                continue
            lang = detect_language(path)
            if not lang:
                continue
            lang_str = lang.value
            pats = patterns_by_lang.get(lang_str)
            if not pats:
                continue
            file_hash = self._hash(code)
            for pat in pats:
                cache_key = (lang_str, pat.name, file_hash)
                cached = self._file_cache.get(cache_key)
                if cached is not None:
                    results.extend(cached)
                    continue
                matches = self.engine.execute_query(pat, code, file_path=str(path))
                converted: List[PatternSearchResult] = []
                for m in matches:
                    converted.append(
                        PatternSearchResult(
                            pattern_name=m.pattern_name,
                            language=lang_str,
                            file_path=str(path),
                            start_line=m.start_line,
                            end_line=m.end_line,
                            snippet=m.matched_text,
                            captures=m.captures,
                        )
                    )
                self._file_cache[cache_key] = converted
                if len(self._file_cache) > self._max_file_cache:
                    # random eviction
                    self._file_cache.pop(next(iter(self._file_cache)))
                results.extend(converted)
        return results


_service: Optional[PatternSearchService] = None


def get_pattern_search_service() -> PatternSearchService:
    global _service
    if _service is None:
        _service = PatternSearchService()
    return _service
