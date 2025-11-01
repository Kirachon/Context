"""
Unit tests for RBAC Authz (Story 4-1)
"""
import pytest
from src.security.authz import set_role, get_role, require_role, Roles


@pytest.mark.asyncio
async def test_require_role_allows_and_denies():
    set_role(Roles.DEVELOPER)

    @require_role([Roles.DEVELOPER, Roles.ADMIN])
    async def dev_action():
        return "ok"

    assert await dev_action() == "ok"

    set_role(Roles.VIEWER)

    with pytest.raises(PermissionError):
        await dev_action()

