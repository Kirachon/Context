"""
Context Application Settings

Configuration management using Pydantic Settings for environment-based configuration.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application metadata
    app_name: str = "Context"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Database configuration
    database_url: str = Field(
        default="postgresql://context:password@localhost:5432/context_dev",
        description="PostgreSQL database connection URL",
    )
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=100)

    # Optional PostgreSQL metadata store (disabled by default)
    postgres_enabled: bool = Field(
        default=False,
        description="Enable PostgreSQL-backed metadata persistence. When false, the server runs in vector-only mode and will not attempt any database connections."
    )

    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # Qdrant vector database
    qdrant_host: str = Field(default="localhost", description="Qdrant server host")
    qdrant_port: int = Field(default=6333, ge=1, le=65535)
    qdrant_collection: str = Field(
        default="context_vectors", description="Qdrant collection name"
    )
    qdrant_vector_size: int = Field(
        default=384, description="Vector embedding dimension"
    )
    qdrant_api_key: Optional[str] = Field(
        default=None, description="Qdrant API key (optional)"
    )
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

    # Rate limiting (simple in-process)
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = 60
    rate_limit_key: str = "ip"  # options: ip, api_key

    # Conversation state (in-memory)
    conversation_state_enabled: bool = True
    conversation_max_conversations: int = 1000
    conversation_max_messages_per_conversation: int = 100
    conversation_ttl_seconds: int = 3600  # 1 hour

    # MCP Server configuration
    mcp_enabled: bool = True
    mcp_server_name: str = "Context"
    mcp_server_version: str = "0.1.0"
    mcp_capabilities: List[str] = Field(
        default=["health_check", "capabilities", "semantic_search"],
        description="MCP server capabilities",
    )

    @field_validator("mcp_capabilities", mode="before")
    @classmethod
    def parse_mcp_capabilities(cls, v):
        if isinstance(v, str):
            # Handle comma-separated string
            if v.startswith("[") and v.endswith("]"):
                # Try to parse as JSON
                try:
                    import json

                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated values
            return [cap.strip() for cap in v.split(",") if cap.strip()]
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
    embeddings_provider: str = Field(
        default="sentence-transformers",
        description="Embedding provider: 'sentence-transformers' (default), 'google', or 'unixcoder'",
    )
    unixcoder_enabled: bool = Field(
        default=False, description="Enable UniXcoder provider behind feature flag"
    )

    # Google embeddings configuration
    google_api_key: Optional[str] = Field(
        default=None, description="Google API key for Gemini embeddings"
    )
    google_embedding_model: str = Field(
        default="text-embedding-004",
        description="Google embedding model (text-embedding-004 or textembedding-gecko)"
    )

    # File system monitoring
    indexed_paths: Optional[List[str]] = Field(
        default=None,
        description="Paths to index for search (defaults to CLAUDE_PROJECT_DIR or current directory)"
    )
    ignore_patterns: List[str] = Field(
        default=[".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"],
        description="Patterns to ignore during indexing",
    )

    @field_validator("indexed_paths", mode="before")
    @classmethod
    def parse_indexed_paths_before(cls, v):
        # Handle string input (from environment variables or config files)
        if isinstance(v, str):
            # Handle JSON array format
            if v.startswith("[") and v.endswith("]"):
                try:
                    import json
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated values
            return [path.strip() for path in v.split(",") if path.strip()]
        return v

    @field_validator("indexed_paths", mode="after")
    @classmethod
    def parse_indexed_paths_after(cls, v):
        # If value is the default ["./"], check for CLAUDE_PROJECT_DIR
        # This allows Claude Code CLI to override the default with the current project directory
        if v == ["./"] or v is None:
            claude_project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
            if claude_project_dir:
                return [claude_project_dir]
            return ["./"]
        return v

    @field_validator("ignore_patterns", mode="before")
    @classmethod
    def parse_ignore_patterns(cls, v):
        if isinstance(v, str):
            # Handle comma-separated string
            if v.startswith("[") and v.endswith("]"):
                # Try to parse as JSON
                try:
                    import json

                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated values
            return [pattern.strip() for pattern in v.split(",") if pattern.strip()]
        return v

    # Hardware requirements
    min_memory_gb: int = 8
    min_cpu_cores: int = 4
    min_disk_space_gb: int = 10

    # GPU configuration
    gpu_enabled: bool = Field(
        default=True,
        description="Enable GPU acceleration if available"
    )
    gpu_batch_size: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Batch size for GPU embedding generation"
    )
    cpu_batch_size: int = Field(
        default=8,
        ge=1,
        le=64,
        description="Batch size for CPU embedding generation"
    )
    gpu_memory_fraction: float = Field(
        default=0.9,
        ge=0.1,
        le=1.0,
        description="Fraction of GPU memory to use (0.1-1.0)"
    )
    embedding_show_progress: bool = Field(
        default=False,
        description="Show progress bar during embedding generation"
    )

    # NLP / Prompt analysis (feature-flagged)
    enable_nlp_analysis: bool = Field(
        default=False,
        description="Enable spaCy-based NLP analysis in PromptAnalyzer (additive, non-breaking)"
    )
    nlp_model: str = Field(
        default="en_core_web_sm",
        description="spaCy model to load for NLP analysis"
    )
    nlp_max_doc_length: int = Field(
        default=20000,
        ge=1000,
        description="Maximum characters to process with NLP to protect performance"
    )

    # Deployment integrations (feature-flagged)
    enable_deployment_integrations: bool = Field(
        default=False,
        description="Enable MCP tools for Vercel/Render/Railway/Supabase integrations"
    )
    # Query refinement & conversation tracking (feature-flagged)
    enable_query_refinement: bool = Field(
        default=False,
        description="Enable query refinement MCP tools"
    )
    enable_conversation_tracking: bool = Field(
        default=False,
        description="Enable conversation-aware query enhancement/refinement features"
    )

    # Performance profiling (feature-flagged)
    enable_performance_profiling: bool = Field(
        default=False,
        description="Enable lightweight performance profiling on selected tools"
    )
    profiling_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Probability (0-1) to sample a profiling run"
    )
    profiling_store_results: bool = Field(
        default=False,
        description="If true, store profiling results in memory (or DB when enabled)"
    )

    # Security scanning (feature-flagged)
    enable_security_scanning: bool = Field(
        default=False,
        description="Enable lightweight security scanning tools"
    )
    security_scan_on_index: bool = Field(
        default=False,
        description="Run security scans during indexing (async). Off by default"
    )
    security_severity_threshold: str = Field(
        default="medium",
        description="Minimum severity to include in reports: low|medium|high"
    )

    # Real-time monitoring (feature-flagged)
    enable_realtime_monitoring: bool = Field(
        default=False,
        description="Enable lightweight real-time code quality/perf/security analysis during indexing"
    )
    monitoring_analysis_depth: str = Field(
        default="quick",
        description="Analysis depth: 'quick' (regex/heuristics) or 'full' (external linters when available)"
    )
    monitoring_async: bool = Field(
        default=True,
        description="Run monitoring callbacks asynchronously to avoid blocking indexing"
    )

    # Code generation (feature-flagged)
    enable_code_generation: bool = Field(
        default=False,
        description="Enable AI-assisted code/test/doc generation tools (safe, additive)"
    )
    code_generation_provider: str = Field(
        default="local",
        description="Provider for code generation: 'local' (heuristic) or 'ollama'"
    )
    code_generation_model: str = Field(
        default="codellama:7b",
        description="Model name when using Ollama provider"
    )

    # Advanced caching (feature-flagged)
    enable_predictive_caching: bool = Field(
        default=False,
        description="Enable predictive embedding caching based on recent query patterns",
    )
    enable_cache_warming: bool = Field(
        default=False,
        description="Warm a small set of common texts on startup to reduce first-hit latency",
    )


    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
