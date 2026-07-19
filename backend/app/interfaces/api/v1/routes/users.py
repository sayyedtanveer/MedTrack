"""User management API endpoints."""

from __future__ import annotations

import secrets
import string
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.infrastructure.persistence.models.sales_models import ClientModel
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_tenant_id,
    get_container,
)
from backend.app.application.rbac.service import get_effective_role_permissions
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.auth_schemas import (
    UserInMeResponse,
)
from pydantic import BaseModel, Field

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreateRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool = True
    supplier_id: Optional[str] = None  # Link to supplier if creating supplier portal user
    client_id: Optional[str] = None  # Link to client if creating client portal user


class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    supplier_id: Optional[str] = None
    client_id: Optional[str] = None


class UserCreateResponse(BaseModel):
    """Response when creating a user - includes temporary password."""
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    tenant_id: str
    is_active: bool
    supplier_id: Optional[str] = None
    client_id: Optional[str] = None
    temporary_password: str = Field(
        description="Temporary password for first login. User must change this after login."
    )


class UserTemporaryPasswordResponse(BaseModel):
    """Response when an admin regenerates a temporary password."""
    id: str
    email: str
    role: str
    tenant_id: str
    is_active: bool
    supplier_id: Optional[str] = None
    client_id: Optional[str] = None
    temporary_password: str = Field(
        description="New temporary password. It is shown once and cannot be retrieved later."
    )


def _generate_temporary_password(length: int = 12) -> str:
    """Generate a secure random temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def _user_response(user: UserModel) -> UserInMeResponse:
    return UserInMeResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        tenant_id=str(user.tenant_id),
        is_active=user.is_active,
        supplier_id=str(user.supplier_id) if user.supplier_id else None,
        client_id=str(user.client_id) if user.client_id else None,
    )


@router.get(
    "",
    response_model=List[UserInMeResponse],
    dependencies=[Depends(require_permission("user:read"))],
    summary="List all users in tenant",
)
async def list_users(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    search: Optional[str] = Query(None, description="Search by email or name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    """Get all users for the current tenant with optional filtering."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(UserModel).where(
            UserModel.tenant_id == tenant_id,
            UserModel.is_deleted.is_(False),
        )

        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                (UserModel.email.ilike(search_pattern))
                | (UserModel.first_name.ilike(search_pattern))
                | (UserModel.last_name.ilike(search_pattern))
            )

        if role:
            stmt = stmt.where(UserModel.role == role)

        if is_active is not None:
            stmt = stmt.where(UserModel.is_active == is_active)

        result = await session.execute(stmt)
        users = result.scalars().all()

        # Convert to response model with explicit field mapping
        user_responses = [
            UserInMeResponse(
                id=str(u.id),
                email=u.email,
                first_name=u.first_name,
                last_name=u.last_name,
                role=u.role,
                tenant_id=str(u.tenant_id),
                is_active=u.is_active,
                supplier_id=str(u.supplier_id) if u.supplier_id else None,
                client_id=str(u.client_id) if u.client_id else None,
            )
            for u in users
        ]

    return user_responses


