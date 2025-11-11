"""
Tests for Auto-Discovery Engine

Comprehensive tests for project scanner, classifier, dependency analyzer,
and config generator.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.workspace.auto_discovery import (
    ConfigGenerator,
    DependencyAnalyzer,
    DiscoveredProject,
    ProjectScanner,
    ProjectType,
    TypeClassifier,
)


class TestProjectScanner:
    """Tests for ProjectScanner"""

    def test_scan_empty_directory(self, tmp_path):
        """Test scanning an empty directory"""
        scanner = ProjectScanner(max_depth=5)
        projects = scanner.scan(str(tmp_path))

        assert len(projects) == 0
        assert scanner.stats["directories_scanned"] >= 0
        assert scanner.stats["projects_found"] == 0

    def test_scan_single_project(self, tmp_path):
        """Test scanning a directory with one project"""
        # Create a Python project
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / "setup.py").touch()

        scanner = ProjectScanner(max_depth=5)
        projects = scanner.scan(str(tmp_path))

        assert len(projects) == 1
        assert projects[0].path == str(project_dir)
        assert "python" in projects[0].detected_languages
        assert "setup.py" in projects[0].markers

    def test_scan_multiple_projects(self, tmp_path):
        """Test scanning a directory with multiple projects"""
        # Create multiple projects
        projects_data = [
            ("frontend", "package.json", "javascript"),
            ("backend", "setup.py", "python"),
            ("mobile", "pubspec.yaml", "dart"),
        ]

        for name, marker, lang in projects_data:
            proj_dir = tmp_path / name
            proj_dir.mkdir()
            (proj_dir / marker).touch()

        scanner = ProjectScanner(max_depth=5)
        projects = scanner.scan(str(tmp_path))

        assert len(projects) == 3

        # Verify each project
        paths = {p.path for p in projects}
        assert str(tmp_path / "frontend") in paths
        assert str(tmp_path / "backend") in paths
        assert str(tmp_path / "mobile") in paths

    def test_scan_nested_projects(self, tmp_path):
        """Test scanning with nested projects"""
        # Create nested structure
        root_proj = tmp_path / "root-project"
        root_proj.mkdir()
        (root_proj / "package.json").touch()

        nested_proj = root_proj / "packages" / "nested"
        nested_proj.mkdir(parents=True)
        (nested_proj / "package.json").touch()

        scanner = ProjectScanner(max_depth=10)
        projects = scanner.scan(str(tmp_path))

        # Should find root project but not nested (prevents confusion)
        assert len(projects) == 1
        assert projects[0].path == str(root_proj)

    def test_scan_with_ignore_patterns(self, tmp_path):
        """Test scanning respects ignore patterns"""
        # Create projects in ignored directories
        (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
        (tmp_path / "node_modules" / "pkg" / "package.json").touch()

        (tmp_path / "valid-project").mkdir()
        (tmp_path / "valid-project" / "package.json").touch()

        scanner = ProjectScanner(max_depth=5)
        projects = scanner.scan(str(tmp_path))

        # Should only find valid project
        assert len(projects) == 1
        assert "valid-project" in projects[0].path

    def test_scan_max_depth(self, tmp_path):
        """Test max depth limit"""
        # Create deeply nested project
        deep_path = tmp_path
        for i in range(15):
            deep_path = deep_path / f"level{i}"
            deep_path.mkdir()

        (deep_path / "package.json").touch()

        # Scan with low depth
        scanner = ProjectScanner(max_depth=5)
        projects = scanner.scan(str(tmp_path))

        assert len(projects) == 0  # Too deep

        # Scan with high depth
        scanner = ProjectScanner(max_depth=20)
        projects = scanner.scan(str(tmp_path))

        assert len(projects) == 1

    def test_scan_multiple_markers(self, tmp_path):
        """Test project with multiple markers"""
        project_dir = tmp_path / "multi-lang"
        project_dir.mkdir()
        (project_dir / "package.json").touch()
        (project_dir / "setup.py").touch()

        scanner = ProjectScanner()
        projects = scanner.scan(str(tmp_path))

        assert len(projects) == 1
        assert "javascript" in projects[0].detected_languages
        assert "python" in projects[0].detected_languages


class TestTypeClassifier:
    """Tests for TypeClassifier"""

    def test_classify_nextjs_project(self, tmp_path):
        """Test classifying a Next.js project"""
        # Create Next.js project
        project_dir = tmp_path / "nextjs-app"
        project_dir.mkdir()
        (project_dir / "package.json").write_text(
            json.dumps({"dependencies": {"next": "14.0.0", "react": "18.0.0"}})
        )
        (project_dir / "next.config.js").touch()
        (project_dir / "pages").mkdir()

        # Create discovered project
        project = DiscoveredProject(
            path=str(project_dir),
            type=ProjectType.UNKNOWN,
            confidence=0.0,
            detected_languages=["javascript"],
            detected_dependencies=[],
            suggested_excludes=[],
            markers=["package.json"],
        )

        # Classify
        classifier = TypeClassifier()
        classified = classifier.classify(project)

        assert classified.type == ProjectType.WEB_FRONTEND
        assert classified.framework == "next.js"
        assert classified.confidence > 0.5
        assert "node_modules" in classified.suggested_excludes
        assert ".next" in classified.suggested_excludes

    def test_classify_fastapi_project(self, tmp_path):
        """Test classifying a FastAPI project"""
        project_dir = tmp_path / "fastapi-app"
        project_dir.mkdir()
        (project_dir / "requirements.txt").write_text("fastapi==0.104.0\nuvicorn")
        (project_dir / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

        project = DiscoveredProject(
            path=str(project_dir),
            type=ProjectType.UNKNOWN,
            confidence=0.0,
            detected_languages=["python"],
            detected_dependencies=[],
            suggested_excludes=[],
            markers=["requirements.txt"],
        )

        classifier = TypeClassifier()
        classified = classifier.classify(project)

        assert classified.type == ProjectType.API_SERVER
        assert classified.framework == "fastapi"
        assert classified.confidence > 0.5
        assert "venv" in classified.suggested_excludes
        assert "__pycache__" in classified.suggested_excludes

    def test_classify_react_project(self, tmp_path):
        """Test classifying a React project"""
        project_dir = tmp_path / "react-app"
        project_dir.mkdir()
        (project_dir / "package.json").write_text(
            json.dumps({"dependencies": {"react": "18.0.0", "react-dom": "18.0.0"}})
        )

        project = DiscoveredProject(
            path=str(project_dir),
            type=ProjectType.UNKNOWN,
            confidence=0.0,
            detected_languages=["javascript"],
            detected_dependencies=[],
            suggested_excludes=[],
            markers=["package.json"],
        )

        classifier = TypeClassifier()
        classified = classifier.classify(project)

        assert classified.type == ProjectType.WEB_FRONTEND
        assert classified.framework == "react"

    def test_classify_library_project(self, tmp_path):
        """Test classifying a library project"""
        project_dir = tmp_path / "my-lib"
        project_dir.mkdir()
        (project_dir / "setup.py").touch()
        (project_dir / "src").mkdir()

        project = DiscoveredProject(
            path=str(project_dir),
            type=ProjectType.UNKNOWN,
            confidence=0.0,
            detected_languages=["python"],
            detected_dependencies=[],
            suggested_excludes=[],
            markers=["setup.py"],
        )

        classifier = TypeClassifier()
        classified = classifier.classify(project)

        assert classified.type == ProjectType.LIBRARY

    def test_classify_documentation_project(self, tmp_path):
        """Test classifying a documentation project"""
        project_dir = tmp_path / "docs"
        project_dir.mkdir()
        (project_dir / "mkdocs.yml").touch()

        project = DiscoveredProject(
            path=str(project_dir),
            type=ProjectType.UNKNOWN,
            confidence=0.0,
            detected_languages=[],
            detected_dependencies=[],
            suggested_excludes=[],
            markers=[],
        )

        classifier = TypeClassifier()
        classified = classifier.classify(project)

        assert classified.type == ProjectType.DOCUMENTATION
        assert classified.framework == "mkdocs"


class TestDependencyAnalyzer:
    """Tests for DependencyAnalyzer"""

    def test_analyze_package_json_local_deps(self, tmp_path):
        """Test analyzing package.json with local dependencies"""
        # Create projects
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text(
            json.dumps(
                {
                    "name": "frontend",
                    "dependencies": {
                        "shared": "file:../shared",
                        "react": "18.0.0",
                    },
                }
            )
        )

        shared = tmp_path / "shared"
        shared.mkdir()
        (shared / "package.json").write_text(json.dumps({"name": "shared"}))

        # Create discovered projects
        projects = [
            DiscoveredProject(
                path=str(frontend),
                type=ProjectType.WEB_FRONTEND,
                confidence=0.9,
                detected_languages=["javascript"],
                detected_dependencies=[],
                suggested_excludes=[],
                markers=["package.json"],
            ),
            DiscoveredProject(
                path=str(shared),
                type=ProjectType.LIBRARY,
                confidence=0.9,
                detected_languages=["javascript"],
                detected_dependencies=[],
                suggested_excludes=[],
                markers=["package.json"],
            ),
        ]

        # Analyze
        analyzer = DependencyAnalyzer()
        updated_projects, relations = analyzer.analyze(projects)

        # Check relations
        assert len(relations) > 0
        frontend_deps = [r for r in relations if r.from_project == str(frontend)]
        assert len(frontend_deps) > 0
        assert any(r.to_project == str(shared) for r in frontend_deps)

    def test_analyze_requirements_txt_local_deps(self, tmp_path):
        """Test analyzing requirements.txt with local dependencies"""
        # Create projects
        backend = tmp_path / "backend"
        backend.mkdir()
        (backend / "requirements.txt").write_text(
            "fastapi==0.104.0\n-e ../shared\nuvicorn"
        )

        shared = tmp_path / "shared"
        shared.mkdir()
        (shared / "setup.py").touch()

        # Create discovered projects
        projects = [
            DiscoveredProject(
                path=str(backend),
                type=ProjectType.API_SERVER,
                confidence=0.9,
                detected_languages=["python"],
                detected_dependencies=[],
                suggested_excludes=[],
                markers=["requirements.txt"],
            ),
            DiscoveredProject(
                path=str(shared),
                type=ProjectType.LIBRARY,
                confidence=0.9,
                detected_languages=["python"],
                detected_dependencies=[],
                suggested_excludes=[],
                markers=["setup.py"],
            ),
        ]

        # Analyze
        analyzer = DependencyAnalyzer()
        updated_projects, relations = analyzer.analyze(projects)

        # Check relations
        backend_deps = [r for r in relations if r.from_project == str(backend)]
        assert any(r.to_project == str(shared) for r in backend_deps)

    def test_analyze_related_project_names(self, tmp_path):
        """Test detecting related projects by name"""
        # Create projects with related names
        frontend = tmp_path / "myapp-frontend"
        frontend.mkdir()
        (frontend / "package.json").touch()

        backend = tmp_path / "myapp-backend"
        backend.mkdir()
        (backend / "setup.py").touch()

        projects = [
            DiscoveredProject(
                path=str(frontend),
                type=ProjectType.WEB_FRONTEND,
                confidence=0.9,
                detected_languages=["javascript"],
                detected_dependencies=[],
                suggested_excludes=[],
                markers=["package.json"],
            ),
            DiscoveredProject(
                path=str(backend),
                type=ProjectType.API_SERVER,
                confidence=0.9,
                detected_languages=["python"],
                detected_dependencies=[],
                suggested_excludes=[],
                markers=["setup.py"],
            ),
        ]

        # Analyze
        analyzer = DependencyAnalyzer()
        updated_projects, relations = analyzer.analyze(projects)

        # Should detect semantic similarity
        similarity_relations = [
            r for r in relations if r.relation_type == "semantic_similarity"
        ]
        assert len(similarity_relations) > 0


class TestConfigGenerator:
    """Tests for ConfigGenerator"""

    def test_generate_workspace_config(self, tmp_path):
        """Test generating workspace configuration"""
        # Create discovered projects
        projects = [
            DiscoveredProject(
                path=str(tmp_path / "frontend"),
                type=ProjectType.WEB_FRONTEND,
                confidence=0.95,
                detected_languages=["javascript", "typescript"],
                detected_dependencies=["backend"],
                suggested_excludes=["node_modules", "dist"],
                framework="next.js",
                framework_version="14.0.0",
                markers=["package.json"],
            ),
            DiscoveredProject(
                path=str(tmp_path / "backend"),
                type=ProjectType.API_SERVER,
                confidence=0.88,
                detected_languages=["python"],
                detected_dependencies=[],
                suggested_excludes=["venv", "__pycache__"],
                framework="fastapi",
                framework_version="0.104.0",
                markers=["setup.py"],
            ),
        ]

        relations = []

        # Generate config
        generator = ConfigGenerator()
        config = generator.generate(
            projects=projects,
            relations=relations,
            workspace_name="My Workspace",
            base_path=str(tmp_path),
        )

        # Verify config
        assert config.name == "My Workspace"
        assert config.version == "2.0.0"
        assert len(config.projects) == 2

        # Check frontend project
        frontend = config.projects[0]
        assert frontend.type == "web_frontend"
        assert "javascript" in frontend.language
        assert frontend.indexing.priority == "high"
        assert "node_modules" in frontend.indexing.exclude
        assert frontend.metadata.get("framework") == "next.js"
        assert frontend.metadata.get("auto_discovered") is True

        # Check backend project
        backend = config.projects[1]
        assert backend.type == "api_server"
        assert "python" in backend.language
        assert backend.indexing.priority == "high"
        assert "venv" in backend.indexing.exclude

    def test_generate_project_ids(self, tmp_path):
        """Test project ID generation"""
        projects = [
            DiscoveredProject(
                path=str(tmp_path / "my-app-frontend"),
                type=ProjectType.WEB_FRONTEND,
                confidence=0.9,
                detected_languages=["javascript"],
                detected_dependencies=[],
                suggested_excludes=[],
                markers=["package.json"],
            ),
            DiscoveredProject(
                path=str(tmp_path / "123-invalid-start"),
                type=ProjectType.API_SERVER,
                confidence=0.9,
                detected_languages=["python"],
                detected_dependencies=[],
                suggested_excludes=[],
                markers=["setup.py"],
            ),
        ]

        generator = ConfigGenerator()
        config = generator.generate(projects, [], base_path=str(tmp_path))

        # Check IDs are valid
        ids = [p.id for p in config.projects]
        assert "my_app_frontend" in ids
        assert all(p.id.replace('_', '').isalnum() for p in config.projects)

    def test_generate_workspace_name(self, tmp_path):
        """Test workspace name generation"""
        projects = [
            DiscoveredProject(
                path=str(tmp_path / "myapp-frontend"),
                type=ProjectType.WEB_FRONTEND,
                confidence=0.9,
                detected_languages=["javascript"],
                detected_dependencies=[],
                suggested_excludes=[],
                markers=["package.json"],
            ),
            DiscoveredProject(
                path=str(tmp_path / "myapp-backend"),
                type=ProjectType.API_SERVER,
                confidence=0.9,
                detected_languages=["python"],
                detected_dependencies=[],
                suggested_excludes=[],
                markers=["setup.py"],
            ),
        ]

        generator = ConfigGenerator()
        config = generator.generate(projects, [], base_path=str(tmp_path))

        # Should generate a valid workspace name
        assert config.name
        assert len(config.name) > 0
        # Should be humanized (capitalized)
        assert config.name[0].isupper()


class TestFullDiscoveryWorkflow:
    """Integration tests for full discovery workflow"""

    def test_discover_monorepo(self, tmp_path):
        """Test discovering a monorepo structure"""
        # Create monorepo structure
        (tmp_path / "frontend").mkdir()
        (tmp_path / "frontend" / "package.json").write_text(
            json.dumps(
                {
                    "name": "frontend",
                    "dependencies": {
                        "next": "14.0.0",
                        "react": "18.0.0",
                    },
                }
            )
        )
        (tmp_path / "frontend" / "next.config.js").touch()

        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "requirements.txt").write_text(
            "fastapi==0.104.0\nuvicorn"
        )
        (tmp_path / "backend" / "main.py").write_text(
            "from fastapi import FastAPI\napp = FastAPI()"
        )

        (tmp_path / "shared").mkdir()
        (tmp_path / "shared" / "package.json").write_text(
            json.dumps({"name": "shared"})
        )

        # Run full discovery
        scanner = ProjectScanner()
        discovered = scanner.scan(str(tmp_path))

        classifier = TypeClassifier()
        for project in discovered:
            classifier.classify(project)

        analyzer = DependencyAnalyzer()
        discovered, relations = analyzer.analyze(discovered)

        generator = ConfigGenerator()
        config = generator.generate(discovered, relations, base_path=str(tmp_path))

        # Verify results
        assert len(config.projects) == 3

        # Check types
        types = {p.type for p in config.projects}
        assert "web_frontend" in types
        assert "api_server" in types
        assert "library" in types or "web_frontend" in types

    def test_discover_empty_workspace(self, tmp_path):
        """Test discovering an empty workspace"""
        scanner = ProjectScanner()
        discovered = scanner.scan(str(tmp_path))

        assert len(discovered) == 0

    def test_discover_performance(self, tmp_path):
        """Test discovery performance on larger structure"""
        import time

        # Create 50 projects
        for i in range(50):
            proj_dir = tmp_path / f"project-{i}"
            proj_dir.mkdir()
            (proj_dir / "package.json").touch()

        # Measure scan time
        start = time.time()
        scanner = ProjectScanner()
        discovered = scanner.scan(str(tmp_path))
        scan_time = time.time() - start

        # Should find all projects quickly
        assert len(discovered) == 50
        assert scan_time < 5.0  # Should complete in < 5 seconds

        # Measure classification time
        start = time.time()
        classifier = TypeClassifier()
        for project in discovered:
            classifier.classify(project)
        classify_time = time.time() - start

        assert classify_time < 10.0  # Should complete in < 10 seconds
