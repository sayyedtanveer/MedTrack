"""
Repository interfaces for procurement domain (DDD Layer 1).

Abstract interfaces defining data access contracts.
Implementations are in infrastructure/persistence/repositories/.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from backend.app.domain.procurement.pricing.entities import (
    MaterialCostHistory,
    PriceOverrideRecord,
    StandardCostRevision,
    SupplierPriceAgreement,
)


class ISupplierPriceAgreementRepository(ABC):
    """Abstract repository for supplier price agreements."""

    @abstractmethod
    async def get_by_id(
        self, tenant_id: UUID, agreement_id: UUID
    ) -> Optional[SupplierPriceAgreement]:
        """
        Get agreement by ID (soft delete filter applied).

        Args:
            tenant_id: Tenant ID (for isolation)
            agreement_id: Agreement ID

        Returns:
            SupplierPriceAgreement if found and not deleted, None otherwise
        """
        pass

    @abstractmethod
    async def get_active_by_supplier_material(
        self, tenant_id: UUID, supplier_id: UUID, material_id: UUID
    ) -> Optional[SupplierPriceAgreement]:
        """
        Get active agreement for supplier-material pair.

        Used to check for existing active agreements before activation.

        Args:
            tenant_id: Tenant ID
            supplier_id: Supplier ID
            material_id: Material ID

        Returns:
            Active agreement if exists, None otherwise
        """
        pass

    async def find_overlapping(
        self,
        tenant_id: UUID,
        supplier_id: UUID,
        material_id: UUID,
        effective_from: datetime,
        effective_to: Optional[datetime],
        *,
        exclude_id: Optional[UUID] = None,
    ) -> Optional[SupplierPriceAgreement]:
        """Find a non-cancelled agreement whose effective interval overlaps."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_supplier(
        self, tenant_id: UUID, supplier_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[SupplierPriceAgreement]:
        """
        List agreements for a supplier (active and inactive).

        Args:
            tenant_id: Tenant ID
            supplier_id: Supplier ID
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            List of agreements (soft delete filter applied)
        """
        pass

    @abstractmethod
    async def list_by_material(
        self, tenant_id: UUID, material_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[SupplierPriceAgreement]:
        """
        List agreements for a material (all suppliers).

        Args:
            tenant_id: Tenant ID
            material_id: Material ID
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            List of agreements (soft delete filter applied)
        """
        pass

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[SupplierPriceAgreement]:
        """
        List all agreements for tenant.

        Args:
            tenant_id: Tenant ID
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            List of agreements (soft delete filter applied)
        """
        pass

    async def list_filtered(
        self,
        tenant_id: UUID,
        *,
        supplier_id: Optional[UUID] = None,
        material_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[SupplierPriceAgreement]:
        """List agreements using the API's tenant-scoped filters."""
        raise NotImplementedError

    async def count_filtered(
        self,
        tenant_id: UUID,
        *,
        supplier_id: Optional[UUID] = None,
        material_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count agreements matching the API's tenant-scoped filters."""
        raise NotImplementedError

    @abstractmethod
    async def save(self, agreement: SupplierPriceAgreement) -> SupplierPriceAgreement:
        """
        Insert or update agreement.

        Args:
            agreement: Domain entity to persist

        Returns:
            Persisted entity with updated timestamps
        """
        pass

    @abstractmethod
    async def delete(self, tenant_id: UUID, agreement_id: UUID) -> None:
        """
        Soft-delete agreement (set is_deleted=true, deleted_at=now).

        Args:
            tenant_id: Tenant ID
            agreement_id: Agreement ID to delete
        """
        pass


class IMaterialCostHistoryRepository(ABC):
    """Abstract repository for cost history (immutable audit log)."""

    @abstractmethod
    async def add_entry(self, history: MaterialCostHistory) -> MaterialCostHistory:
        """
        Insert new cost history record (append-only).

        Never updates existing records (immutable).

        Args:
            history: Cost history entry to record

        Returns:
            Persisted entry
        """
        pass

    @abstractmethod
    async def list_by_material(
        self, tenant_id: UUID, material_id: UUID, limit: int = 100
    ) -> List[MaterialCostHistory]:
        """
        List cost history for a material (chronological order).

        Args:
            tenant_id: Tenant ID
            material_id: Material ID
            limit: Maximum records to return

        Returns:
            List of history entries (newest first)
        """
        pass

    @abstractmethod
    async def list_by_change_type(
        self,
        tenant_id: UUID,
        change_type: str,
        limit: int = 100,
    ) -> List[MaterialCostHistory]:
        """
        List history entries by change type (e.g., GRN_RECEIPT, COST_REVISION_APPROVED).

        Args:
            tenant_id: Tenant ID
            change_type: Type of change to filter by
            limit: Maximum records to return

        Returns:
            List of history entries
        """
        pass

    @abstractmethod
    async def get_by_id(
        self, tenant_id: UUID, history_id: UUID
    ) -> Optional[MaterialCostHistory]:
        """
        Get cost history record by ID.

        Args:
            tenant_id: Tenant ID
            history_id: History record ID

        Returns:
            History entry if found, None otherwise
        """
        pass


class IStandardCostRevisionRepository(ABC):
    """Abstract repository for cost revision approvals."""

    @abstractmethod
    async def get_by_id(
        self, tenant_id: UUID, revision_id: UUID
    ) -> Optional[StandardCostRevision]:
        """
        Get revision by ID (soft delete filter applied).

        Args:
            tenant_id: Tenant ID
            revision_id: Revision ID

        Returns:
            StandardCostRevision if found and not deleted, None otherwise
        """
        pass

    async def get_by_id_for_update(
        self, tenant_id: UUID, revision_id: UUID
    ) -> Optional[StandardCostRevision]:
        """Return a revision while holding a row lock for a state transition."""
        raise NotImplementedError

    async def get_material_current_cost(
        self, tenant_id: UUID, material_id: UUID, *, lock: bool = False
    ) -> Optional[Decimal]:
        """Return the active material's current cost, scoped to its tenant."""
        raise NotImplementedError

    async def update_material_current_cost(
        self, tenant_id: UUID, material_id: UUID, cost: Decimal, updated_by: UUID
    ) -> bool:
        """Persist the approved cost on an active material."""
        raise NotImplementedError

    async def get_approved_cost(
        self, tenant_id: UUID, material_id: UUID
    ) -> Optional[StandardCostRevision]:
        """Return the latest approved cost revision for a material."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_material(
        self, tenant_id: UUID, material_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[StandardCostRevision]:
        """
        List revisions for a material (all statuses).

        Args:
            tenant_id: Tenant ID
            material_id: Material ID
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            List of revisions (soft delete filter applied)
        """
        pass

    @abstractmethod
    async def list_pending(
        self, tenant_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[StandardCostRevision]:
        """
        List pending revisions awaiting approval.

        Args:
            tenant_id: Tenant ID
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            List of PENDING revisions
        """
        pass

    async def count_pending(self, tenant_id: UUID) -> int:
        """Count pending revisions for a tenant."""
        raise NotImplementedError

    async def count_by_material(self, tenant_id: UUID, material_id: UUID) -> int:
        """Count revisions for a tenant-scoped material."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_requester(
        self, tenant_id: UUID, requester_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[StandardCostRevision]:
        """
        List revisions requested by a specific user.

        Args:
            tenant_id: Tenant ID
            requester_id: User ID who made the request
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            List of revisions
        """
        pass

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: UUID, page: int = 1, page_size: int = 20
    ) -> List[StandardCostRevision]:
        """
        List all revisions for tenant.

        Args:
            tenant_id: Tenant ID
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            List of revisions (soft delete filter applied)
        """
        pass

    @abstractmethod
    async def save(self, revision: StandardCostRevision) -> StandardCostRevision:
        """
        Insert or update revision.

        Args:
            revision: Domain entity to persist

        Returns:
            Persisted entity with updated timestamps
        """
        pass

    @abstractmethod
    async def delete(self, tenant_id: UUID, revision_id: UUID) -> None:
        """
        Soft-delete revision (set is_deleted=true, deleted_at=now).

        Args:
            tenant_id: Tenant ID
            revision_id: Revision ID to delete
        """
        pass


class IPriceOverrideRecordRepository(ABC):
    """Abstract repository for price override records (analytics)."""

    @abstractmethod
    async def get_by_id(
        self, tenant_id: UUID, record_id: UUID
    ) -> Optional[PriceOverrideRecord]:
        """
        Get override record by ID (soft delete filter applied).

        Args:
            tenant_id: Tenant ID
            record_id: Record ID

        Returns:
            PriceOverrideRecord if found and not deleted, None otherwise
        """
        pass

    @abstractmethod
    async def list_by_material(
        self, tenant_id: UUID, material_id: UUID, limit: int = 50
    ) -> List[PriceOverrideRecord]:
        """
        List override records for a material (newest first).

        Args:
            tenant_id: Tenant ID
            material_id: Material ID
            limit: Maximum records to return

        Returns:
            List of override records
        """
        pass

    @abstractmethod
    async def list_by_grn(
        self, tenant_id: UUID, grn_id: UUID
    ) -> List[PriceOverrideRecord]:
        """
        List overrides associated with a GRN.

        Args:
            tenant_id: Tenant ID
            grn_id: GRN ID

        Returns:
            List of override records
        """
        pass

    @abstractmethod
    async def list_by_override_reason(
        self,
        tenant_id: UUID,
        reason: str,
        limit: int = 50,
    ) -> List[PriceOverrideRecord]:
        """
        List overrides by reason (e.g., QUALITY_ISSUE, RUSH_ORDER).

        Args:
            tenant_id: Tenant ID
            reason: Override reason to filter by
            limit: Maximum records to return

        Returns:
            List of override records
        """
        pass

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: UUID, limit: int = 100
    ) -> List[PriceOverrideRecord]:
        """
        List all override records for tenant (newest first).

        Args:
            tenant_id: Tenant ID
            limit: Maximum records to return

        Returns:
            List of override records (soft delete filter applied)
        """
        pass

    @abstractmethod
    async def save(self, record: PriceOverrideRecord) -> PriceOverrideRecord:
        """
        Insert new override record.

        Args:
            record: Record to persist

        Returns:
            Persisted record
        """
        pass

    @abstractmethod
    async def delete(self, tenant_id: UUID, record_id: UUID) -> None:
        """
        Soft-delete override record (set is_deleted=true, deleted_at=now).

        Args:
            tenant_id: Tenant ID
            record_id: Record ID to delete
        """
        pass
