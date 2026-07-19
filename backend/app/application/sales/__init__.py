"""Sales application layer (CQRS orchestration).

Commands - Write operations:
- CreateSalesOrderCommand: Create new order
- AddLineToSalesOrderCommand: Add line item
- RemoveLineFromSalesOrderCommand: Remove line item
- ApplyDiscountToOrderCommand: Apply discount
- ConfirmSalesOrderCommand: Confirm and allocate resources
- CancelSalesOrderCommand: Cancel order
- ShipOrderCommand: Record shipment
- DeliverOrderCommand: Record delivery
- CreateClientCommand: Create client
- UpdateClientCommand: Update client info
- DeactivateClientCommand: Deactivate client
- CreatePriceListCommand: Create price list
- AddPriceListLineCommand: Add pricing in list
- UpdatePriceListLineCommand: Update price
- RemovePriceListLineCommand: Remove from price list

Queries - Read operations:
- GetClientByIdQuery: Fetch client
- GetSalesOrderByIdQuery: Fetch order
- ListClientOrdersQuery: Get client's orders
- GetProductPriceQuery: Get pricing
- CheckClientCreditQuery: Validate credit
- GetPriceListByIdQuery: Fetch price list
- ListPriceListsQuery: List all price lists
- And many more filtering/search queries

Handlers - Business logic orchestration:
- Command Handlers: Validate input, orchestrate domain services and save
- Query Handlers: Execute read queries and return results

Example usage:
    command = CreateSalesOrderCommand(...)
    handler = CreateSalesOrderCommandHandler(repo, uow)
    order_id = await handler.handle(command)
"""

from backend.app.application.sales.commands import (
    CreateSalesOrderCommand,
    AddLineToSalesOrderCommand,
    RemoveLineFromSalesOrderCommand,
    ApplyDiscountToOrderCommand,
    SubmitSalesOrderForApprovalCommand,
    ApproveSalesOrderCommand,
    RejectSalesOrderCommand,
    ConfirmSalesOrderCommand,
    CancelSalesOrderCommand,
    TransitionOrderToProductionCommand,
    TransitionOrderToReadyCommand,
    ShipOrderCommand,
    DeliverOrderCommand,
    RecordPaymentCommand,
    CreateClientCommand,
    UpdateClientCommand,
    DeactivateClientCommand,
    CreatePriceListCommand,
    AddPriceListLineCommand,
    UpdatePriceListLineCommand,
    RemovePriceListLineCommand,
)

from backend.app.application.sales.queries import (
    GetClientByIdQuery,
    GetClientByCodeQuery,
    ListClientsQuery,
    GetSalesOrderByIdQuery,
    GetSalesOrderByNumberQuery,
    ListClientOrdersQuery,
    ListOrdersByDateRangeQuery,
    ListPendingOrdersQuery,
    GetProductPriceQuery,
    CheckClientCreditQuery,
    GetPriceListByIdQuery,
    ListPriceListsQuery,
    GetOrderCountByStatusQuery,
    ListDraftOrdersQuery,
    ListOrdersByDeliveryDateQuery,
)

from backend.app.application.sales.command_handlers import (
    CreateSalesOrderCommandHandler,
    AddLineToSalesOrderCommandHandler,
    RemoveLineFromSalesOrderCommandHandler,
    ApplyDiscountToOrderCommandHandler,
    SubmitSalesOrderForApprovalCommandHandler,
    ApproveSalesOrderCommandHandler,
    RejectSalesOrderCommandHandler,
    ConfirmSalesOrderCommandHandler,
    CancelSalesOrderCommandHandler,
    ShipOrderCommandHandler,
    DeliverOrderCommandHandler,
)

from backend.app.application.sales.client_handlers import (
    CreateClientCommandHandler,
    UpdateClientCommandHandler,
    DeactivateClientCommandHandler,
    CreatePriceListCommandHandler,
    AddPriceListLineCommandHandler,
    UpdatePriceListLineCommandHandler,
    RemovePriceListLineCommandHandler,
)

