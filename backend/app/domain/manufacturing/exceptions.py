"""Domain exceptions for the manufacturing module."""


class InsufficientStockError(Exception):
    error_code = "INSUFFICIENT_STOCK"


class MaterialNotIssuedError(Exception):
    error_code = "MATERIAL_NOT_ISSUED"


class BOMNotFoundError(Exception):
    error_code = "BOM_NOT_FOUND"


class WorkOrderImmutableError(Exception):
    error_code = "WO_IMMUTABLE"
