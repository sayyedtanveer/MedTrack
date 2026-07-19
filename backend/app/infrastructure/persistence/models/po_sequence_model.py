from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class PONumberSequenceModel(Base):
    __tablename__ = "po_number_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
