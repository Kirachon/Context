"""
Model Manager (Epic 3)

Keeps track of active/default LLM model and parameters.
"""

import logging
from typing import Optional, Dict, Any

from src.config.settings import settings

logger = logging.getLogger(__name__)


class ModelManager:
    def __init__(self):
        self._default_model = settings.ollama_default_model
        self._params: Dict[str, Any] = {}

    def set_default_model(self, model: str):
        logger.info(f"Default model set to {model}")
        self._default_model = model

    def get_default_model(self) -> str:
        return self._default_model

    def set_params(self, **kwargs):
        self._params.update(kwargs)

    def get_params(self) -> Dict[str, Any]:
        return dict(self._params)


# Singleton
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager

