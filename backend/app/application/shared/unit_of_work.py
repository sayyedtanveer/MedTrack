# Re-export IUnitOfWork for application layer use
from backend.app.domain.shared.interfaces.unit_of_work_interface import IUnitOfWork

__all__ = ["IUnitOfWork"]
