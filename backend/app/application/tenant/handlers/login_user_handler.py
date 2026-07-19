from __future__ import annotations

from backend.app.application.shared.command_handler import ICommandHandler
from backend.app.application.tenant.commands.login_user import LoginUserCommand
from backend.app.application.tenant.handlers.results import LoginResult
from backend.app.domain.tenant.value_objects.email import Email
from backend.app.domain.tenant.repositories.user_repository_interface import IUserRepository
from backend.app.domain.shared.exceptions.domain_exception import DomainException
from backend.app.infrastructure.security.password_hasher import IPasswordHasher


class LoginUserHandler(ICommandHandler[LoginUserCommand, LoginResult]):
    """Authenticate a user and return a JWT access token."""

    def __init__(
        self,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher,
        jwt_handler,
    ) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher
        self._jwt_handler = jwt_handler

    async def handle(self, command: LoginUserCommand) -> LoginResult:
        email = Email(address=command.email)
        user = await self._user_repo.get_by_email(email, command.tenant_id)

        if not user:
            raise DomainException("Invalid email or password", code="AUTH_FAILED")
        if not user.is_active:
            raise DomainException("Account is inactive", code="ACCOUNT_INACTIVE")
        if not self._password_hasher.verify(command.password, user.hashed_password):
            raise DomainException("Invalid email or password", code="AUTH_FAILED")

        # Build extra JWT claims for supplier / client portal users.
        # Both methods are now formally declared on IUserRepository.
        extra: dict = {}
        sid = await self._user_repo.get_supplier_id_for_user(user.id, command.tenant_id)
        if sid:
            extra["sid"] = str(sid)
        cid = await self._user_repo.get_client_id_for_user(user.id, command.tenant_id)
        if cid:
            extra["cid"] = str(cid)

        access_token = self._jwt_handler.create_access_token(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            role=user.role,
            extra_claims=extra or None,
        )

        return LoginResult(
            access_token=access_token,
            token_type="bearer",
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            email=str(user.email),
            role=user.role,
            full_name=user.full_name,
        )
