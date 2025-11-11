"""
Data Models for Auto-Discovery Engine

Defines data structures used throughout the auto-discovery process.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ProjectType(str, Enum):
    """Project type classification"""

    WEB_FRONTEND = "web_frontend"
    API_SERVER = "api_server"
    LIBRARY = "library"
    MOBILE_APP = "mobile_app"
    CLI_TOOL = "cli_tool"
    DOCUMENTATION = "documentation"
    MICROSERVICE = "microservice"
    DESKTOP_APP = "desktop_app"
    UNKNOWN = "unknown"


@dataclass
class DiscoveredProject:
    """
    Auto-discovered project with metadata.

    Represents a project detected during directory scanning with
    automatically inferred metadata including type, languages,
    dependencies, and suggested configuration.
    """

    path: str
    """Absolute path to project root directory"""

    type: ProjectType
    """Classified project type"""

    confidence: float
    """Confidence score for classification (0.0 - 1.0)"""

    detected_languages: List[str]
    """Programming languages detected in project"""

    detected_dependencies: List[str]
    """Project names or package names this project depends on"""

    suggested_excludes: List[str]
    """Recommended exclusion patterns for indexing"""

    framework: Optional[str] = None
    """Detected framework (e.g., 'next.js', 'fastapi', 'django')"""

    framework_version: Optional[str] = None
    """Version of detected framework"""

    markers: List[str] = field(default_factory=list)
    """Project marker files found (e.g., 'package.json', 'setup.py')"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional project metadata"""

    discovery_timestamp: datetime = field(default_factory=datetime.now)
    """When this project was discovered"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "path": self.path,
            "type": self.type.value,
            "confidence": self.confidence,
            "detected_languages": self.detected_languages,
            "detected_dependencies": self.detected_dependencies,
            "suggested_excludes": self.suggested_excludes,
            "framework": self.framework,
            "framework_version": self.framework_version,
            "markers": self.markers,
            "metadata": self.metadata,
            "discovery_timestamp": self.discovery_timestamp.isoformat(),
        }


@dataclass
class FrameworkSignal:
    """Signal indicating presence of a framework"""

    framework: str
    """Framework name"""

    confidence: float
    """Confidence this framework is present (0.0 - 1.0)"""

    indicators: List[str]
    """What indicated this framework (files, patterns, etc.)"""


@dataclass
class DependencyRelation:
    """Dependency relationship between projects"""

    from_project: str
    """Source project path"""

    to_project: str
    """Target project path or package name"""

    relation_type: str
    """Type of dependency (imports, api_client, etc.)"""

    confidence: float = 1.0
    """Confidence in this relationship (0.0 - 1.0)"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the relationship"""
