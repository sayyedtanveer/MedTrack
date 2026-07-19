"""Client and Price List command handlers."""

from uuid import uuid4

from backend.app.domain.sales.entities import Client, PriceList, PriceListLine
from backend.app.domain.sales.repositories import ClientRepository, PriceListRepository
from backend.app.application.sales.commands import (
    CreateClientCommand,
    UpdateClientCommand,
    DeactivateClientCommand,
    CreatePriceListCommand,
    AddPriceListLineCommand,
    UpdatePriceListLineCommand,
    RemovePriceListLineCommand,
)


class CreateClientCommandHandler:
    """Handler for creating new clients."""

    def __init__(self, client_repo: ClientRepository, uow):
        """Initialize handler."""
        self.client_repo = client_repo
        self.uow = uow

    async def handle(self, command: CreateClientCommand) -> str:
        """
        Create a new client.
        
        Args:
            command: Create client command
            
        Returns:
            Client ID
            
        Raises:
            ValueError: If code already exists
        """
        # Check for duplicate code
        existing = await self.client_repo.get_by_code(
            tenant_id=command.tenant_id,
            code=command.code,
        )
        if existing:
            raise ValueError(f"Client code '{command.code}' already exists")
        
        # Create client aggregate
        client_id = uuid4()
        client = Client(
            id=client_id,
            tenant_id=command.tenant_id,
            code=command.code,
            name=command.name,
            email=command.email,
            phone=command.phone,
            address=command.address,
            gst_number=command.gst_number,
            credit_limit=command.credit_limit,
            payment_terms_days=command.payment_terms_days,
        )
        
        # Persist
        await self.client_repo.save(client)
        await self.uow.work()
        
        return str(client_id)


class UpdateClientCommandHandler:
    """Handler for updating client information."""

    def __init__(self, client_repo: ClientRepository, uow):
        """Initialize handler."""
        self.client_repo = client_repo
        self.uow = uow

    async def handle(self, command: UpdateClientCommand) -> None:
        """Update client details."""
        client = await self.client_repo.get_by_id(
            id=command.client_id,
            tenant_id=command.tenant_id,
        )
        if not client:
            raise ValueError(f"Client {command.client_id} not found")
        
        # Update fields
        if command.name is not None:
            client.name = command.name
        if command.email is not None:
            client.email = command.email
        if command.phone is not None:
            client.phone = command.phone
        if command.address is not None:
            client.address = command.address
        if command.gst_number is not None:
            client.gst_number = command.gst_number
        if command.credit_limit is not None:
            client.credit_limit = command.credit_limit
        if command.payment_terms_days is not None:
            client.payment_terms_days = command.payment_terms_days
        
        await self.client_repo.save(client)
        await self.uow.work()


class DeactivateClientCommandHandler:
    """Handler for deactivating clients."""

    def __init__(self, client_repo: ClientRepository, uow):
        """Initialize handler."""
        self.client_repo = client_repo
        self.uow = uow

    async def handle(self, command: DeactivateClientCommand) -> None:
        """Deactivate a client (soft delete)."""
        client = await self.client_repo.get_by_id(
            id=command.client_id,
            tenant_id=command.tenant_id,
        )
        if not client:
            raise ValueError(f"Client {command.client_id} not found")
        
        client.is_active = False
        
        await self.client_repo.save(client)
        await self.uow.work()


class CreatePriceListCommandHandler:
    """Handler for creating price lists."""

    def __init__(self, price_list_repo: PriceListRepository, uow):
        """Initialize handler."""
        self.price_list_repo = price_list_repo
        self.uow = uow

    async def handle(self, command: CreatePriceListCommand) -> str:
        """
        Create a new price list.
        
        Args:
            command: Create price list command
            
        Returns:
            Price list ID
        """
        price_list_id = uuid4()
        price_list = PriceList(
            id=price_list_id,
            tenant_id=command.tenant_id,
            name=command.name,
            is_default=command.is_default,
        )
        
        if command.valid_from:
            price_list.valid_from = command.valid_from
        if command.valid_to:
            price_list.valid_to = command.valid_to
        
        await self.price_list_repo.save(price_list)
        await self.uow.work()
        
        return str(price_list_id)


class AddPriceListLineCommandHandler:
    """Handler for adding pricing lines to price lists."""

    def __init__(self, price_list_repo: PriceListRepository, uow):
        """Initialize handler."""
        self.price_list_repo = price_list_repo
        self.uow = uow

    async def handle(self, command: AddPriceListLineCommand) -> None:
        """Add a pricing line to a price list."""
        price_list = await self.price_list_repo.get_by_id(
            id=command.price_list_id,
            tenant_id=command.tenant_id,
        )
        if not price_list:
            raise ValueError(f"Price list {command.price_list_id} not found")
        
        line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=command.product_id,
            product_type=command.product_type,
            unit_price=command.unit_price,
        )
        
        price_list.add_line(line)
        
        await self.price_list_repo.save(price_list)
        await self.uow.work()


class UpdatePriceListLineCommandHandler:
    """Handler for updating pricing lines."""

    def __init__(self, price_list_repo: PriceListRepository, uow):
        """Initialize handler."""
        self.price_list_repo = price_list_repo
        self.uow = uow

    async def handle(self, command: UpdatePriceListLineCommand) -> None:
        """Update a pricing line."""
        price_list = await self.price_list_repo.get_by_id(
            id=command.price_list_id,
            tenant_id=command.tenant_id,
        )
        if not price_list:
            raise ValueError(f"Price list {command.price_list_id} not found")
        
        price_list.update_line_price(
            product_id=command.product_id,
            product_type=command.product_type,
            new_price=command.new_price,
        )
        
        await self.price_list_repo.save(price_list)
        await self.uow.work()


class RemovePriceListLineCommandHandler:
    """Handler for removing pricing lines."""

    def __init__(self, price_list_repo: PriceListRepository, uow):
        """Initialize handler."""
        self.price_list_repo = price_list_repo
        self.uow = uow

    async def handle(self, command: RemovePriceListLineCommand) -> None:
        """Remove a pricing line from a price list."""
        price_list = await self.price_list_repo.get_by_id(
            id=command.price_list_id,
            tenant_id=command.tenant_id,
        )
        if not price_list:
            raise ValueError(f"Price list {command.price_list_id} not found")
        
        price_list.remove_line(
            product_id=command.product_id,
            product_type=command.product_type,
        )
        
        await self.price_list_repo.save(price_list)
        await self.uow.work()

