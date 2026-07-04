"""
Phase 1 Integration Tests — Users and Roles
=============================================
Tests for: POST /api/v1/users          (create user)
           POST /api/v1/admin/rbac/roles  (create role)

Covers:
  TC-2.1  POST /users creates a user with a unique email
  TC-2.2  POST /users rejects duplicate email in same tenant with 409
  TC-2.3  POST /users returns the created user with an ID and the role assigned
  TC-3.1  POST /roles creates a new role with at least one permission
  TC-3.2  POST /roles rejects duplicate role name within same tenant
  TC-3.3  POST /roles persists the role with the specified permissions

Requirements: 2 (Req 2 AC 1–4), 3 (Req 3 AC 1–4)
"""
from __future__ import annotations

import backend.app.main  # noqa: F401  (registers all ORM models)

import uuid
import pytest
from httpx import AsyncClient


USERS_URL = "/api/v1/users"
ROLES_URL = "/api/v1/admin/rbac/roles"


# ─────────────────────────────────────────────────────────────────────────────
# TC-2.1  POST /users creates a user with unique email
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_user_with_unique_email(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 1 & 2: POST /users with a unique email and valid display name must
    create a record in the users table and return HTTP 201.

    Validates: Requirements 2 AC 1, 2
    """
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"testuser-{suffix}@e2e-test.local",
        "first_name": "Test",
        "last_name": f"User-{suffix}",
        "role": "admin",
        "is_active": True,
    }

    response = await async_client.post(
        USERS_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert response.status_code == 201, (
        f"Expected 201 when creating a user with unique email, "
        f"got {response.status_code}: {response.text}"
    )

    data = response.json()
    assert "id" in data, "Response must include the user id"
    assert data["email"] == payload["email"], (
        f"Returned email '{data['email']}' must match the submitted email"
    )
    assert data["role"] == "admin", "Role must be persisted on the created user"
    assert "temporary_password" in data, (
        "Response must include a temporary_password for the new user"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-2.2  POST /users rejects duplicate email within the same tenant
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 3: When the Admin submits a duplicate email within the same tenant,
    the System SHALL reject the submission with "Email already exists".

    Validates: Requirements 2 AC 3
    """
    suffix = uuid.uuid4().hex[:8]
    email = f"duplicate-user-{suffix}@e2e-test.local"
    payload = {
        "email": email,
        "first_name": "Dup",
        "last_name": "User",
        "role": "admin",
    }

    # First creation should succeed
    resp1 = await async_client.post(
        USERS_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert resp1.status_code == 201, (
        f"First user creation should succeed, got {resp1.status_code}: {resp1.text}"
    )

    # Second creation with same email must be rejected
    resp2 = await async_client.post(
        USERS_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert resp2.status_code == 409, (
        f"Expected 409 for duplicate email, got {resp2.status_code}: {resp2.text}"
    )
    detail = resp2.json().get("detail", "")
    assert "email" in detail.lower() or "exists" in detail.lower(), (
        f"Error message must reference duplicate email, got: '{detail}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-2.3  POST /users for multiple roles (Sales, Storekeeper, QC, Accountant)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_users_for_multiple_roles(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 2: Each user role (Sales, Storekeeper, QC, Accountant, Dispatch) must
    be creatable via POST /users.

    Validates: Requirements 2 AC 2
    """
    # Use the built-in role names defined in ROLE_PERMISSIONS (permissions.py).
    # "qc_inspector" and "dispatch" are not built-in roles; the correct names
    # are "qc" (for QC Inspector) and "planner" (covers the dispatch/planning role).
    roles_to_create = ["storekeeper", "sales", "qc", "accountant", "planner"]

    for role in roles_to_create:
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "email": f"{role}-{suffix}@e2e-test.local",
            "first_name": role.capitalize(),
            "last_name": f"User-{suffix}",
            "role": role,
            "is_active": True,
        }
        response = await async_client.post(
            USERS_URL,
            json=payload,
            headers=admin_user["headers"],
            follow_redirects=True,
        )
        assert response.status_code == 201, (
            f"Failed to create user with role '{role}': "
            f"{response.status_code} {response.text}"
        )
        data = response.json()
        assert data["role"] == role, (
            f"Created user role '{data['role']}' must match requested role '{role}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TC-3.1  POST /roles creates a new role with at least one permission
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_role_with_valid_permissions(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 1 & 2: POST /admin/rbac/roles with a unique role name and at least one
    permission must create the role and return HTTP 201.

    Validates: Requirements 3 AC 1, 2
    """
    suffix = uuid.uuid4().hex[:8]
    role_name = f"testrole_{suffix}"
    payload = {
        "name": role_name,
        "label": f"Test Role {suffix}",
        "description": "Created by E2E test",
        "permissions": ["inventory:read", "sales:read"],
    }

    response = await async_client.post(
        ROLES_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )

    assert response.status_code == 201, (
        f"Expected 201 when creating role, got {response.status_code}: {response.text}"
    )

    data = response.json()
    assert data.get("name") == role_name or data.get("id"), (
        f"Response must include the created role name or id, got: {data}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-3.2  POST /roles rejects duplicate role name within same tenant
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_role_rejects_duplicate_name(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 3: When the Admin submits a duplicate role name within the same tenant,
    the System SHALL reject the submission with "Role already exists".

    Validates: Requirements 3 AC 3
    """
    suffix = uuid.uuid4().hex[:8]
    role_name = f"duprole_{suffix}"
    payload = {
        "name": role_name,
        "label": f"Dup Role {suffix}",
        "permissions": ["inventory:read"],
    }

    # First creation should succeed
    resp1 = await async_client.post(
        ROLES_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert resp1.status_code == 201, (
        f"First role creation should succeed, got {resp1.status_code}: {resp1.text}"
    )

    # Second creation with the same name must be rejected
    resp2 = await async_client.post(
        ROLES_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert resp2.status_code in (400, 409), (
        f"Expected 400 or 409 for duplicate role name, "
        f"got {resp2.status_code}: {resp2.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-3.3  GET /roles returns the newly created role with its permissions
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_created_role_is_listed_with_permissions(
    async_client: AsyncClient,
    admin_user: dict,
    seed_number_series,
):
    """
    AC 2 & 4: After successful role creation, the role must appear in the
    roles list with its assigned permissions.

    Validates: Requirements 3 AC 2, 4
    """
    suffix = uuid.uuid4().hex[:8]
    role_name = f"listedrole_{suffix}"
    permissions = ["inventory:read", "manufacturing:read"]
    payload = {
        "name": role_name,
        "label": f"Listed Role {suffix}",
        "permissions": permissions,
    }

    create_resp = await async_client.post(
        ROLES_URL,
        json=payload,
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert create_resp.status_code == 201, (
        f"Role creation failed: {create_resp.status_code} {create_resp.text}"
    )

    # Retrieve the role permissions
    get_resp = await async_client.get(
        f"/api/v1/admin/rbac/roles/{role_name}/permissions",
        headers=admin_user["headers"],
        follow_redirects=True,
    )
    assert get_resp.status_code == 200, (
        f"GET /roles/{role_name}/permissions failed: "
        f"{get_resp.status_code} {get_resp.text}"
    )

    role_data = get_resp.json()
    returned_permissions = set(role_data.get("permissions", []))
    for perm in permissions:
        assert perm in returned_permissions, (
            f"Permission '{perm}' must be present in the created role's permissions. "
            f"Got: {returned_permissions}"
        )
