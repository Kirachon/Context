from __future__ import annotations

from typing import Dict


TEMPLATES: Dict[str, str] = {
    "crud_api": (
        """
# CRUD API Template (FastAPI)

from fastapi import APIRouter

router = APIRouter()

@router.get("/{item_id}")
def read_item(item_id: int):
    return {"id": item_id}

@router.post("/")
def create_item(payload: dict):
    return {"id": 1, **payload}
"""
    ).strip(),
    "pytest_test": (
        """
# Pytest Test Template

import pytest

def test_subject():
    # TODO: implement
    assert True
"""
    ).strip(),
}

