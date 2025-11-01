"""
MCP Cross-Language Analysis Tools

Provides cross-language code analysis tools via MCP protocol.
"""

import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.analysis.cross_language import get_cross_language_analyzer
from src.analysis.similarity import get_similarity_detector
from src.parsing.parser import get_parser
from src.parsing.models import Language

logger = logging.getLogger(__name__)


def register_cross_language_tools(mcp: FastMCP):
    """
    Register cross-language analysis tools with MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def analyze_codebase_architecture(
        directory_path: str,
        recursive: bool = True,
        languages: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze codebase architecture and design patterns

        Performs comprehensive cross-language analysis including design pattern
        detection, architectural layer analysis, dependency mapping, and
        complexity metrics calculation.

        Args:
            directory_path: Path to directory to analyze
            recursive: Whether to analyze subdirectories (default: true)
            languages: Filter by specific languages (optional)

        Returns:
            Dict containing architectural analysis results
        """
        logger.info(f"MCP architectural analysis invoked: {directory_path}")

        try:
            dir_path = Path(directory_path)
            if not dir_path.exists() or not dir_path.is_dir():
                return {
                    "error": f"Directory does not exist: {directory_path}",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Find and parse code files
            parser = get_parser()
            parse_results = []

            # Get supported file extensions
            supported_extensions = {
                ".py": Language.PYTHON,
                ".js": Language.JAVASCRIPT,
                ".jsx": Language.JAVASCRIPT,
                ".ts": Language.TYPESCRIPT,
                ".tsx": Language.TYPESCRIPT,
                ".java": Language.JAVA,
                ".cpp": Language.CPP,
                ".cc": Language.CPP,
                ".hpp": Language.CPP,
                ".h": Language.CPP,
                ".go": Language.GO,
                ".rs": Language.RUST,
            }

            # Find files to analyze
            files_to_analyze = []
            if recursive:
                for ext in supported_extensions.keys():
                    files_to_analyze.extend(dir_path.rglob(f"*{ext}"))
            else:
                for file_path in dir_path.iterdir():
                    if file_path.suffix in supported_extensions:
                        files_to_analyze.append(file_path)

            # Filter by languages if specified
            if languages:
                language_set = set(languages)
                files_to_analyze = [
                    f
                    for f in files_to_analyze
                    if supported_extensions.get(f.suffix, "").value in language_set
                ]

            # Parse files
            for file_path in files_to_analyze[:50]:  # Limit to 50 files for performance
                try:
                    result = parser.parse(file_path)
                    if result.parse_success:
                        parse_results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to parse {file_path}: {e}")

            if not parse_results:
                return {
                    "error": "No files could be parsed successfully",
                    "files_found": len(files_to_analyze),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Perform cross-language analysis
            analyzer = get_cross_language_analyzer()
            analysis = analyzer.analyze_codebase(parse_results)

            # Convert to response format
            return {
                "success": True,
                "directory": str(dir_path),
                "files_analyzed": len(parse_results),
                "files_found": len(files_to_analyze),
                "architectural_layers": analysis.to_dict()["layers"],
                "design_patterns": [pattern.to_dict() for pattern in analysis.patterns],
                "dependencies": [
                    dep.to_dict() for dep in analysis.dependencies[:20]
                ],  # Limit for response size
                "complexity_metrics": analysis.complexity_metrics,
                "language_distribution": analysis.language_distribution,
                "summary": {
                    "total_patterns": len(analysis.patterns),
                    "total_dependencies": len(analysis.dependencies),
                    "cross_language_dependencies": analysis.complexity_metrics.get(
                        "cross_language_dependencies", 0
                    ),
                    "coupling_factor": analysis.complexity_metrics.get(
                        "coupling_factor", 0.0
                    ),
                    "cohesion_factor": analysis.complexity_metrics.get(
                        "cohesion_factor", 0.0
                    ),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Architectural analysis failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    @mcp.tool()
    async def detect_design_patterns(
        directory_path: str,
        pattern_types: Optional[List[str]] = None,
        min_confidence: float = 0.6,
    ) -> Dict[str, Any]:
        """
        Detect design patterns across the codebase

        Analyzes code to identify common design patterns like Singleton,
        Factory, Observer, Strategy, Repository, Service, and more.

        Args:
            directory_path: Path to directory to analyze
            pattern_types: Specific pattern types to look for (optional)
            min_confidence: Minimum confidence score (0.0-1.0, default: 0.6)

        Returns:
            Dict containing detected design patterns
        """
        logger.info(f"MCP pattern detection invoked: {directory_path}")

        try:
            # Similar file parsing logic as above
            dir_path = Path(directory_path)
            if not dir_path.exists():
                return {"error": f"Directory does not exist: {directory_path}"}

            # Parse files (simplified for this tool)
            parser = get_parser()
            parse_results = []

            for file_path in dir_path.rglob("*.py"):  # Focus on Python for demo
                if len(parse_results) >= 20:  # Limit for performance
                    break
                try:
                    result = parser.parse(file_path)
                    if result.parse_success:
                        parse_results.append(result)
                except Exception:
                    continue

            if not parse_results:
                return {"error": "No files could be parsed"}

            # Analyze patterns
            analyzer = get_cross_language_analyzer()
            analysis = analyzer.analyze_codebase(parse_results)

            # Filter patterns
            patterns = analysis.patterns
            if pattern_types:
                pattern_set = set(pattern_types)
                patterns = [p for p in patterns if p.pattern_type.value in pattern_set]

            patterns = [p for p in patterns if p.confidence >= min_confidence]

            # Group by pattern type
            pattern_groups = {}
            for pattern in patterns:
                pattern_type = pattern.pattern_type.value
                if pattern_type not in pattern_groups:
                    pattern_groups[pattern_type] = []
                pattern_groups[pattern_type].append(pattern.to_dict())

            return {
                "success": True,
                "directory": str(dir_path),
                "files_analyzed": len(parse_results),
                "patterns_found": len(patterns),
                "pattern_groups": pattern_groups,
                "summary": {
                    pattern_type: len(group)
                    for pattern_type, group in pattern_groups.items()
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Pattern detection failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    @mcp.tool()
    async def find_code_similarities(
        directory_path: str,
        min_similarity: float = 0.7,
        cross_language_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Find similar code patterns across languages

        Detects structurally and semantically similar code elements across
        different programming languages, helping identify code duplication
        and potential refactoring opportunities.

        Args:
            directory_path: Path to directory to analyze
            min_similarity: Minimum similarity score (0.0-1.0, default: 0.7)
            cross_language_only: Only show cross-language similarities (default: false)

        Returns:
            Dict containing similarity matches
        """
        logger.info(f"MCP similarity detection invoked: {directory_path}")

        try:
            dir_path = Path(directory_path)
            if not dir_path.exists():
                return {"error": f"Directory does not exist: {directory_path}"}

            # Parse files
            parser = get_parser()
            parse_results = []

            supported_extensions = [".py", ".js", ".ts", ".java"]
            for ext in supported_extensions:
                for file_path in dir_path.rglob(f"*{ext}"):
                    if len(parse_results) >= 20:  # Limit for performance
                        break
                    try:
                        result = parser.parse(file_path)
                        if result.parse_success and result.symbols:
                            parse_results.append(result)
                    except Exception:
                        continue

            if len(parse_results) < 2:
                return {"error": "Need at least 2 files with symbols to compare"}

            # Find similarities
            detector = get_similarity_detector()
            similarities = detector.find_similarities(parse_results, min_similarity)

            # Filter cross-language only if requested
            if cross_language_only:
                similarities = [
                    s for s in similarities if s.source_language != s.target_language
                ]

            # Group by similarity type
            similarity_groups = {}
            for sim in similarities:
                sim_type = sim.similarity_type
                if sim_type not in similarity_groups:
                    similarity_groups[sim_type] = []
                similarity_groups[sim_type].append(sim.to_dict())

            # Calculate statistics
            cross_language_count = len(
                [s for s in similarities if s.source_language != s.target_language]
            )

            return {
                "success": True,
                "directory": str(dir_path),
                "files_analyzed": len(parse_results),
                "similarities_found": len(similarities),
                "cross_language_similarities": cross_language_count,
                "similarity_groups": similarity_groups,
                "summary": {
                    "by_type": {
                        sim_type: len(group)
                        for sim_type, group in similarity_groups.items()
                    },
                    "average_similarity": sum(s.similarity_score for s in similarities)
                    / max(len(similarities), 1),
                    "languages_involved": list(
                        set(
                            [s.source_language for s in similarities]
                            + [s.target_language for s in similarities]
                        )
                    ),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Similarity detection failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
