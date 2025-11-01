"""
Unit tests for Model Manager (Story 5-2)
"""
from src.ai_processing.model_manager import get_model_manager


def test_model_register_and_set_default():
    mm = get_model_manager()
    mm.register_model("gemma")
    mm.set_default_model("gemma")
    assert mm.get_default_model() == "gemma"
    assert "gemma" in mm.list_models()

