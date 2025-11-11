"""Database connection and session management for Memory System."""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from src.memory.models import Base


class DatabaseManager:
    """Manage database connections and sessions."""

    def __init__(self, database_url: str = None):
        """Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL. If not provided,
                         reads from DATABASE_URL environment variable.
        """
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'postgresql://context:context@localhost:5432/context'
        )

        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            echo=False,  # Set to True for SQL logging
            pool_pre_ping=True,  # Verify connections before using
            pool_size=5,
            max_overflow=10,
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def create_tables(self):
        """Create all tables defined in models."""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all tables (use with caution!)."""
        Base.metadata.drop_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope for database operations.

        Yields:
            Session: SQLAlchemy session for database operations

        Example:
            with db_manager.get_session() as session:
                conversation = Conversation(...)
                session.add(conversation)
                session.commit()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database manager instance
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Get or create the global database manager instance.

    Returns:
        DatabaseManager: Global database manager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database():
    """Initialize database by creating all tables."""
    db_manager = get_db_manager()
    db_manager.create_tables()
