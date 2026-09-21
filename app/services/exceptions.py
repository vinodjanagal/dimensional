"""Domain-level exceptions.

Routers translate these into HTTP status codes.
Services raise them without knowing HTTP exists.
"""


class ServiceError(Exception):
    """Base class for domain errors."""


class NotFoundError(ServiceError):
    """A referenced resource does not exist (or is not visible to the caller)."""


class ConflictError(ServiceError):
    """The operation would violate a uniqueness invariant."""


class ValidationError(ServiceError):
    """The request is well-formed but semantically invalid."""