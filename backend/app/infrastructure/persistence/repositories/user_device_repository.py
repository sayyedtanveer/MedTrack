"""
User Device Repository

Data access layer for UserDeviceModel.
"""

from typing import Optional
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.user_device_model import UserDeviceModel


class UserDeviceRepository:
    """
    Repository for managing user devices (trusted for 2FA bypass).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, device_id: uuid.UUID) -> Optional[UserDeviceModel]:
        """Fetch device by ID"""
        query = select(UserDeviceModel).where(UserDeviceModel.id == device_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_fingerprint(self, user_id: uuid.UUID, fingerprint: str) -> Optional[UserDeviceModel]:
        """
        Fetch trusted device by user + fingerprint.

        Args:
            user_id: User who owns the device
            fingerprint: SHA256 hash of device characteristics

        Returns:
            UserDeviceModel if device found and still trusted, None otherwise
        """
        query = select(UserDeviceModel).where(
            and_(
                UserDeviceModel.user_id == user_id,
                UserDeviceModel.device_fingerprint == fingerprint,
            )
        )
        result = await self.session.execute(query)
        device = result.scalars().first()

        # Check if still within trust period
        if device:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            if now > device.trusted_until:
                # Device trust expired
                return None

        return device

    async def get_all_by_user(self, user_id: uuid.UUID) -> list[UserDeviceModel]:
        """Get all trusted devices for a user"""
        query = select(UserDeviceModel).where(UserDeviceModel.user_id == user_id).order_by(
            UserDeviceModel.last_used_at.desc()
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_by_user(self, user_id: uuid.UUID) -> list[UserDeviceModel]:
        """Get only currently trusted devices for a user"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        query = select(UserDeviceModel).where(
            and_(
                UserDeviceModel.user_id == user_id,
                UserDeviceModel.trusted_until > now,
            )
        ).order_by(UserDeviceModel.last_used_at.desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    def create_user_device(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        device_fingerprint: str,
        device_name: str,
        ip_address: str,
        trusted_until,
    ) -> UserDeviceModel:
        """Create a new trusted device record"""
        from datetime import datetime, timezone

        device = UserDeviceModel(
            id=uuid.uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
            ip_address=ip_address,
            trusted_until=trusted_until,
            created_at=datetime.now(timezone.utc),
            last_used_at=datetime.now(timezone.utc),
        )
        return device

    async def delete(self, device_id: uuid.UUID) -> bool:
        """Delete a trusted device"""
        device = await self.get_by_id(device_id)
        if device:
            await self.session.delete(device)
            return True
        return False

    async def delete_all_by_user(self, user_id: uuid.UUID) -> int:
        """Delete all trusted devices for a user (used on password change)"""
        query = select(UserDeviceModel).where(UserDeviceModel.user_id == user_id)
        result = await self.session.execute(query)
        devices = result.scalars().all()

        for device in devices:
            await self.session.delete(device)

        return len(devices)

    async def cleanup_expired(self, tenant_id: uuid.UUID) -> int:
        """
        Delete expired device records.

        Should be run periodically (e.g., daily background task).
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        query = select(UserDeviceModel).where(
            and_(
                UserDeviceModel.tenant_id == tenant_id,
                UserDeviceModel.trusted_until < now,
            )
        )

        result = await self.session.execute(query)
        expired_devices = result.scalars().all()

        for device in expired_devices:
            await self.session.delete(device)

        return len(expired_devices)
