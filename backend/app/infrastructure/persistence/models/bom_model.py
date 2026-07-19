import uuid
from datetime import datetime
from typing import List

from sqlalchemy import (
    String,
    Boolean,
    ForeignKey,
    DateTime,
    CheckConstraint,
    UniqueConstraint,
    Numeric,
    Index,
    func,
    select
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property

from backend.app.infrastructure.persistence.models.bom_operation_model import BOMOperationModel

from backend.app.infrastructure.persistence.database import Base


class BOMModel(Base):
    __tablename__ = "boms"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    
    # Nullable FKs for target product
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("item_templates.id"), nullable=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("item_variants.id"), nullable=True)
    
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship to Lines
    lines: Mapped[List["BOMLineModel"]] = relationship(
        "BOMLineModel",
        back_populates="bom",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    operations: Mapped[List["BOMOperationModel"]] = relationship(
        "BOMOperationModel",
        back_populates="bom",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    operations_count: Mapped[int] = column_property(
        select(func.count(BOMOperationModel.id)).where(BOMOperationModel.bom_id == id).correlate_except(BOMOperationModel).scalar_subquery()
    )

    __table_args__ = (
        CheckConstraint(
            "(template_id IS NOT NULL AND variant_id IS NULL) OR (template_id IS NULL AND variant_id IS NOT NULL)",
            name="chk_bom_product_target"
        ),
        UniqueConstraint("tenant_id", "template_id", "version", name="uq_bom_tenant_template_version"),
        UniqueConstraint("tenant_id", "variant_id", "version", name="uq_bom_tenant_variant_version"),
        Index("ix_bom_tenant_product", "tenant_id", "template_id", "variant_id"),
    )


class BOMLineModel(Base):
    __tablename__ = "bom_lines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    bom_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("boms.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Nullable FKs for component linkage
    material_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("materials.id"), nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("item_templates.id"), nullable=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("item_variants.id"), nullable=True)
    
    quantity: Mapped[float] = mapped_column(Numeric(15, 6), nullable=False)
    scrap_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    bom: Mapped["BOMModel"] = relationship("BOMModel", back_populates="lines")

    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN material_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN template_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN variant_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="chk_bom_line_component"
        ),
        CheckConstraint("quantity > 0", name="chk_bom_line_qty_positive"),
        Index("ix_bom_line_tenant_bom", "tenant_id", "bom_id"),
    )
