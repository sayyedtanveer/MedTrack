from __future__ import annotations

from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from backend.app.config import Settings
from backend.app.infrastructure.persistence.database import create_engine, create_session_factory
from backend.app.infrastructure.security.jwt_handler import JWTHandler
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher, IPasswordHasher
from backend.app.infrastructure.storage.storage_interface import IStorageService
from backend.app.infrastructure.storage.local_storage_service import LocalStorageService
from backend.app.infrastructure.events.event_bus import InMemoryEventBus
from backend.app.infrastructure.events.event_dispatcher import EventDispatcher
from backend.app.infrastructure.websocket.connection_manager import ConnectionManager
from backend.app.infrastructure.tasks.background_task_service import BackgroundTaskService
from backend.app.infrastructure.audit.audit_service import AuditService
from backend.app.infrastructure.external.email_service import IEmailService, StubEmailService
from backend.app.infrastructure.logging.error_logger import ErrorLogger
from backend.app.infrastructure.logging.repository import ErrorLogRepository
from backend.app.application.notifications.notification_service import NotificationService


@dataclass
class Container:
    """
    Application-level Dependency Injection container.

    Instantiated ONCE in main.py lifespan and stored on app.state.container.
    FastAPI Depends() helpers pull services from request.app.state.container.

    Upgrade path: replace Container.create() body or individual fields
    to swap implementations (e.g. S3StorageService, real EmailService).
    """

    # ── Infrastructure ────────────────────────────────────────────────────
    db_engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

    # ── Security ──────────────────────────────────────────────────────────
    jwt_handler: JWTHandler
    password_hasher: IPasswordHasher

    # ── Storage ───────────────────────────────────────────────────────────
    storage_service: IStorageService

    # ── Events ────────────────────────────────────────────────────────────
    event_bus: InMemoryEventBus
    event_dispatcher: EventDispatcher
    # ── WebSocket ──────────────────────────────────────────────────────────
    connection_manager: ConnectionManager
    # ── Tasks ─────────────────────────────────────────────────────────────
    task_service: BackgroundTaskService

    # ── Audit ─────────────────────────────────────────────────────────────
    audit_service: AuditService

    # ── Error Logging ──────────────────────────────────────────────────────
    error_log_repository: ErrorLogRepository
    error_logger: ErrorLogger

    # ── External ──────────────────────────────────────────────────────────
    email_service: IEmailService

    @classmethod
    def create(cls, settings: Settings) -> "Container":
        """
        Factory method — wires all concrete implementations together.
        Called once at application startup.
        """
        # Database
        engine = create_engine(settings.async_database_url)
        session_factory = create_session_factory(engine)

        # Security
        jwt_handler = JWTHandler(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expiry_minutes=settings.jwt_expiry_minutes,
        )
        password_hasher = BcryptPasswordHasher()

        # Storage
        storage_service = LocalStorageService(upload_dir=settings.upload_dir)

        # Events
        event_bus = InMemoryEventBus()
        event_dispatcher = EventDispatcher(bus=event_bus)

        # WebSocket
        connection_manager = ConnectionManager()

        # Tasks
        task_service = BackgroundTaskService()

        # Audit
        audit_service = AuditService(session_factory=session_factory)

        # Error Logging
        error_log_repository = ErrorLogRepository(session_factory=session_factory)
        error_logger = ErrorLogger(
            session_factory=session_factory,
        )

        # External
        if settings.resend_api_key:
            from backend.app.infrastructure.external.resend_email_service import ResendEmailService
            email_service = ResendEmailService(
                api_key=settings.resend_api_key,
                from_email=settings.resend_from_email,
            )
        else:
            email_service = StubEmailService()

        return cls(
            db_engine=engine,
            session_factory=session_factory,
            jwt_handler=jwt_handler,
            password_hasher=password_hasher,
            storage_service=storage_service,
            event_bus=event_bus,
            event_dispatcher=event_dispatcher,
            connection_manager=connection_manager,
            task_service=task_service,
            audit_service=audit_service,
            error_log_repository=error_log_repository,
            error_logger=error_logger,
            email_service=email_service,
        )

    def get_session(self) -> async_sessionmaker[AsyncSession]:
        """Convenience accessor for FastAPI dependencies."""
        return self.session_factory

    def create_notification_service(self, session: AsyncSession) -> NotificationService:
        """Create a new notification service instance for the current DB session."""
        return NotificationService(session=session, connection_manager=self.connection_manager)
