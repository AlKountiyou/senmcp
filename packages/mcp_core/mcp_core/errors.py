from __future__ import annotations


class SenCivicError(Exception):
    """Base exception for the SenCivic MCP Stack."""


class ValidationError(SenCivicError):
    """Raised when input data fails validation."""


class NotFoundError(SenCivicError):
    """Raised when a requested resource cannot be found."""


class ExternalSourceError(SenCivicError):
    """Raised when an external source (e.g., HTTP) fails."""


class TrustPolicyError(SenCivicError):
    """Raised when a trust & safety policy blocks a request."""
