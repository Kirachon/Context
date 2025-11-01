"""
Context Application Settings

Configuration management using Pydantic Settings for environment-based configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Optional, Dict, Any
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application metadata
    app_name: str = "Context"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Database configuration
    database_url: str = Field(
        default="postgresql://context:password@localhost:5432/context_dev",
        description="PostgreSQL database connection URL"
    )
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=100)

    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # Qdrant vector database
    qdrant_host: str = Field(default="localhost", description="Qdrant server host")
    qdrant_port: int = Field(default=6333, ge=1, le=65535)
    qdrant_collection: str = Field(default="context_vectors", description="Qdrant collection name")
    qdrant_vector_size: int = Field(default=384, description="Vector embedding dimension")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API key (optional)")
    qdrant_timeout: int = Field(default=30, ge=1, le=300)
    qdrant_max_retries: int = Field(default=3, ge=1, le=10)

    # Ollama AI processing
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "codellama:7b"
    ollama_timeout: int = 300
    ollama_max_retries: int = 3

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    workers: int = 1

    # API AuthN (optional)
    api_auth_enabled: bool = False
    api_auth_scheme: str = "none"  # options: none, api_key
    api_key: Optional[str] = None

    # Correlation ID
    correlation_id_header: str = "X-Request-ID"

    # MCP Server configuration
    mcp_enabled: bool = True
    mcp_server_name: str = "Context"
    mcp_server_version: str = "0.1.0"
    mcp_capabilities: List[str] = Field(
        default=["health_check", "capabilities", "semantic_search"],
        description="MCP server capabilities"
    )

    @field_validator('mcp_capabilities', mode='before')
    @classmethod
    def parse_mcp_capabilities(cls, v):
        if isinstance(v, str):
            # Handle comma-separated string
            if v.startswith('[') and v.endswith(']'):
                # Try to parse as JSON
                try:
                    import json
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated values
            return [cap.strip() for cap in v.split(',') if cap.strip()]
        return v
    # Query cache
    query_cache_redis_enabled: bool = False
    cache_max_items: int = 500

    # Circuit breaker (Ollama)
    ollama_cb_enabled: bool = True
    ollama_cb_threshold: int = 5
    ollama_cb_window_seconds: int = 30
    ollama_cb_cooldown_seconds: int = 20

    mcp_connection_timeout: int = 30
    mcp_max_retries: int = 3

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Performance settings
    max_search_results: int = 50
    cache_ttl_seconds: int = 1800
    indexing_batch_size: int = 100

    # Embeddings provider (feature-flagged)
    embeddings_provider: str = Field(default="sentence-transformers", description="Embedding provider: 'sentence-transformers' (default) or 'unixcoder'")
    unixcoder_enabled: bool = Field(default=False, description="Enable UniXcoder provider behind feature flag")

    # File system monitoring
    indexed_paths: List[str] = Field(default=["./"], description="Paths to index for search")
    ignore_patterns: List[str] = Field(
        default=[".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"],
        description="Patterns to ignore during indexing"
    )

    @field_validator('indexed_paths', mode='before')
    @classmethod
    def parse_indexed_paths(cls, v):
        if isinstance(v, str):
            # Handle comma-separated string
            if v.startswith('[') and v.endswith(']'):
                # Try to parse as JSON
                try:
                    import json
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated values
            return [path.strip() for path in v.split(',') if path.strip()]
        return v

    @field_validator('ignore_patterns', mode='before')
    @classmethod
    def parse_ignore_patterns(cls, v):
        if isinstance(v, str):
            # Handle comma-separated string
            if v.startswith('[') and v.endswith(']'):
                # Try to parse as JSON
                try:
                    import json
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated values
            return [pattern.strip() for pattern in v.split(',') if pattern.strip()]
        return v

    # Hardware requirements
    min_memory_gb: int = 8
    min_cpu_cores: int = 4
    min_disk_space_gb: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
