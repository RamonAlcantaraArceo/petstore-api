"""Domain exceptions shared by HTTP and gRPC adapters."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level service errors."""

    default_message = "Domain error"

    def __init__(self, message: str | None = None) -> None:
        """Initialize a domain error with an optional message override."""
        super().__init__(message or self.default_message)


class NotFoundError(DomainError):
    """Raised when a requested resource cannot be found."""

    default_message = "Resource not found"


class ValidationError(DomainError):
    """Raised when a request violates a domain validation rule."""

    default_message = "Validation error"
