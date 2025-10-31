"""
Qdrant Client Service

Manages connection to Qdrant vector database with health checks and retry logic.
"""

import asyncio
import logging
import os
import sys
from typing import Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from qdrant_client import QdrantClient
from qdrant_client.http import models
from src.config.settings import settings

logger = logging.getLogger(__name__)


class QdrantClientService:
    """
    Qdrant Client Service
    
    Manages connection to Qdrant vector database with health monitoring.
    """
    
    def __init__(self):
        """Initialize Qdrant client service"""
        self.client: Optional[QdrantClient] = None
        self.is_connected = False
        self.connection_attempts = 0
        self.max_retries = 3
        
        logger.info(f"QdrantClientService initialized for {settings.qdrant_host}:{settings.qdrant_port}")
    
    async def connect(self) -> bool:
        """
        Connect to Qdrant database
        
        Returns:
            bool: True if connection successful
        """
        if self.is_connected:
            logger.warning("Already connected to Qdrant")
            return True
        
        logger.info("Connecting to Qdrant...")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                self.connection_attempts = attempt
                
                # Create Qdrant client
                self.client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                    api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
                    timeout=10.0
                )
                
                # Test connection with health check
                health = await self.health_check()
                
                if health.get("status") == "healthy":
                    self.is_connected = True
                    logger.info(f"Successfully connected to Qdrant (attempt {attempt}/{self.max_retries})")
                    return True
                else:
                    logger.warning(f"Qdrant health check failed (attempt {attempt}/{self.max_retries})")
                
            except Exception as e:
                logger.error(f"Connection attempt {attempt}/{self.max_retries} failed: {e}")
                
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        logger.error("Failed to connect to Qdrant after all retries")
        self.is_connected = False
        return False
    
    async def disconnect(self):
        """Disconnect from Qdrant database"""
        if not self.is_connected:
            logger.warning("Not connected to Qdrant")
            return
        
        logger.info("Disconnecting from Qdrant...")
        
        try:
            if self.client:
                self.client.close()
            
            self.is_connected = False
            self.client = None
            logger.info("Disconnected from Qdrant successfully")
            
        except Exception as e:
            logger.error(f"Error disconnecting from Qdrant: {e}", exc_info=True)
    
    async def health_check(self) -> dict:
        """
        Check Qdrant health status
        
        Returns:
            dict: Health status information
        """
        if not self.client:
            return {
                "status": "disconnected",
                "message": "Client not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            # Get Qdrant health info
            health_info = self.client.get_collections()
            
            return {
                "status": "healthy",
                "connected": self.is_connected,
                "collections_count": len(health_info.collections),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_client(self) -> Optional[QdrantClient]:
        """
        Get Qdrant client instance
        
        Returns:
            QdrantClient: Client instance or None if not connected
        """
        if not self.is_connected:
            logger.warning("Attempting to get client while not connected")
            return None
        
        return self.client
    
    def get_status(self) -> dict:
        """
        Get connection status
        
        Returns:
            dict: Connection status information
        """
        return {
            "connected": self.is_connected,
            "host": settings.qdrant_host,
            "port": settings.qdrant_port,
            "connection_attempts": self.connection_attempts,
            "max_retries": self.max_retries
        }


# Global Qdrant client instance
qdrant_client_service = QdrantClientService()


async def connect_qdrant() -> bool:
    """Connect to Qdrant (entry point for integration)"""
    return await qdrant_client_service.connect()


async def disconnect_qdrant():
    """Disconnect from Qdrant (entry point for integration)"""
    await qdrant_client_service.disconnect()


def get_qdrant_client() -> Optional[QdrantClient]:
    """Get Qdrant client instance (entry point for operations)"""
    return qdrant_client_service.get_client()


async def get_qdrant_status() -> dict:
    """Get Qdrant status (entry point for health checks)"""
    health = await qdrant_client_service.health_check()
    status = qdrant_client_service.get_status()
    
    return {
        **status,
        "health": health
    }

