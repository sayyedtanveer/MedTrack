import asyncio, sys, pathlib
sys.path.insert(0, '.')

EMAIL = "admin.e2e@medtrack-demo.com"
TENANT_ID = "b5ef68c4-18be-4fa6-a439-a23c34877550"
NEW_PASSWORD = "Admin@1234"
OUT = pathlib.Path("tmp_reset_result.txt")

async def main():
    lines = []
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text
    from backend.app.config import get_settings
    from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher
    from backend.app.infrastructure.security.jwt_handler import JWTHandler
    from backend.app.infrastructure.persistence.repositories.user_repository import UserRepository
    from backend.app.application.tenant.handlers.login_user_handler import LoginUserHandler
    from backend.app.application.tenant.commands.login_user import LoginUserCommand
    import uuid

    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, echo=False)
    hasher = BcryptPasswordHasher()

    hashed = hasher.hash(NEW_PASSWORD)
    async with engine.begin() as conn:
        r = await conn.execute(
            text("UPDATE users SET hashed_password = :hp WHERE email = :email AND tenant_id = :tid"),
            {"hp": hashed, "email": EMAIL, "tid": TENANT_ID}
        )
        lines.append(f"Rows updated: {r.rowcount}")

    async with AsyncSession(engine) as session:
        jwt = JWTHandler(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expiry_minutes=settings.jwt_expiry_minutes,
        )
        handler = LoginUserHandler(user_repo=UserRepository(session), password_hasher=hasher, jwt_handler=jwt)
        try:
            cmd = LoginUserCommand(email=EMAIL, password=NEW_PASSWORD, tenant_id=uuid.UUID(TENANT_ID))
            result = await handler.handle(cmd)
            lines.append("LOGIN: SUCCESS")
            lines.append(f"Email:     {EMAIL}")
            lines.append(f"Password:  {NEW_PASSWORD}")
            lines.append(f"Tenant ID: {TENANT_ID}")
            lines.append(f"Role:      {result.role}")
            lines.append(f"Token:     {result.access_token[:60]}...")
        except Exception as e:
            lines.append(f"LOGIN FAILED: {e}")

    await engine.dispose()
    OUT.write_text("\n".join(lines))

asyncio.run(main())
