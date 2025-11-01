"""
Global test configuration for unit tests.
Mocks heavy external dependencies to keep tests lightweight and offline.
"""
import sys
from unittest.mock import Mock

# Mock Qdrant and model dependencies used by vector DB and embeddings
sys.modules.setdefault('qdrant_client', Mock())
sys.modules.setdefault('qdrant_client.http', Mock())
sys.modules.setdefault('qdrant_client.http.models', Mock())
sys.modules.setdefault('sentence_transformers', Mock())
sys.modules.setdefault('torch', Mock())