from backend.app.application.sales.query_handlers import (
    GetClientByIdQueryHandler,
    GetClientByCodeQueryHandler,
    ListClientsQueryHandler,
    GetSalesOrderByIdQueryHandler,
    GetSalesOrderByNumberQueryHandler,
    ListClientOrdersQueryHandler,
    ListOrdersByDateRangeQueryHandler,
    ListDraftOrdersQueryHandler,
    ListOrdersByDeliveryDateQueryHandler,
    GetProductPriceQueryHandler,
    CheckClientCreditQueryHandler,
    GetPriceListByIdQueryHandler,
    ListPriceListsQueryHandler,
    GetOrderCountByStatusQueryHandler,
)

__all__ = [
    # Commands
    "CreateSalesOrderCommand",
    "AddLineToSalesOrderCommand",
    "RemoveLineFromSalesOrderCommand",
    "ApplyDiscountToOrderCommand",
    "SubmitSalesOrderForApprovalCommand",
    "ApproveSalesOrderCommand",
    "RejectSalesOrderCommand",
    "ConfirmSalesOrderCommand",
    "CancelSalesOrderCommand",
    "TransitionOrderToProductionCommand",
    "TransitionOrderToReadyCommand",
    "ShipOrderCommand",
    "DeliverOrderCommand",
    "RecordPaymentCommand",
    "CreateClientCommand",
    "UpdateClientCommand",
    "DeactivateClientCommand",
    "CreatePriceListCommand",
    "AddPriceListLineCommand",
    "UpdatePriceListLineCommand",
    "RemovePriceListLineCommand",
    # Queries
    "GetClientByIdQuery",
    "GetClientByCodeQuery",
    "ListClientsQuery",
    "GetSalesOrderByIdQuery",
    "GetSalesOrderByNumberQuery",
    "ListClientOrdersQuery",
    "ListOrdersByDateRangeQuery",
    "ListPendingOrdersQuery",
    "GetProductPriceQuery",
    "CheckClientCreditQuery",
    "GetPriceListByIdQuery",
    "ListPriceListsQuery",
    "GetOrderCountByStatusQuery",
    "ListDraftOrdersQuery",
    "ListOrdersByDeliveryDateQuery",
    # Command Handlers
    "CreateSalesOrderCommandHandler",
    "AddLineToSalesOrderCommandHandler",
    "RemoveLineFromSalesOrderCommandHandler",
    "ApplyDiscountToOrderCommandHandler",
    "SubmitSalesOrderForApprovalCommandHandler",
    "ApproveSalesOrderCommandHandler",
    "RejectSalesOrderCommandHandler",
    "ConfirmSalesOrderCommandHandler",
    "CancelSalesOrderCommandHandler",
    "ShipOrderCommandHandler",
    "DeliverOrderCommandHandler",
    "CreateClientCommandHandler",
    "UpdateClientCommandHandler",
    "DeactivateClientCommandHandler",
    "CreatePriceListCommandHandler",
    "AddPriceListLineCommandHandler",
    "UpdatePriceListLineCommandHandler",
    "RemovePriceListLineCommandHandler",
    # Query Handlers
    "GetClientByIdQueryHandler",
    "GetClientByCodeQueryHandler",
    "ListClientsQueryHandler",
    "GetSalesOrderByIdQueryHandler",
    "GetSalesOrderByNumberQueryHandler",
    "ListClientOrdersQueryHandler",
    "ListOrdersByDateRangeQueryHandler",
    "ListDraftOrdersQueryHandler",
    "ListOrdersByDeliveryDateQueryHandler",
    "GetProductPriceQueryHandler",
    "CheckClientCreditQueryHandler",
    "GetPriceListByIdQueryHandler",
    "ListPriceListsQueryHandler",
    "GetOrderCountByStatusQueryHandler",
]

