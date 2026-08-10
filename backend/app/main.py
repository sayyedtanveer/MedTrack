from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.logging import configure_logging

# Configure structured logging first, before any other imports that log.
# Requirements: 41.1, 41.5
configure_logging()

from backend.app.config import get_settings
from backend.app.infrastructure.container import Container
from backend.app.infrastructure.logging.logger import get_logger
from backend.app.infrastructure.websocket.event_handlers import (
    OrderStatusChangeHandler,
    InventoryLowStockAlert,
    WorkOrderReleased,
    WorkOrderStarted,
    WorkOrderCompleted,
    InvoiceOverdue,
    QualityInspectionFailed,
)
from backend.app.interfaces.api.v1.middleware.logging_middleware import RequestLoggingMiddleware
from backend.app.interfaces.api.v1.middleware.tenant_middleware import TenantMiddleware
from backend.app.interfaces.api.v1.middleware.audit_middleware import AuditMiddleware
from backend.app.interfaces.api.v1.middleware.rbac_audit import RBACPermissionAuditMiddleware
from backend.app.interfaces.api.v1.middleware.error_logging_middleware import ErrorLoggingMiddleware
from backend.app.middleware.security_headers import SecurityHeadersMiddleware
from backend.app.middleware.rate_limiting import limiter, rate_limit_exceeded_handler
from backend.app.middleware.correlation_id import CorrelationIdMiddleware
from backend.app.interfaces.api.v1.router import api_v1_router
from backend.app.interfaces.api.v1.routes.websocket import router as websocket_router
from backend.app.core.module_registry import module_registry

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan – startup and shutdown."""
    logger.info("Starting MedTrack ERP", extra={"version": settings.app_version})

    # Enforce production CORS policy before starting
    settings.validate_cors_for_production()

    # Build DI container once
    container = Container.create(settings)
    app.state.container = container

    # Create upload directory
    import os
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Register WebSocket event handlers with event dispatcher
    event_dispatcher = container.event_dispatcher
    connection_manager = container.connection_manager

    event_dispatcher.subscribe(
        "order.status_changed", OrderStatusChangeHandler(connection_manager)
    )
    event_dispatcher.subscribe(
        "inventory.low_stock_alert", InventoryLowStockAlert(connection_manager)
    )
    event_dispatcher.subscribe(
        "work_order.released", WorkOrderReleased(connection_manager)
    )
    event_dispatcher.subscribe(
        "work_order.started", WorkOrderStarted(connection_manager)
    )
    event_dispatcher.subscribe(
        "work_order.completed", WorkOrderCompleted(connection_manager)
    )
    event_dispatcher.subscribe(
        "invoice.overdue", InvoiceOverdue(connection_manager)
    )
    event_dispatcher.subscribe(
        "quality.inspection_failed", QualityInspectionFailed(connection_manager)
    )

    logger.info("WebSocket event handlers registered")
    
    # Freeze the system map to prevent mutations and ensure dependencies are valid
    module_registry.lock()

    logger.info("Application startup complete")
    yield

    # Shutdown
    await container.db_engine.dispose()
    logger.info("Application shutdown complete")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-tenant Manufacturing ERP — Phase 0 Foundation",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware (order matters: outermost first) ──
    app.add_middleware(ErrorLoggingMiddleware)  # ✅ NEW: Centralized error capture + logging
    app.add_middleware(CorrelationIdMiddleware)  # ✅ NEW: X-Request-ID tracing (Req 41.2)
    from backend.app.interfaces.api.v1.middleware.timing_middleware import TimingMiddleware
    app.add_middleware(TimingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)  # ✅ Security headers for production hardening

    # Rate limiting (SlowAPI)
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RBACPermissionAuditMiddleware)  # ✅ NEW: Log 403 denials
    app.add_middleware(AuditMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # ── Static file serving for uploads ──────────────
    import os
    os.makedirs(settings.upload_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

    # ── Routers ───────────────────────────────────────
    # WebSocket routes. Keep the legacy /ws path and expose /api/v1/ws for
    # the Vite dev proxy/front-end API base.
    app.include_router(websocket_router)
    app.include_router(websocket_router, prefix="/api/v1")
    
    # REST API routes
    app.include_router(api_v1_router, prefix="/api/v1")

    # ── Exception handlers ─────────────────────────────
    from backend.app.domain.shared.exceptions.domain_exception import DomainException
    
    _AUTH_CODES = {"INVALID_TOKEN", "TOKEN_EXPIRED", "AUTH_REQUIRED", "UNAUTHORIZED"}

    @app.exception_handler(DomainException)
    async def domain_exception_handler(request, exc: DomainException):
        """Convert domain exceptions to appropriate HTTP responses.

        Auth-specific codes → 401.
        All other domain rule violations → 422 (business logic failure,
        not an auth problem — prevents spurious frontend logouts).
        """
        if exc.code in _AUTH_CODES:
            return JSONResponse(status_code=401, content={"detail": exc.message})
        return JSONResponse(status_code=422, content={"detail": exc.message, "code": exc.code})

    # ── Health check ──────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "environment": settings.environment,
            "version": settings.app_version,
        }

    return app


app = create_application()