@router.get(
    "/{user_id}",
    response_model=UserInMeResponse,
    dependencies=[Depends(require_permission("user:read"))],
    summary="Get user by ID",
)
async def get_user(
    user_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get a specific user in the current tenant."""
    container = get_container(request)
    async with container.session_factory() as session:
        result = await session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id,
                UserModel.is_deleted.is_(False),
            )
        )
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return _user_response(user)


@router.post(
    "",
    response_model=UserCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user:write"))],
    summary="Create a new user",
)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Create a new user in the current tenant with a temporary password."""
    container = get_container(request)

    async with container.session_factory() as session:
        # Check if email already exists
        result = await session.execute(
            select(UserModel).where(
                UserModel.tenant_id == tenant_id,
                UserModel.email == body.email,
                UserModel.is_deleted.is_(False),
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already exists")

        role_name = body.role.strip().lower()
        effective_role = await get_effective_role_permissions(session, tenant_id, role_name)
        if not effective_role.permissions:
            raise HTTPException(status_code=400, detail=f"Role '{body.role}' does not exist")

        # CRITICAL: If supplier_id provided, validate it belongs to current tenant
        supplier_id_value = None
        if body.supplier_id:
            try:
                supplier_uuid = uuid.UUID(body.supplier_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid supplier_id format")
            
            supplier = await session.get(SupplierModel, supplier_uuid)
            if not supplier or supplier.tenant_id != tenant_id or supplier.is_deleted:
                raise HTTPException(status_code=404, detail="Supplier not found")
            supplier_id_value = supplier_uuid

        # CRITICAL: If client_id provided, validate it belongs to current tenant
        client_id_value = None
        if body.client_id:
            try:
                client_uuid = uuid.UUID(body.client_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid client_id format")

            client = await session.get(ClientModel, client_uuid)
            if not client or client.tenant_id != tenant_id or client.is_deleted:
                raise HTTPException(status_code=404, detail="Client not found")
            client_id_value = client_uuid

        # Generate secure temporary password
        temporary_password = _generate_temporary_password()
        
        # Create user with hashed temporary password
        user = UserModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            role=role_name,
            is_active=body.is_active,
            hashed_password=container.password_hasher.hash(temporary_password),
            supplier_id=supplier_id_value,  # Set supplier_id if provided
            client_id=client_id_value,  # Set client_id if provided
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    if supplier_id_value:
        await container.audit_service.log_action(
            action="SUPPLIER_USER_CREATED",
            entity_type="user",
            entity_id=user.id,
            after_value={
                "email": user.email,
                "role": user.role,
                "supplier_id": str(supplier_id_value),
                "is_active": user.is_active,
            },
            extra={
                "source": "business_event",
                "module": "administration",
                "business_step": "Supplier portal access",
                "summary": f"Supplier portal login created for {user.email}",
                "document_no": user.email,
                "supplier_id": str(supplier_id_value),
            },
        )

    if client_id_value:
        await container.audit_service.log_action(
            action="CLIENT_USER_CREATED",
            entity_type="user",
            entity_id=user.id,
            after_value={
                "email": user.email,
                "role": user.role,
                "client_id": str(client_id_value),
                "is_active": user.is_active,
            },
            extra={
                "source": "business_event",
                "module": "sales",
                "business_step": "Client portal access",
                "summary": f"Client portal login created for {user.email}",
                "document_no": user.email,
                "client_id": str(client_id_value),
            },
        )

    # Return response with temporary password (only shown at creation time)
    return UserCreateResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        tenant_id=str(user.tenant_id),
        is_active=user.is_active,
        supplier_id=str(user.supplier_id) if user.supplier_id else None,
        client_id=str(user.client_id) if user.client_id else None,
        temporary_password=temporary_password,
    )


@router.put(
    "/{user_id}",
    response_model=UserInMeResponse,
    dependencies=[Depends(require_permission("user:write"))],
    summary="Update user",
)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Update a user in the current tenant."""
    container = get_container(request)

    async with container.session_factory() as session:
        normalized_role = None
        if body.role is not None:
            normalized_role = body.role.strip().lower()
            effective_role = await get_effective_role_permissions(session, tenant_id, normalized_role)
            if not effective_role.permissions:
                raise HTTPException(status_code=400, detail=f"Role '{normalized_role}' does not exist")

        result = await session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id,
                UserModel.is_deleted.is_(False),
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # CRITICAL: If supplier_id provided, validate it belongs to current tenant
        if body.supplier_id is not None:
            try:
                supplier_uuid = uuid.UUID(body.supplier_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid supplier_id format")
            
            supplier = await session.get(SupplierModel, supplier_uuid)
            if not supplier or supplier.tenant_id != tenant_id or supplier.is_deleted:
                raise HTTPException(status_code=404, detail="Supplier not found")
            user.supplier_id = supplier_uuid
        elif "supplier_id" in body.model_fields_set:
            user.supplier_id = None

        # CRITICAL: If client_id provided, validate it belongs to current tenant
        if body.client_id is not None:
            try:
                client_uuid = uuid.UUID(body.client_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid client_id format")

            client = await session.get(ClientModel, client_uuid)
            if not client or client.tenant_id != tenant_id or client.is_deleted:
                raise HTTPException(status_code=404, detail="Client not found")
            user.client_id = client_uuid
        elif "client_id" in body.model_fields_set:
            user.client_id = None
        
        # Update other fields (normalize role to lowercase)
        data = body.model_dump(exclude_unset=True)
        for key, value in data.items():
            if key in {"supplier_id", "client_id"}:
                continue  # Already handled above
            if key == "email" and isinstance(value, str):
                value = value.strip().lower()
                if not value:
                    raise HTTPException(status_code=400, detail="Email is required")
                existing = await session.scalar(
                    select(UserModel.id).where(
                        UserModel.tenant_id == tenant_id,
                        UserModel.email == value,
                        UserModel.id != user_id,
                        UserModel.is_deleted.is_(False),
                    )
                )
                if existing:
                    raise HTTPException(status_code=409, detail="Email already exists")
            if key == "role" and isinstance(value, str):
                value = normalized_role or value.strip().lower()
            setattr(user, key, value)

        await session.commit()
        await session.refresh(user)

    return _user_response(user)


@router.post(
    "/{user_id}/temporary-password",
    response_model=UserTemporaryPasswordResponse,
    dependencies=[Depends(require_permission("user:write"))],
    summary="Regenerate a user's temporary password",
)
async def regenerate_temporary_password(
    user_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Generate a new temporary password for an existing user in the current tenant."""
    container = get_container(request)
    temporary_password = _generate_temporary_password()

    async with container.session_factory() as session:
        result = await session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id,
                UserModel.is_deleted.is_(False),
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.hashed_password = container.password_hasher.hash(temporary_password)
        await session.commit()
        await session.refresh(user)

    await container.audit_service.log_action(
        action="USER_TEMP_PASSWORD_REGENERATED",
        entity_type="user",
        entity_id=user.id,
        after_value={
            "email": user.email,
            "role": user.role,
            "supplier_id": str(user.supplier_id) if user.supplier_id else None,
            "client_id": str(user.client_id) if user.client_id else None,
            "is_active": user.is_active,
        },
        extra={
            "source": "admin_action",
            "module": "administration",
            "business_step": "User password recovery",
            "summary": f"Temporary password regenerated for {user.email}",
            "document_no": user.email,
        },
    )

    return UserTemporaryPasswordResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        tenant_id=str(user.tenant_id),
        is_active=user.is_active,
        supplier_id=str(user.supplier_id) if user.supplier_id else None,
        client_id=str(user.client_id) if user.client_id else None,
        temporary_password=temporary_password,
    )
