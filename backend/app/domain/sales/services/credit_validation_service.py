"""Credit validation domain service."""

from decimal import Decimal
from uuid import UUID


class CreditValidationService:
    """
    Credit validation service for sales orders.
    
    Business rule:
    - Block order confirmation if: grand_total > (credit_limit - credit_used)
    - Only applied if client has credit limit set
    """

    def __init__(self, client_repository):
        """Initialize credit validation service."""
        self.client_repo = client_repository

    async def validate_credit(
        self,
        tenant_id: UUID,
        client_id: UUID,
        order_grand_total: Decimal,
    ) -> tuple[bool, str]:
        """
        Validate if order can be confirmed under client's credit limit.
        
        Args:
            tenant_id: Tenant ID
            client_id: Client ID
            order_grand_total: Grand total amount of order
            
        Returns:
            Tuple of (is_valid: bool, reason: str)
            - (True, "") if credit check passes
            - (False, reason) if credit check fails
            
        Raises:
            ValueError: If client not found
        """
        client = await self.client_repo.get_by_id(
            id=client_id,
            tenant_id=tenant_id,
        )
        
        if not client:
            raise ValueError(f"Client {client_id} not found")
        
        if not client.credit_limit:
            # No credit limit = unlimited credit
            return True, ""
        
        available_credit = client.credit_limit - client.credit_used
        
        if order_grand_total > available_credit:
            return False, (
                f"Insufficient credit. Order total: {order_grand_total}, "
                f"Available credit: {available_credit} "
                f"(Limit: {client.credit_limit}, Used: {client.credit_used})"
            )
        
        return True, ""

    async def allocate_credit(
        self,
        tenant_id: UUID,
        client_id: UUID,
        amount: Decimal,
    ) -> None:
        """
        Allocate credit when order is confirmed.
        
        Args:
            tenant_id: Tenant ID
            client_id: Client ID
            amount: Amount to allocate
            
        Raises:
            ValueError: If credit validation fails
        """
        client = await self.client_repo.get_by_id(
            id=client_id,
            tenant_id=tenant_id,
        )
        
        if not client:
            raise ValueError(f"Client {client_id} not found")
        
        client.increase_credit_used(amount)
        await self.client_repo.save(client)

    async def release_credit(
        self,
        tenant_id: UUID,
        client_id: UUID,
        amount: Decimal,
    ) -> None:
        """
        Release credit when order is cancelled.
        
        Args:
            tenant_id: Tenant ID
            client_id: Client ID
            amount: Amount to release
        """
        client = await self.client_repo.get_by_id(
            id=client_id,
            tenant_id=tenant_id,
        )
        
        if not client:
            raise ValueError(f"Client {client_id} not found")
        
        client.decrease_credit_used(amount)
        await self.client_repo.save(client)
