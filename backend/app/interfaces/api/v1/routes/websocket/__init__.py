"""WebSocket endpoint for real-time notifications."""

from __future__ import annotations

import uuid
import secrets

from fastapi import WebSocketException, WebSocket, APIRouter, Depends, Request
from fastapi.exceptions import WebSocketException as FastAPIWebSocketException

from backend.app.config import get_settings
from backend.app.infrastructure.security.jwt_handler import JWTHandler
from backend.app.infrastructure.security.jwt_claim_validator import (
    parse_user_claim,
    parse_tenant_claim,
)
from backend.app.infrastructure.websocket import ConnectionManager, ConnectionContext
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def verify_ws_token(token: str, jwt_handler: JWTHandler) -> dict:
    """Verify JWT token from WebSocket connection."""
    try:
        payload = jwt_handler.verify_token(token)
        return payload
    except Exception as e:
        logger.warning(f"WebSocket token verification failed: {str(e)}")
        raise WebSocketException(code=1008, reason="Unauthorized")


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str,
):
    """
    WebSocket endpoint for real-time notifications.

    Connection flow:
    1. Client connects: ws://...api/v1/ws/notifications?token={jwt}
    2. Server verifies JWT token
    3. On success: connection accepted, ready to receive broadcasts
    4. On failure: connection rejected with code 1008

    Message format:
    {
        "type": "notification",
        "payload": {
            "id": "event-id",
            "type": "ORDER_STATUS_CHANGED",
            "title": "Order Updated",
            "message": "Order #123 status changed to shipped",
            "data": {...event-specific data},
            "timestamp": "2026-04-14T10:30:00Z"
        }
    }
    """
    connection_id = secrets.token_hex(16)
    connection_manager: ConnectionManager | None = None

    try:
        # Verify JWT token from query parameter
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Missing token")
            return

        # Get container and JWT handler from app state
        jwt_handler = websocket.app.state.container.jwt_handler
        connection_manager = websocket.app.state.container.connection_manager
        
        payload = await verify_ws_token(token, jwt_handler)

        user_id = parse_user_claim(payload)
        tenant_id = parse_tenant_claim(payload)

        # Accept connection
        await websocket.accept()

        # Create connection context
        connection = ConnectionContext(
            user_id=user_id,
            tenant_id=tenant_id,
            websocket=websocket,
            connection_id=connection_id,
        )

        # Register connection
        await connection_manager.connect(connection)

        logger.info(
            "WebSocket notification connection established",
            extra={
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "connection_id": connection_id,
                "total_connections": connection_manager.get_total_connections(),
            },
        )

        # Keep connection alive and handle incoming messages
        try:
            while True:
                # Wait for message from client
                # Usually clients send heartbeat/ping pong, but we're primarily
                # a server-to-client broadcast channel
                data = await websocket.receive_text()

                # Handle heartbeat/ping
                if data == "ping":
                    await websocket.send_text("pong")

        except Exception as e:
            logger.debug(
                "WebSocket connection error",
                extra={"connection_id": connection_id, "error": str(e)},
            )

    except FastAPIWebSocketException:
        raise
    except Exception as e:
        logger.error(
            "WebSocket connection failed",
            extra={"connection_id": connection_id, "error": str(e)},
        )
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass
    finally:
        # Cleanup on disconnect
        if connection_manager:
            try:
                await connection_manager.disconnect(connection_id)

                logger.info(
                    "WebSocket connection closed",
                    extra={
                        "connection_id": connection_id,
                        "total_connections": connection_manager.get_total_connections(),
                    },
                )
            except Exception as e:
                logger.error(
                    "Error disconnecting WebSocket",
                    extra={"connection_id": connection_id, "error": str(e)},
                )
