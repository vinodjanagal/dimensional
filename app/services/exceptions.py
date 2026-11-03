"""Domain-level exceptions.
Routers translate these into HTTP status codes.
Services raise them without knowing HTTP exists.
"""

from app.models import Unit


class ServiceError(Exception):
    """Base class for domain errors."""


class NotFoundError(ServiceError):
    """A referenced resource does not exist (or is not visible to the caller)."""


class ConflictError(ServiceError):
    """The operation would violate a uniqueness invariant."""


class ValidationError(ServiceError):
    """The request is well-formed but semantically invalid."""


class UnitError(Exception):
    """Base class for unit-related errors."""


class IncompatibleUnitsError(ValidationError):
    """Raised when two units have different dimensions."""

    def __init__(self, a: Unit, b: Unit) -> None:
        super().__init__(
            f"Cannot convert between {a.symbol!r} and {b.symbol!r}: "
            f"dimensions {a.dimension} and {b.dimension} differ"
        )
        self.a = a
        self.b = b
