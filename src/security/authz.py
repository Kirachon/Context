"""
RBAC Authorization (Story 4-1)

Simple role-based authorization helpers and decorator.
"""

import functools
from typing import Callable, Optional, List


class Roles:
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class AuthzState:
    """In-memory role store (for demo/testing)."""
    def __init__(self):
        self._role: str = Roles.DEVELOPER

    def set_role(self, role: str):
        if role not in {Roles.ADMIN, Roles.DEVELOPER, Roles.VIEWER}:
            raise ValueError("invalid role")
        self._role = role

    def get_role(self) -> str:
        return self._role


_authz_state = AuthzState()


def get_role() -> str:
    return _authz_state.get_role()


def set_role(role: str):
    _authz_state.set_role(role)


def require_role(allowed: List[str]) -> Callable:
    """Decorator requiring one of the roles."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if get_role() not in allowed:
                raise PermissionError("insufficient role")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

