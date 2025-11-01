"""
Indexing Database Models

SQLAlchemy models for file metadata storage.
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, BigInteger, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.config.settings import settings

Base = declarative_base()


class FileMetadata(Base):
    """
    File Metadata Model

    Stores metadata for indexed files including paths, types, and timestamps.
    """

    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String(1024), unique=True, nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False, index=True)
    extension = Column(String(20), nullable=False)
    size = Column(BigInteger, nullable=False)
    modified_time = Column(DateTime, nullable=False, index=True)
    created_time = Column(DateTime, nullable=True)
    indexed_time = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    status = Column(String(20), nullable=False, default="indexed", index=True)

    def __repr__(self):
        return f"<FileMetadata(id={self.id}, file_path='{self.file_path}', file_type='{self.file_type}')>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "extension": self.extension,
            "size": self.size,
            "modified_time": (
                self.modified_time.isoformat() if self.modified_time else None
            ),
            "created_time": (
                self.created_time.isoformat() if self.created_time else None
            ),
            "indexed_time": (
                self.indexed_time.isoformat() if self.indexed_time else None
            ),
            "status": self.status,
        }


# Database engine and session
engine = None
SessionLocal = None


def init_db():
    """Initialize database connection and create tables"""
    global engine, SessionLocal

    if engine is None:
        engine = create_engine(
            settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=10
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create tables
        Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    if SessionLocal is None:
        init_db()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# CRUD Operations


async def create_file_metadata(metadata: dict) -> Optional[FileMetadata]:
    """
    Create file metadata record

    Args:
        metadata: File metadata dictionary

    Returns:
        FileMetadata: Created record or None if failed
    """
    if SessionLocal is None:
        init_db()

    db = SessionLocal()
    try:
        file_metadata = FileMetadata(
            file_path=metadata["file_path"],
            file_name=metadata["file_name"],
            file_type=metadata["file_type"],
            extension=metadata["extension"],
            size=metadata["size"],
            modified_time=metadata["modified_time"],
            created_time=metadata.get("created_time"),
            indexed_time=metadata.get("indexed_time", datetime.now(timezone.utc)),
            status=metadata.get("status", "indexed"),
        )

        db.add(file_metadata)
        db.commit()
        db.refresh(file_metadata)

        return file_metadata

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


async def update_file_metadata(
    file_path: str, metadata: dict
) -> Optional[FileMetadata]:
    """
    Update file metadata record

    Args:
        file_path: Path to file
        metadata: Updated metadata dictionary

    Returns:
        FileMetadata: Updated record or None if not found
    """
    if SessionLocal is None:
        init_db()

    db = SessionLocal()
    try:
        file_metadata = (
            db.query(FileMetadata).filter(FileMetadata.file_path == file_path).first()
        )

        if not file_metadata:
            return None

        # Update fields
        for key, value in metadata.items():
            if hasattr(file_metadata, key):
                setattr(file_metadata, key, value)

        file_metadata.indexed_time = datetime.now(timezone.utc)

        db.commit()
        db.refresh(file_metadata)

        return file_metadata

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


async def delete_file_metadata(file_path: str) -> bool:
    """
    Delete file metadata record

    Args:
        file_path: Path to file

    Returns:
        bool: True if deleted, False if not found
    """
    if SessionLocal is None:
        init_db()

    db = SessionLocal()
    try:
        file_metadata = (
            db.query(FileMetadata).filter(FileMetadata.file_path == file_path).first()
        )

        if not file_metadata:
            return False

        db.delete(file_metadata)
        db.commit()

        return True

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


async def get_file_metadata(file_path: str) -> Optional[FileMetadata]:
    """
    Get file metadata record

    Args:
        file_path: Path to file

    Returns:
        FileMetadata: Record or None if not found
    """
    if SessionLocal is None:
        init_db()

    db = SessionLocal()
    try:
        return (
            db.query(FileMetadata).filter(FileMetadata.file_path == file_path).first()
        )
    finally:
        db.close()


async def get_all_file_metadata(limit: int = 100, offset: int = 0) -> list:
    """
    Get all file metadata records

    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        list: List of FileMetadata records
    """
    if SessionLocal is None:
        init_db()

    db = SessionLocal()
    try:
        return db.query(FileMetadata).limit(limit).offset(offset).all()
    finally:
        db.close()


async def get_metadata_stats() -> dict:
    """
    Get metadata statistics

    Returns:
        dict: Statistics about indexed files
    """
    if SessionLocal is None:
        init_db()

    db = SessionLocal()
    try:
        total_files = db.query(FileMetadata).count()

        # Count by file type
        by_type = {}
        for file_type, count in (
            db.query(FileMetadata.file_type, func.count(FileMetadata.id))
            .group_by(FileMetadata.file_type)
            .all()
        ):
            by_type[file_type] = count

        # Count by status
        by_status = {}
        for status, count in (
            db.query(FileMetadata.status, func.count(FileMetadata.id))
            .group_by(FileMetadata.status)
            .all()
        ):
            by_status[status] = count

        return {"total_files": total_files, "by_type": by_type, "by_status": by_status}

    finally:
        db.close()


# Import func for aggregation
from sqlalchemy import func
