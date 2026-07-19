from __future__ import annotations

from backend.app.application.shared.command_handler import ICommandHandler
from backend.app.application.tenant.commands.register_tenant import RegisterTenantCommand
from backend.app.application.tenant.handlers.results import RegisterTenantResult
from backend.app.domain.tenant.entities.tenant import Tenant
from backend.app.domain.tenant.entities.user import User
from backend.app.domain.tenant.value_objects.email import Email
from backend.app.domain.tenant.value_objects.role import Role
from backend.app.domain.tenant.events.tenant_created import TenantCreated
from backend.app.domain.tenant.events.user_created import UserCreated
from backend.app.domain.tenant.repositories.tenant_repository_interface import ITenantRepository
from backend.app.domain.tenant.repositories.user_repository_interface import IUserRepository
from backend.app.domain.shared.exceptions.business_rule_violation import BusinessRuleViolationException
from backend.app.domain.shared.interfaces.unit_of_work_interface import IUnitOfWork
from backend.app.infrastructure.security.password_hasher import IPasswordHasher


class RegisterTenantHandler(ICommandHandler[RegisterTenantCommand, RegisterTenantResult]):
    """
    Creates a new Tenant and its first admin User in a single transaction.

    Publishes TenantCreated and UserCreated domain events after commit.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        tenant_repo: ITenantRepository,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher,
        jwt_handler,  # Injected from container — avoids circular import
    ) -> None:
        self._uow = uow
        self._tenant_repo = tenant_repo
        self._user_repo = user_repo
        self._password_hasher = password_hasher
        self._jwt_handler = jwt_handler

    async def handle(self, command: RegisterTenantCommand) -> RegisterTenantResult:
        # Step 1: Check slug uniqueness
        if await self._tenant_repo.slug_exists(command.slug):
            raise BusinessRuleViolationException(
                rule="Tenant slug already exists",
                details=f"'{command.slug}' is already taken",
            )

        # Step 2: Create Tenant aggregate
        tenant = Tenant(
            name=command.name,
            slug=command.slug,
            plan=command.plan,
        )

        # Step 3: Hash password and create admin User
        hashed_pw = self._password_hasher.hash(command.admin_password)
        user = User(
            tenant_id=tenant.id,
            email=Email(address=command.admin_email),
            hashed_password=hashed_pw,
            first_name=command.admin_first_name,
            last_name=command.admin_last_name,
            role=Role.ADMIN,
        )

        # Step 4: Register domain events on aggregates
        tenant.add_domain_event(
            TenantCreated(
                aggregate_id=tenant.id,
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                slug=tenant.slug,
                admin_email=command.admin_email,
                correlation_id=command.correlation_id,
            )
        )
        user.add_domain_event(
            UserCreated(
                aggregate_id=user.id,
                tenant_id=tenant.id,
                user_email=command.admin_email,
                user_role=Role.ADMIN.value,
                correlation_id=command.correlation_id,
            )
        )

        # Step 5: Persist in single transaction (UoW dispatches events on commit)
        async with self._uow:
            await self._tenant_repo.save(tenant)
            await self._user_repo.save(user)
            await self._uow.commit()

        # Step 6: Generate JWT access token
        access_token = self._jwt_handler.create_access_token(
            user_id=str(user.id),
            tenant_id=str(tenant.id),
            role=user.role,
        )

        return RegisterTenantResult(
            tenant_id=str(tenant.id),
            tenant_name=tenant.name,
            slug=tenant.slug,
            user_id=str(user.id),
            email=command.admin_email,
            role=user.role,
            access_token=access_token,
        )
