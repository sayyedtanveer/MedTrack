from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from backend.app.application.shared.query import Query

Q = TypeVar("Q", bound=Query)
R = TypeVar("R")


class IQueryHandler(Generic[Q, R]):
    """Protocol for CQRS query handlers."""

    @abstractmethod
    async def handle(self, query: Q) -> R:
        ...
