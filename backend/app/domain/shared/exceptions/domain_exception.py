from __future__ import annotations


class DomainException(Exception):
    """Base exception for all domain rule violations."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"
