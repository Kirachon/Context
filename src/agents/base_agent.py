"""
Base agent class for all autonomous agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional
from .models import AgentContext

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all autonomous agents.

    All agents inherit from this class and implement the execute method.
    """

    def __init__(self, context: AgentContext):
        """
        Initialize the agent.

        Args:
            context: Agent execution context
        """
        self.context = context
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute the agent's primary function.

        Must be implemented by subclasses.

        Returns:
            Agent-specific result object
        """
        pass

    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)

    def log_error(self, message: str, exc_info=None):
        """Log error message"""
        self.logger.error(message, exc_info=exc_info)

    def log_debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)

    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
