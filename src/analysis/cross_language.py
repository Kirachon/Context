"""
Cross-Language Analysis Engine

Provides advanced code analysis capabilities including dependency tracking,
design pattern recognition, and cross-language relationship mapping.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from src.parsing.models import ParseResult, ClassInfo, ImportInfo, Language

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of design patterns that can be detected."""

    SINGLETON = "singleton"
    FACTORY = "factory"
    OBSERVER = "observer"
    STRATEGY = "strategy"
    DECORATOR = "decorator"
    ADAPTER = "adapter"
    BUILDER = "builder"
    COMMAND = "command"
    FACADE = "facade"
    PROXY = "proxy"
    MVC = "mvc"
    REPOSITORY = "repository"
    SERVICE = "service"
    DAO = "dao"
    ERROR_HANDLING = "error_handling"
    ASYNC_PATTERN = "async_pattern"
    DEPENDENCY_INJECTION = "dependency_injection"


class ArchitecturalLayer(str, Enum):
    """Architectural layers in a codebase."""

    PRESENTATION = "presentation"
    BUSINESS = "business"
    DATA = "data"
    INFRASTRUCTURE = "infrastructure"
    UTILITY = "utility"
    TEST = "test"
    CONFIG = "config"


@dataclass
class DependencyRelation:
    """Represents a dependency relationship between code elements."""

    source_file: str
    source_symbol: str
    target_file: str
    target_symbol: str
    relation_type: str  # import, call, inheritance, composition
    language: str
    confidence: float = 1.0
    line_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_file": self.source_file,
            "source_symbol": self.source_symbol,
            "target_file": self.target_file,
            "target_symbol": self.target_symbol,
            "relation_type": self.relation_type,
            "language": self.language,
            "confidence": self.confidence,
            "line_number": self.line_number,
        }


@dataclass
class PatternMatch:
    """Represents a detected design pattern."""

    pattern_type: PatternType
    confidence: float
    files: List[str]
    symbols: List[str]
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_type": self.pattern_type.value,
            "confidence": self.confidence,
            "files": self.files,
            "symbols": self.symbols,
            "description": self.description,
            "evidence": self.evidence,
        }


@dataclass
class ArchitecturalAnalysis:
    """Results of architectural analysis."""

    layers: Dict[ArchitecturalLayer, List[str]]
    patterns: List[PatternMatch]
    dependencies: List[DependencyRelation]
    complexity_metrics: Dict[str, float]
    language_distribution: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layers": {layer.value: files for layer, files in self.layers.items()},
            "patterns": [pattern.to_dict() for pattern in self.patterns],
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "complexity_metrics": self.complexity_metrics,
            "language_distribution": self.language_distribution,
        }


