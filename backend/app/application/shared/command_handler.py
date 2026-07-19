from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

from backend.app.application.shared.command import Command

C = TypeVar("C", bound=Command)
R = TypeVar("R")


class ICommandHandler(Generic[C, R]):
    """Protocol for CQRS command handlers."""

    @abstractmethod
    async def handle(self, command: C) -> R:
        ...
