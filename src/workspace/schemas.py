"""
JSON Schemas for Workspace Configuration

Provides JSON Schema definitions for .context-workspace.json file format.
These schemas can be used for IDE autocomplete, validation, and documentation.
"""

from typing import Any, Dict

# JSON Schema for .context-workspace.json
WORKSPACE_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://context-engine.dev/schemas/workspace-config.json",
    "title": "Context Workspace Configuration",
    "description": "Configuration for multi-project code context workspace",
    "type": "object",
    "required": ["version", "name", "projects"],
    "properties": {
        "version": {
            "type": "string",
            "description": "Workspace configuration version (semver)",
            "pattern": "^\\d+\\.\\d+\\.\\d+$",
            "default": "2.0.0",
        },
        "name": {
            "type": "string",
            "description": "Human-readable workspace name",
            "minLength": 1,
        },
        "projects": {
            "type": "array",
            "description": "List of projects in the workspace",
            "items": {"$ref": "#/definitions/project"},
            "minItems": 1,
        },
        "relationships": {
            "type": "array",
            "description": "Explicit project-to-project relationships",
            "items": {"$ref": "#/definitions/relationship"},
            "default": [],
        },
        "search": {
            "$ref": "#/definitions/search_config",
            "description": "Search behavior configuration",
        },
    },
    "definitions": {
        "project": {
            "type": "object",
            "required": ["id", "name", "path"],
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Unique project identifier (alphanumeric + underscore)",
                    "pattern": "^[a-zA-Z0-9_]+$",
                },
                "name": {
                    "type": "string",
                    "description": "Human-readable project name",
                    "minLength": 1,
                },
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to project directory",
                    "minLength": 1,
                },
                "type": {
                    "type": "string",
                    "description": "Project type classification",
                    "default": "application",
                    "examples": [
                        "web_frontend",
                        "api_server",
                        "library",
                        "documentation",
                        "mobile_app",
                        "desktop_app",
                        "cli_tool",
                        "microservice",
                    ],
                },
                "language": {
                    "type": "array",
                    "description": "Programming languages used in project",
                    "items": {"type": "string"},
                    "default": [],
                    "examples": [
                        ["typescript", "tsx"],
                        ["python"],
                        ["rust"],
                        ["go"],
                    ],
                },
                "dependencies": {
                    "type": "array",
                    "description": "Project IDs this project depends on",
                    "items": {"type": "string"},
                    "default": [],
                },
                "indexing": {
                    "$ref": "#/definitions/indexing_config",
                    "description": "Indexing configuration for this project",
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional project metadata",
                    "default": {},
                    "additionalProperties": True,
                },
            },
        },
        "indexing_config": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "Whether indexing is enabled",
                    "default": True,
                },
                "priority": {
                    "type": "string",
                    "description": "Indexing priority level",
                    "enum": ["critical", "high", "medium", "low"],
                    "default": "medium",
                },
                "exclude": {
                    "type": "array",
                    "description": "Glob patterns to exclude from indexing",
                    "items": {"type": "string"},
                    "default": [],
                    "examples": [
                        ["node_modules", "dist", ".next"],
                        ["venv", "__pycache__", ".pytest_cache"],
                        ["target", "Cargo.lock"],
                    ],
                },
            },
        },
        "relationship": {
            "type": "object",
            "required": ["from", "to", "type"],
            "properties": {
                "from": {
                    "type": "string",
                    "description": "Source project ID",
                },
                "to": {
                    "type": "string",
                    "description": "Target project ID",
                },
                "type": {
                    "type": "string",
                    "description": "Type of relationship",
                    "enum": [
                        "imports",
                        "api_client",
                        "shared_database",
                        "event_driven",
                        "semantic_similarity",
                        "dependency",
                    ],
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of relationship",
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional relationship metadata",
                    "default": {},
                    "additionalProperties": True,
                },
            },
        },
        "search_config": {
            "type": "object",
            "properties": {
                "default_scope": {
                    "type": "string",
                    "description": "Default search scope",
                    "enum": ["project", "dependencies", "workspace", "related"],
                    "default": "workspace",
                },
                "cross_project_ranking": {
                    "type": "boolean",
                    "description": "Enable relationship-aware ranking",
                    "default": True,
                },
                "relationship_boost": {
                    "type": "number",
                    "description": "Boost factor for results from related projects",
                    "minimum": 1.0,
                    "maximum": 3.0,
                    "default": 1.5,
                },
            },
        },
    },
}


def get_schema_for_vscode() -> Dict[str, Any]:
    """
    Get JSON schema formatted for VS Code settings.json.

    Add this to your VS Code settings:
    ```json
    {
      "json.schemas": [
        {
          "fileMatch": [".context-workspace.json"],
          "schema": <insert returned schema here>
        }
      ]
    }
    ```

    Returns:
        JSON schema dictionary
    """
    return WORKSPACE_SCHEMA


def get_schema_url() -> str:
    """
    Get the canonical URL for the workspace schema.

    This can be used in workspace files:
    ```json
    {
      "$schema": "https://context-engine.dev/schemas/workspace-config.json",
      "version": "2.0.0",
      ...
    }
    ```

    Returns:
        Schema URL string
    """
    return WORKSPACE_SCHEMA["$id"]