class CrossLanguageAnalyzer:
    """
    Cross-Language Analysis Engine

    Analyzes code across multiple languages to identify patterns, dependencies,
    and architectural structures.
    """

    def __init__(self):
        """Initialize cross-language analyzer."""
        self.pattern_detectors = {
            PatternType.SINGLETON: self._detect_singleton_pattern,
            PatternType.FACTORY: self._detect_factory_pattern,
            PatternType.OBSERVER: self._detect_observer_pattern,
            PatternType.STRATEGY: self._detect_strategy_pattern,
            PatternType.DECORATOR: self._detect_decorator_pattern,
            PatternType.REPOSITORY: self._detect_repository_pattern,
            PatternType.SERVICE: self._detect_service_pattern,
            PatternType.ERROR_HANDLING: self._detect_error_handling_pattern,
            PatternType.ASYNC_PATTERN: self._detect_async_pattern,
            PatternType.DEPENDENCY_INJECTION: self._detect_dependency_injection_pattern,
        }

        self.stats = {
            "files_analyzed": 0,
            "patterns_detected": 0,
            "dependencies_mapped": 0,
            "cross_language_relations": 0,
        }

        logger.info("CrossLanguageAnalyzer initialized")

    def analyze_codebase(
        self, parse_results: List[ParseResult]
    ) -> ArchitecturalAnalysis:
        """
        Perform comprehensive cross-language analysis of a codebase.

        Args:
            parse_results: List of parse results from different files

        Returns:
            ArchitecturalAnalysis with patterns, dependencies, and metrics
        """
        logger.info(f"Starting cross-language analysis of {len(parse_results)} files")

        # Build dependency graph
        dependencies = self._build_dependency_graph(parse_results)

        # Detect design patterns
        patterns = self._detect_patterns(parse_results)

        # Analyze architectural layers
        layers = self._analyze_architectural_layers(parse_results)

        # Calculate complexity metrics
        complexity_metrics = self._calculate_complexity_metrics(
            parse_results, dependencies
        )

        # Analyze language distribution
        language_distribution = self._analyze_language_distribution(parse_results)

        # Update statistics
        self.stats["files_analyzed"] = len(parse_results)
        self.stats["patterns_detected"] = len(patterns)
        self.stats["dependencies_mapped"] = len(dependencies)
        self.stats["cross_language_relations"] = len(
            [
                dep
                for dep in dependencies
                if self._is_cross_language_dependency(dep, parse_results)
            ]
        )

        analysis = ArchitecturalAnalysis(
            layers=layers,
            patterns=patterns,
            dependencies=dependencies,
            complexity_metrics=complexity_metrics,
            language_distribution=language_distribution,
        )

        logger.info(
            f"Analysis complete: {len(patterns)} patterns, {len(dependencies)} dependencies"
        )
        return analysis

    def _build_dependency_graph(
        self, parse_results: List[ParseResult]
    ) -> List[DependencyRelation]:
        """Build dependency graph from parse results."""
        dependencies = []

        # Create lookup maps for efficient searching
        symbol_map = {}  # symbol_name -> (file_path, symbol_info)
        class_map = {}  # class_name -> (file_path, class_info)

        # Build lookup maps
        for result in parse_results:
            file_path = str(result.file_path)

            # Map symbols
            for symbol in result.symbols:
                key = f"{symbol.name}:{symbol.type}"
                if key not in symbol_map:
                    symbol_map[key] = []
                symbol_map[key].append((file_path, symbol))

            # Map classes
            for class_info in result.classes:
                if class_info.name not in class_map:
                    class_map[class_info.name] = []
                class_map[class_info.name].append((file_path, class_info))

        # Analyze dependencies
        for result in parse_results:
            file_path = str(result.file_path)
            language = result.language.value

            # Import dependencies
            for import_info in result.imports:
                dependencies.extend(
                    self._analyze_import_dependencies(
                        file_path, import_info, language, parse_results
                    )
                )

            # Inheritance dependencies
            for class_info in result.classes:
                dependencies.extend(
                    self._analyze_inheritance_dependencies(
                        file_path, class_info, language, class_map
                    )
                )

            # Function call dependencies (basic analysis)
            dependencies.extend(
                self._analyze_call_dependencies(file_path, result, language, symbol_map)
            )

        return dependencies

    def _analyze_import_dependencies(
        self,
        file_path: str,
        import_info: ImportInfo,
        language: str,
        parse_results: List[ParseResult],
    ) -> List[DependencyRelation]:
        """Analyze import-based dependencies."""
        dependencies = []

        # Find target files that match the import
        for result in parse_results:
            target_file = str(result.file_path)

            # Check if this file could be the import target
            if self._matches_import(import_info, result):
                # Create dependency for each imported item
                if import_info.items:
                    for item in import_info.items:
                        dependencies.append(
                            DependencyRelation(
                                source_file=file_path,
                                source_symbol=f"import:{item}",
                                target_file=target_file,
                                target_symbol=item,
                                relation_type="import",
                                language=language,
                                confidence=0.8,
                                line_number=import_info.line,
                            )
                        )
                else:
                    # Module-level import
                    dependencies.append(
                        DependencyRelation(
                            source_file=file_path,
                            source_symbol=f"import:{import_info.module}",
                            target_file=target_file,
                            target_symbol=import_info.module,
                            relation_type="import",
                            language=language,
                            confidence=0.7,
                            line_number=import_info.line,
                        )
                    )

        return dependencies

    def _analyze_inheritance_dependencies(
        self, file_path: str, class_info: ClassInfo, language: str, class_map: Dict
    ) -> List[DependencyRelation]:
        """Analyze inheritance-based dependencies."""
        dependencies = []

        # Base class dependencies
        for base_class in class_info.base_classes:
            if base_class in class_map:
                for target_file, target_class in class_map[base_class]:
                    if target_file != file_path:  # Don't create self-dependencies
                        dependencies.append(
                            DependencyRelation(
                                source_file=file_path,
                                source_symbol=class_info.name,
                                target_file=target_file,
                                target_symbol=base_class,
                                relation_type="inheritance",
                                language=language,
                                confidence=0.9,
                                line_number=class_info.line_start,
                            )
                        )

        # Interface implementation dependencies
        for interface in class_info.interfaces:
            if interface in class_map:
                for target_file, target_class in class_map[interface]:
                    if target_file != file_path:
                        dependencies.append(
                            DependencyRelation(
                                source_file=file_path,
                                source_symbol=class_info.name,
                                target_file=target_file,
                                target_symbol=interface,
                                relation_type="implements",
                                language=language,
                                confidence=0.9,
                                line_number=class_info.line_start,
                            )
                        )

        return dependencies

    def _analyze_call_dependencies(
        self, file_path: str, result: ParseResult, language: str, symbol_map: Dict
    ) -> List[DependencyRelation]:
        """Analyze function call dependencies (basic implementation)."""
        dependencies = []

        # This is a simplified implementation
        # In a full implementation, we would analyze the AST for function calls

        # For now, we'll look for method calls within classes
        for symbol in result.symbols:
            if symbol.parent_class:
                # This is a method - it depends on its class
                class_key = f"{symbol.parent_class}:class"
                if class_key in symbol_map:
                    for target_file, target_symbol in symbol_map[class_key]:
                        if target_file != file_path:
                            dependencies.append(
                                DependencyRelation(
                                    source_file=file_path,
                                    source_symbol=symbol.name,
                                    target_file=target_file,
                                    target_symbol=symbol.parent_class,
                                    relation_type="composition",
                                    language=language,
                                    confidence=0.8,
                                    line_number=symbol.line_start,
                                )
                            )

        return dependencies

    def _matches_import(self, import_info: ImportInfo, result: ParseResult) -> bool:
        """Check if a parse result matches an import statement."""
        file_path = result.file_path

        # Simple heuristic: check if module name matches file/directory structure
        module_parts = import_info.module.split(".")
        path_parts = file_path.parts

        # Check if any part of the module matches the file path
        for module_part in module_parts:
            if module_part in path_parts or module_part == file_path.stem:
                return True

        return False

    def _is_cross_language_dependency(
        self, dependency: DependencyRelation, parse_results: List[ParseResult]
    ) -> bool:
        """Check if a dependency crosses language boundaries."""
        source_lang = None
        target_lang = None

        for result in parse_results:
            file_path = str(result.file_path)
            if file_path == dependency.source_file:
                source_lang = result.language.value
            elif file_path == dependency.target_file:
                target_lang = result.language.value

        return source_lang and target_lang and source_lang != target_lang

    def _detect_patterns(self, parse_results: List[ParseResult]) -> List[PatternMatch]:
        """Detect design patterns across the codebase."""
        patterns = []

        for pattern_type, detector in self.pattern_detectors.items():
            try:
                pattern_matches = detector(parse_results)
                patterns.extend(pattern_matches)
            except Exception as e:
                logger.warning(f"Pattern detection failed for {pattern_type}: {e}")

        # Sort by confidence
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return patterns

    def _detect_singleton_pattern(
        self, parse_results: List[ParseResult]
    ) -> List[PatternMatch]:
        """Detect Singleton pattern."""
        patterns = []

        for result in parse_results:
            for class_info in result.classes:
                # Look for singleton indicators
                singleton_indicators = 0
                evidence = {}

                # Check for private constructor (language-specific)
                if result.language == Language.JAVA:
                    # Look for private constructor in methods
                    private_constructors = [
                        m for m in class_info.methods if "private" in str(m)
                    ]
                    if private_constructors:
                        singleton_indicators += 1
                        evidence["private_constructor"] = True

                # Check for getInstance method
                get_instance_methods = [
                    m
                    for m in class_info.methods
                    if "getInstance" in str(m) or "get_instance" in str(m)
                ]
                if get_instance_methods:
                    singleton_indicators += 1
                    evidence["get_instance_method"] = get_instance_methods

                # Check for static instance field
                static_fields = [
                    f
                    for f in class_info.fields
                    if "static" in str(f) or "instance" in str(f)
                ]
                if static_fields:
                    singleton_indicators += 1
                    evidence["static_instance"] = static_fields

                # If we have enough indicators, it's likely a singleton
                if singleton_indicators >= 2:
                    confidence = min(0.9, singleton_indicators * 0.3)
                    patterns.append(
                        PatternMatch(
                            pattern_type=PatternType.SINGLETON,
                            confidence=confidence,
                            files=[str(result.file_path)],
                            symbols=[class_info.name],
                            description=f"Singleton pattern detected in class {class_info.name}",
                            evidence=evidence,
                        )
                    )

        return patterns

    def _detect_factory_pattern(
        self, parse_results: List[ParseResult]
    ) -> List[PatternMatch]:
        """Detect Factory pattern."""
        patterns = []

        for result in parse_results:
            # Look for factory-like class names
            factory_classes = [
                c
                for c in result.classes
                if "factory" in c.name.lower() or "builder" in c.name.lower()
            ]

            for factory_class in factory_classes:
                # Look for create methods
                create_methods = [
                    m
                    for m in factory_class.methods
                    if any(
                        keyword in str(m).lower()
                        for keyword in ["create", "build", "make", "new"]
                    )
                ]

                if create_methods:
                    patterns.append(
                        PatternMatch(
                            pattern_type=PatternType.FACTORY,
                            confidence=0.7,
                            files=[str(result.file_path)],
                            symbols=[factory_class.name] + create_methods,
                            description=f"Factory pattern detected in {factory_class.name}",
                            evidence={"create_methods": create_methods},
                        )
                    )

        return patterns

    def _detect_observer_pattern(
        self, parse_results: List[ParseResult]
    ) -> List[PatternMatch]:
        """Detect Observer pattern."""
        patterns = []

        for result in parse_results:
            # Look for observer-like structures
            observer_indicators = []

            for class_info in result.classes:
                # Check for observer-like method names
                observer_methods = [
                    m
                    for m in class_info.methods
                    if any(
                        keyword in str(m).lower()
                        for keyword in ["notify", "update", "observe", "listen"]
                    )
                ]

                # Check for listener/observer collections
                listener_fields = [
                    f
                    for f in class_info.fields
                    if any(
                        keyword in str(f).lower()
                        for keyword in ["listener", "observer", "subscriber"]
                    )
                ]

                if observer_methods or listener_fields:
                    observer_indicators.append(
                        {
                            "class": class_info.name,
                            "methods": observer_methods,
                            "fields": listener_fields,
                        }
                    )

            if observer_indicators:
                patterns.append(
                    PatternMatch(
                        pattern_type=PatternType.OBSERVER,
                        confidence=0.6,
                        files=[str(result.file_path)],
                        symbols=[ind["class"] for ind in observer_indicators],
                        description="Observer pattern detected",
                        evidence={"indicators": observer_indicators},
                    )
                )

        return patterns

    def _detect_strategy_pattern(
        self, parse_results: List[ParseResult]
    ) -> List[PatternMatch]:
        """Detect Strategy pattern."""
        patterns = []

        for result in parse_results:
            # Look for strategy-like interfaces and implementations
            strategy_interfaces = [
                c
                for c in result.classes
                if c.is_interface and "strategy" in c.name.lower()
            ]

            if strategy_interfaces:
                # Look for implementations
                implementations = []
                for class_info in result.classes:
                    for interface in class_info.interfaces:
                        if any(interface == si.name for si in strategy_interfaces):
                            implementations.append(class_info.name)

                if implementations:
                    patterns.append(
                        PatternMatch(
                            pattern_type=PatternType.STRATEGY,
                            confidence=0.8,
                            files=[str(result.file_path)],
                            symbols=[si.name for si in strategy_interfaces]
                            + implementations,
                            description="Strategy pattern detected",
                            evidence={
                                "interfaces": [si.name for si in strategy_interfaces],
                                "implementations": implementations,
                            },
                        )
                    )

        return patterns

    def _detect_decorator_pattern(
        self, parse_results: List[ParseResult]
    ) -> List[PatternMatch]:
        """Detect Decorator pattern."""
        patterns = []

        for result in parse_results:
            # Look for decorator indicators
            for symbol in result.symbols:
                if symbol.decorators:
                    # Python decorators are a form of decorator pattern
                    if result.language == Language.PYTHON:
                        patterns.append(
                            PatternMatch(
                                pattern_type=PatternType.DECORATOR,
                                confidence=0.9,
                                files=[str(result.file_path)],
                                symbols=[symbol.name],
                                description=f"Decorator pattern in {symbol.name}",
                                evidence={"decorators": symbol.decorators},
                            )
                        )

        return patterns

    def _detect_repository_pattern(
        self, parse_results: List[ParseResult]
    ) -> List[PatternMatch]:
        """Detect Repository pattern."""
        patterns = []

        for result in parse_results:
            repo_classes = [
                c
                for c in result.classes
                if "repository" in c.name.lower() or "repo" in c.name.lower()
            ]

            for repo_class in repo_classes:
                # Look for CRUD methods
                crud_methods = [
                    m
                    for m in repo_class.methods
                    if any(
                        keyword in str(m).lower()
                        for keyword in ["find", "save", "delete", "update", "create"]
                    )
                ]

                if crud_methods:
                    patterns.append(
                        PatternMatch(
                            pattern_type=PatternType.REPOSITORY,
                            confidence=0.8,
                            files=[str(result.file_path)],
                            symbols=[repo_class.name],
                            description=f"Repository pattern in {repo_class.name}",
                            evidence={"crud_methods": crud_methods},
                        )
                    )

        return patterns

    def _detect_service_pattern(
        self, parse_results: List[ParseResult]
    ) -> List[PatternMatch]:
        """Detect Service pattern."""
        patterns = []

        for result in parse_results:
            service_classes = [c for c in result.classes if "service" in c.name.lower()]

            for service_class in service_classes:
                # Services typically have business logic methods
                business_methods = [
                    m
                    for m in service_class.methods
                    if not any(
                        keyword in str(m).lower()
                        for keyword in ["get", "set", "__init__", "constructor"]
                    )
                ]

                if business_methods:
                    patterns.append(
                        PatternMatch(
                            pattern_type=PatternType.SERVICE,
                            confidence=0.7,
                            files=[str(result.file_path)],
                            symbols=[service_class.name],
                            description=f"Service pattern in {service_class.name}",
                            evidence={"business_methods": business_methods},
                        )
                    )

        return patterns

    def _detect_error_handling_pattern(
        self, parse_results: List[ParseResult]
    ) -> List[PatternMatch]:
        """Detect error handling patterns."""
        patterns = []

        for result in parse_results:
            error_handling_symbols = []

            # Look for exception/error classes
            error_classes = [
                c
                for c in result.classes
                if any(
                    keyword in c.name.lower()
                    for keyword in ["error", "exception", "fault"]
                )
            ]

            # Look for try-catch like functions (language-specific)
            error_functions = [
                s
                for s in result.symbols
                if any(
                    keyword in s.name.lower()
                    for keyword in ["handle", "catch", "rescue", "except"]
                )
            ]

            if error_classes or error_functions:
                error_handling_symbols.extend([c.name for c in error_classes])
                error_handling_symbols.extend([f.name for f in error_functions])

                patterns.append(
                    PatternMatch(
                        pattern_type=PatternType.ERROR_HANDLING,
                        confidence=0.6,
                        files=[str(result.file_path)],
                        symbols=error_handling_symbols,
                        description="Error handling pattern detected",
                        evidence={
                            "error_classes": [c.name for c in error_classes],
                            "error_functions": [f.name for f in error_functions],
                        },
                    )
                )

        return patterns

    def _detect_async_pattern(
        self, parse_results: List[ParseResult]
    ) -> List[PatternMatch]:
        """Detect async/await patterns."""
        patterns = []

        for result in parse_results:
            async_symbols = [s for s in result.symbols if s.is_async]

            if async_symbols:
                patterns.append(
                    PatternMatch(
                        pattern_type=PatternType.ASYNC_PATTERN,
                        confidence=0.9,
                        files=[str(result.file_path)],
                        symbols=[s.name for s in async_symbols],
                        description=f"Async pattern with {len(async_symbols)} async functions",
                        evidence={"async_functions": [s.name for s in async_symbols]},
                    )
                )

        return patterns

    def _detect_dependency_injection_pattern(
        self, parse_results: List[ParseResult]
    ) -> List[PatternMatch]:
        """Detect dependency injection patterns."""
        patterns = []

        for result in parse_results:
            di_indicators = []

            # Look for constructor injection
            for class_info in result.classes:
                # Check for constructor parameters that look like dependencies
                constructor_methods = [
                    m
                    for m in class_info.methods
                    if m.lower() in ["__init__", "constructor"]
                ]

                if constructor_methods:
                    # This is a simplified check - in reality we'd analyze parameters
                    di_indicators.append(
                        {"class": class_info.name, "type": "constructor_injection"}
                    )

            # Look for dependency injection decorators/annotations
            for symbol in result.symbols:
                if any(
                    decorator.lower() in ["@inject", "@autowired", "@component"]
                    for decorator in symbol.decorators
                ):
                    di_indicators.append(
                        {
                            "symbol": symbol.name,
                            "type": "annotation_injection",
                            "decorators": symbol.decorators,
                        }
                    )

            if di_indicators:
                patterns.append(
                    PatternMatch(
                        pattern_type=PatternType.DEPENDENCY_INJECTION,
                        confidence=0.7,
                        files=[str(result.file_path)],
                        symbols=[
                            ind.get("class", ind.get("symbol", ""))
                            for ind in di_indicators
                        ],
                        description="Dependency injection pattern detected",
                        evidence={"indicators": di_indicators},
                    )
                )

        return patterns

    def _analyze_architectural_layers(
        self, parse_results: List[ParseResult]
    ) -> Dict[ArchitecturalLayer, List[str]]:
        """Analyze architectural layers in the codebase."""
        layers = {layer: [] for layer in ArchitecturalLayer}

        for result in parse_results:
            file_path = str(result.file_path)
            layer = self._classify_architectural_layer(result)
            layers[layer].append(file_path)

        return layers

    def _classify_architectural_layer(self, result: ParseResult) -> ArchitecturalLayer:
        """Classify a file into an architectural layer."""
        file_path = str(result.file_path).lower()

        # Check path-based indicators
        if any(keyword in file_path for keyword in ["test", "spec", "__test__"]):
            return ArchitecturalLayer.TEST
        elif any(keyword in file_path for keyword in ["config", "settings", "env"]):
            return ArchitecturalLayer.CONFIG
        elif any(keyword in file_path for keyword in ["util", "helper", "common"]):
            return ArchitecturalLayer.UTILITY
        elif any(
            keyword in file_path for keyword in ["controller", "view", "ui", "frontend"]
        ):
            return ArchitecturalLayer.PRESENTATION
        elif any(
            keyword in file_path for keyword in ["model", "entity", "dao", "repository"]
        ):
            return ArchitecturalLayer.DATA
        elif any(keyword in file_path for keyword in ["service", "business", "logic"]):
            return ArchitecturalLayer.BUSINESS
        elif any(
            keyword in file_path for keyword in ["infra", "infrastructure", "external"]
        ):
            return ArchitecturalLayer.INFRASTRUCTURE

        # Check class/symbol-based indicators
        for class_info in result.classes:
            class_name = class_info.name.lower()
            if any(
                keyword in class_name for keyword in ["controller", "view", "component"]
            ):
                return ArchitecturalLayer.PRESENTATION
            elif any(
                keyword in class_name for keyword in ["service", "manager", "handler"]
            ):
                return ArchitecturalLayer.BUSINESS
            elif any(
                keyword in class_name
                for keyword in ["repository", "dao", "model", "entity"]
            ):
                return ArchitecturalLayer.DATA
            elif any(
                keyword in class_name for keyword in ["client", "adapter", "gateway"]
            ):
                return ArchitecturalLayer.INFRASTRUCTURE

        # Default to business layer
        return ArchitecturalLayer.BUSINESS

    def _calculate_complexity_metrics(
        self, parse_results: List[ParseResult], dependencies: List[DependencyRelation]
    ) -> Dict[str, float]:
        """Calculate complexity metrics for the codebase."""
        metrics = {}

        # Basic metrics
        total_files = len(parse_results)
        total_symbols = sum(len(result.symbols) for result in parse_results)
        total_classes = sum(len(result.classes) for result in parse_results)
        total_dependencies = len(dependencies)

        metrics["total_files"] = float(total_files)
        metrics["total_symbols"] = float(total_symbols)
        metrics["total_classes"] = float(total_classes)
        metrics["total_dependencies"] = float(total_dependencies)

        # Averages
        metrics["avg_symbols_per_file"] = total_symbols / max(total_files, 1)
        metrics["avg_classes_per_file"] = total_classes / max(total_files, 1)
        metrics["avg_dependencies_per_file"] = total_dependencies / max(total_files, 1)

        # Complexity indicators
        metrics["cyclomatic_complexity"] = self._estimate_cyclomatic_complexity(
            parse_results
        )
        metrics["coupling_factor"] = self._calculate_coupling_factor(
            dependencies, total_files
        )
        metrics["cohesion_factor"] = self._calculate_cohesion_factor(parse_results)

        # Cross-language metrics
        cross_lang_deps = [
            d
            for d in dependencies
            if self._is_cross_language_dependency(d, parse_results)
        ]
        metrics["cross_language_dependencies"] = float(len(cross_lang_deps))
        metrics["cross_language_ratio"] = len(cross_lang_deps) / max(
            total_dependencies, 1
        )

        return metrics

    def _estimate_cyclomatic_complexity(
        self, parse_results: List[ParseResult]
    ) -> float:
        """Estimate cyclomatic complexity based on available information."""
        # This is a simplified estimation
        # In a full implementation, we would analyze control flow from AST

        complexity_indicators = 0
        total_symbols = 0

        for result in parse_results:
            for symbol in result.symbols:
                total_symbols += 1

                # Estimate complexity based on symbol characteristics
                if symbol.parameters:
                    complexity_indicators += len(symbol.parameters) * 0.1

                if symbol.is_async:
                    complexity_indicators += 1  # Async adds complexity

                # Functions with many decorators might be more complex
                complexity_indicators += len(symbol.decorators) * 0.2

        return complexity_indicators / max(total_symbols, 1)

    def _calculate_coupling_factor(
        self, dependencies: List[DependencyRelation], total_files: int
    ) -> float:
        """Calculate coupling factor based on dependencies."""
        if total_files <= 1:
            return 0.0

        # Count unique file pairs that have dependencies
        file_pairs = set()
        for dep in dependencies:
            if dep.source_file != dep.target_file:
                pair = tuple(sorted([dep.source_file, dep.target_file]))
                file_pairs.add(pair)

        # Maximum possible pairs
        max_pairs = (total_files * (total_files - 1)) / 2

        return len(file_pairs) / max(max_pairs, 1)

    def _calculate_cohesion_factor(self, parse_results: List[ParseResult]) -> float:
        """Calculate cohesion factor based on class structure."""
        total_cohesion = 0.0
        total_classes = 0

        for result in parse_results:
            for class_info in result.classes:
                total_classes += 1

                # Simple cohesion metric: ratio of methods to fields
                method_count = len(class_info.methods)
                field_count = len(class_info.fields)

                if method_count + field_count > 0:
                    # Higher ratio of methods to fields suggests better cohesion
                    cohesion = method_count / (method_count + field_count + 1)
                    total_cohesion += cohesion

        return total_cohesion / max(total_classes, 1)

    def _analyze_language_distribution(
        self, parse_results: List[ParseResult]
    ) -> Dict[str, int]:
        """Analyze distribution of programming languages."""
        distribution = {}

        for result in parse_results:
            language = result.language.value
            distribution[language] = distribution.get(language, 0) + 1

        return distribution

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return self.stats.copy()


# Global cross-language analyzer instance
_global_analyzer: Optional[CrossLanguageAnalyzer] = None


def get_cross_language_analyzer() -> CrossLanguageAnalyzer:
    """Get the global cross-language analyzer instance."""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = CrossLanguageAnalyzer()
    return _global_analyzer


# Module-level stub function for MCP tool integration
def analyze_dependencies(directory: str) -> Dict:
    """
    Analyze dependencies in directory.

    Stub implementation for MCP tool integration.

    Args:
        directory: Directory path to analyze

    Returns:
        Dict with status and dependency analysis
    """
    logger.warning(f"CrossLanguageAnalyzer stub called with directory: {directory}")
    return {
        "status": "NOT_IMPLEMENTED",
        "message": "analyze_dependencies is a stub implementation",
        "directory": directory,
        "results": [],
        "dependencies": [],
        "data": {}
    }
