"""
Dependency Analyzer (Story 2.5)

Builds dependency graphs from ParseResult structures, finds references,
performs impact analysis, and detects cycles.

Design goals:
- Pure-Python, no external services
- Works directly with parsing models (unit-test friendly)
- Can later plug into cross_language analyzer and AST store
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional

from src.parsing.models import ParseResult, SymbolInfo, ClassInfo, ImportInfo


@dataclass(frozen=True)
class DependencyEdge:
    source_file: str
    target_file: str
    relation: str  # e.g., "import", "inheritance", "implementation", "call"
    source_symbol: Optional[str] = None
    target_symbol: Optional[str] = None


class DependencyAnalyzer:
    """Builds dependency graphs and provides analysis helpers."""

    def __init__(self, parse_results: List[ParseResult]):
        self.parse_results = parse_results
        # index by file for quick lookup
        self._by_file: Dict[str, ParseResult] = {str(p.file_path): p for p in parse_results}
        # build edges lazily
        self._edges: Optional[List[DependencyEdge]] = None

    # ---------------- Graph Construction -----------------
    def build_edges(self) -> List[DependencyEdge]:
        if self._edges is not None:
            return self._edges
        edges: List[DependencyEdge] = []
        for p in self.parse_results:
            # imports -> file-to-file
            for imp in p.imports or []:
                target = self._resolve_import_to_path(imp)
                if target:
                    edges.append(DependencyEdge(str(p.file_path), target, "import"))
            # inheritance and implementation
            for cls in p.classes or []:
                for base in cls.base_classes or []:
                    # naive mapping: base class name to file containing class of same name
                    target = self._find_file_defining_class(base)
                    if target and target != str(p.file_path):
                        edges.append(DependencyEdge(str(p.file_path), target, "inheritance", cls.name, base))
                for iface in getattr(cls, 'interfaces', []) or []:
                    target = self._find_file_defining_class(iface)
                    if target and target != str(p.file_path):
                        edges.append(DependencyEdge(str(p.file_path), target, "implementation", cls.name, iface))
            # function calls: skipped for now (SymbolInfo has no call map in current model)
            # This can be enabled when call graph data is available in ParseResult/SymbolInfo
        self._edges = edges
        return edges

    def build_graph(self) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
        """Returns (adj_out, adj_in) maps between files."""
        adj_out: Dict[str, Set[str]] = {}
        adj_in: Dict[str, Set[str]] = {}
        for e in self.build_edges():
            adj_out.setdefault(e.source_file, set()).add(e.target_file)
            adj_in.setdefault(e.target_file, set()).add(e.source_file)
            adj_out.setdefault(e.target_file, set())
            adj_in.setdefault(e.source_file, set())
        return adj_out, adj_in

    # ---------------- Queries -----------------
    def find_references(self, symbol_name: str) -> List[DependencyEdge]:
        """Find edges that reference the given symbol (as target_symbol)."""
        refs: List[DependencyEdge] = []
        for e in self.build_edges():
            if e.target_symbol and e.target_symbol == symbol_name:
                refs.append(e)
        return refs

    def impact_of_change(self, file_path: str) -> Set[str]:
        """Return files that are impacted if file_path changes (transitive dependents)."""
        _, adj_in = self.build_graph()
        impacted: Set[str] = set()
        stack = [file_path]
        while stack:
            node = stack.pop()
            for parent in adj_in.get(node, set()):
                if parent not in impacted:
                    impacted.add(parent)
                    stack.append(parent)
        impacted.discard(file_path)
        return impacted

    def detect_cycles(self) -> List[List[str]]:
        """Detect cycles (file-level) using DFS with recursion stack."""
        adj_out, _ = self.build_graph()
        visited: Set[str] = set()
        stack: Set[str] = set()
        cycles: List[List[str]] = []

        def dfs(node: str, path: List[str]):
            visited.add(node)
            stack.add(node)
            for nxt in adj_out.get(node, set()):
                if nxt not in visited:
                    dfs(nxt, path + [nxt])
                elif nxt in stack:
                    # cycle found; extract segment
                    if nxt in path:
                        idx = path.index(nxt)
                        cycles.append(path[idx:] + [nxt])
            stack.remove(node)

        for n in adj_out.keys():
            if n not in visited:
                dfs(n, [n])
        return cycles

    # ---------------- Helpers -----------------
    def _resolve_import_to_path(self, imp: ImportInfo) -> Optional[str]:
        # naive: map module name to file ending with it; prefer exact module match
        mod = (imp.module or "").replace(".", "/")
        # try exact module.py
        candidate = f"{mod}.py" if mod else None
        if candidate and candidate in self._by_file:
            return candidate
        # search by basename
        for path in self._by_file.keys():
            if path.endswith(f"/{mod}.py") or path.endswith(f"\\{mod}.py") or path.endswith(f"{mod}.py"):
                return path
        return None

    def _find_file_defining_class(self, class_name: str) -> Optional[str]:
        for p in self.parse_results:
            for cls in p.classes or []:
                if cls.name == class_name:
                    return str(p.file_path)
        return None

    def _find_file_defining_symbol(self, symbol_name: str) -> Optional[str]:
        for p in self.parse_results:
            for s in p.symbols or []:
                if s.name == symbol_name:
                    return str(p.file_path)
        return None

