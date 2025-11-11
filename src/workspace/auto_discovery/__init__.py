"""
Auto-Discovery Engine for Context Workspace v2.5

Automatically detects and configures projects with zero manual setup.
Scans directory trees, classifies project types, analyzes dependencies,
and generates complete workspace configurations.
"""

from .models import DiscoveredProject, ProjectType
from .scanner import ProjectScanner
from .classifier import TypeClassifier
from .dependency_analyzer import DependencyAnalyzer
from .config_generator import ConfigGenerator

__all__ = [
    "DiscoveredProject",
    "ProjectType",
    "ProjectScanner",
    "TypeClassifier",
    "DependencyAnalyzer",
    "ConfigGenerator",
]
