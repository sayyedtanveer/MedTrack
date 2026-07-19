"""WebSocket connection manager for real-time notifications."""

from __future__ import annotations

import uuid
import json
from typing import Set, Dict, Optional
from dataclasses import dataclass

from fastapi import WebSocket
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass(eq=False)
class ConnectionContext:
    """Context for an active WebSocket connection."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    websocket: WebSocket
    connection_id: str  # Unique ID for this connection


class ConnectionManager:
    """
    Manages WebSocket connections per user and tenant.
    
    Allows broadcasting notifications to:
    - Specific user (across all tabs/windows)
    - Specific tenant (all connected users in tenant)
    - All connected clients
    
    Thread-safe for asyncio (single-threaded event loop).
    """

    def __init__(self) -> None:
        # tenant_id -> user_id -> [ConnectionContext]
        self._connections: Dict[uuid.UUID, Dict[uuid.UUID, Set[ConnectionContext]]] = {}
        # connection_id -> ConnectionContext (for quick lookup)
        self._connection_index: Dict[str, ConnectionContext] = {}

    async def connect(self, connection: ConnectionContext) -> None:
        """Register a new WebSocket connection."""
        tenant_id = connection.tenant_id
        user_id = connection.user_id
        connection_id = connection.connection_id

        # Initialize tenant dict if needed
        if tenant_id not in self._connections:
            self._connections[tenant_id] = {}

        # Initialize user set if needed
        if user_id not in self._connections[tenant_id]:
            self._connections[tenant_id][user_id] = set()

        # Add connection
        self._connections[tenant_id][user_id].add(connection)
        self._connection_index[connection_id] = connection

        logger.debug(
            "WebSocket connection established",
            extra={
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "connection_id": connection_id,
            },
        )

    async def disconnect(self, connection_id: str) -> None:
        """Unregister a WebSocket connection."""
        connection = self._connection_index.get(connection_id)
        if not connection:
            return

        tenant_id = connection.tenant_id
        user_id = connection.user_id

        # Remove from index
        del self._connection_index[connection_id]

        # Remove from tenant/user dict
        if tenant_id in self._connections:
            if user_id in self._connections[tenant_id]:
                self._connections[tenant_id][user_id].discard(connection)

                # Cleanup empty sets
                if not self._connections[tenant_id][user_id]:
                    del self._connections[tenant_id][user_id]

            # Cleanup empty tenant dicts
            if not self._connections[tenant_id]:
                del self._connections[tenant_id]

        logger.debug(
            "WebSocket connection closed",
            extra={
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "connection_id": connection_id,
            },
        )

    async def send_to_user(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        message_type: str,
        payload: dict,
    ) -> None:
        """Send notification to specific user across all connections."""
        if tenant_id not in self._connections:
            return

        if user_id not in self._connections[tenant_id]:
            return

        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": None,  # Will be set on client
        }

        connections = self._connections[tenant_id][user_id].copy()
        for connection in connections:
            await self._send_message(connection, message)

    async def broadcast_to_tenant(
        self,
        tenant_id: uuid.UUID,
        message_type: str,
        payload: dict,
    ) -> None:
        """Broadcast notification to all users in a tenant."""
        if tenant_id not in self._connections:
            return

        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": None,
        }

        # Copy to avoid modification during iteration
        users_copy = self._connections[tenant_id].copy()
        for user_id, connections in users_copy.items():
            for connection in connections.copy():
                await self._send_message(connection, message)

    async def broadcast_to_role(
        self,
        tenant_id: uuid.UUID,
        role: str,
        message_type: str,
        payload: dict,
    ) -> None:
        """
        Broadcast notification to all users with a specific role in a tenant.
        Note: Requires role information to be passed separately since we only
        store connection data here. This should be called from a handler that
        has access to user role data.
        """
        # This would need to be called from context that has role info
        # For now, we'll handle role-based filtering in the event handlers
        pass

    async def broadcast_all(
        self,
        message_type: str,
        payload: dict,
    ) -> None:
        """Broadcast notification to all connected clients."""
        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": None,
        }

        for tenant_id, users in self._connections.items():
            for user_id, connections in users.items():
                for connection in connections.copy():
                    await self._send_message(connection, message)

    async def _send_message(
        self, connection: ConnectionContext, message: dict
    ) -> None:
        """Send a message through a WebSocket connection."""
        try:
            await connection.websocket.send_json(message)
        except Exception as e:
            logger.warning(
                "Failed to send WebSocket message",
                extra={
                    "connection_id": connection.connection_id,
                    "user_id": str(connection.user_id),
                    "error": str(e),
                },
            )
            # Attempt to disconnect
            await self.disconnect(connection.connection_id)

    def get_connected_users(self, tenant_id: uuid.UUID) -> Set[uuid.UUID]:
        """Get all currently connected users for a tenant."""
        if tenant_id not in self._connections:
            return set()
        return set(self._connections[tenant_id].keys())

    def get_connection_count(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Get number of active connections for a user."""
        if tenant_id not in self._connections:
            return 0
        if user_id not in self._connections[tenant_id]:
            return 0
        return len(self._connections[tenant_id][user_id])

    def get_total_connections(self) -> int:
        """Get total number of active WebSocket connections."""
        return len(self._connection_index)
