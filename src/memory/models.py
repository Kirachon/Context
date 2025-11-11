"""SQLAlchemy models for Context Memory System.

This module defines the database schema for all four memory types:
- Conversations: Store user interactions with enhanced prompts
- Patterns: Store code patterns extracted from codebase
- Solutions: Store problem-solution pairs with success metrics
- Preferences: Store user coding style preferences
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

Base = declarative_base()


class Conversation(Base):
    """Store conversation history with enhanced prompts.

    Each conversation represents a user prompt, the enhanced context,
    and the response along with feedback metrics.
    """

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
        index=True
    )

    # Prompts
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    enhanced_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Analysis
    intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    entities: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Feedback
    feedback: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    resolution: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    helpful_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadata
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    context_sources: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
        Index("idx_intent", "intent"),
        Index("idx_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user={self.user_id}, intent={self.intent})>"


class CodePattern(Base):
    """Store code patterns extracted from codebase.

    Patterns represent common coding approaches like API design,
    error handling, testing patterns, etc.
    """

    __tablename__ = "code_patterns"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )

    # Pattern identification
    pattern_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Pattern content
    example_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signature: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Usage statistics
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_using: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    user_preference_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Metadata
    project_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_pattern_type", "pattern_type"),
        Index("idx_project_id", "project_id"),
        Index("idx_usage_count", "usage_count"),
    )

    def __repr__(self) -> str:
        return f"<CodePattern(id={self.id}, type={self.pattern_type}, name={self.name})>"


class Solution(Base):
    """Store problem-solution pairs with success metrics.

    Solutions represent successful approaches to problems,
    clustered by similarity for reuse.
    """

    __tablename__ = "solutions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()")
    )

    # Problem description
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    problem_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Solution
    solution_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    solution_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    files_affected: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metrics
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_resolution_time_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Clustering
    similar_problems: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Metadata
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_success_rate", "success_rate"),
        Index("idx_problem_type", "problem_type"),
        Index("idx_cluster_id", "cluster_id"),
        Index("idx_project_id", "project_id"),
    )

    def __repr__(self) -> str:
        return f"<Solution(id={self.id}, type={self.problem_type}, success={self.success_rate})>"


class UserPreference(Base):
    """Store user coding style preferences learned from git history.

    Preferences include indentation style, naming conventions,
    preferred libraries, testing approach, etc.
    """

    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Code style preferences
    code_style: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Indentation, naming conventions, comment style, etc."
    )

    # Library preferences
    preferred_libraries: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Preferred libraries by category (e.g., testing, http, async)"
    )

    # Development practices
    testing_approach: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="unit, integration, tdd, bdd, etc."
    )
    documentation_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="minimal, moderate, extensive"
    )

    # Language-specific preferences
    language_preferences: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Preferences by programming language"
    )

    # Project-specific overrides
    project_preferences: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Project-specific preference overrides"
    )

    # Metadata
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="How confident we are in these preferences (0-1)"
    )
    sample_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of commits analyzed"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<UserPreference(user_id={self.user_id}, confidence={self.confidence_score})>"
