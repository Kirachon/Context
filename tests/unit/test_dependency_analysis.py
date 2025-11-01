"""
Unit tests for DependencyAnalyzer (Story 2.5)
"""
from src.analysis.dependency_analysis import DependencyAnalyzer, DependencyEdge
from pathlib import Path
from src.parsing.models import ParseResult, SymbolInfo, ClassInfo, ImportInfo, Language


def make_pr(file_path, imports=None, classes=None, symbols=None):
    return ParseResult(
        file_path=Path(file_path),
        language=Language.PYTHON,
        ast_root=None,
        imports=imports or [],
        classes=classes or [],
        symbols=symbols or [],
    )


def test_graph_from_imports_and_inheritance():
    # a.py imports b; class A inherits B
    pr_a = make_pr(
        "a.py",
        imports=[ImportInfo(module="b", items=[])],
        classes=[ClassInfo(name="A", line_start=1, line_end=2, base_classes=["B"], interfaces=[], methods=[])],
    )
    pr_b = make_pr("b.py", classes=[ClassInfo(name="B", line_start=1, line_end=2, base_classes=[], interfaces=[], methods=[])])

    analyzer = DependencyAnalyzer([pr_a, pr_b])
    edges = analyzer.build_edges()
    kinds = {(e.source_file, e.target_file, e.relation) for e in edges}
    assert ("a.py", "b.py", "import") in kinds
    assert ("a.py", "b.py", "inheritance") in kinds


def test_cycle_detection_mutual_imports():
    pr_a = make_pr("a.py", imports=[ImportInfo(module="b", items=[])])
    pr_b = make_pr("b.py", imports=[ImportInfo(module="a", items=[])])

    analyzer = DependencyAnalyzer([pr_a, pr_b])
    cycles = analyzer.detect_cycles()
    # Expect a cycle containing both files
    joined = ["->".join(c) for c in cycles]
    assert any("a.py" in c and "b.py" in c for c in joined)


def test_impact_of_change_depends_on_transitive():
    # a.py -> b.py -> c.py; change in c.py should impact b.py and a.py
    pr_a = make_pr("a.py", imports=[ImportInfo(module="b", items=[])])
    pr_b = make_pr("b.py", imports=[ImportInfo(module="c", items=[])])
    pr_c = make_pr("c.py")

    analyzer = DependencyAnalyzer([pr_a, pr_b, pr_c])
    impacted = analyzer.impact_of_change("c.py")
    assert impacted == {"b.py", "a.py"}

