"""Unit conversion and dimensional analysis.

Pure functions. No DB. No I/O. All inputs are value objects.
"""

from decimal import Decimal

from app.models import Unit


class UnitError(Exception):
    """Base class for unit-related errors."""


class IncompatibleUnitsError(UnitError):
    """Raised when two units have different dimensions."""

    def __init__(self, a: Unit, b: Unit) -> None:
        super().__init__(
            f"Cannot convert between {a.symbol!r} and {b.symbol!r}: "
            f"dimensions {a.dimension} and {b.dimension} differ"
        )
        self.a = a
        self.b = b


def is_compatible(a: Unit, b: Unit) -> bool:
    """Two units are compatible iff their dimension vectors are equal."""
    return a.dimension == b.dimension


def to_base(value: Decimal, unit: Unit) -> Decimal:
    """Convert `value` in `unit` to its SI base unit."""
    return value * unit.factor + unit.offset


def from_base(value: Decimal, unit: Unit) -> Decimal:
    """Convert a value expressed in `unit`'s SI base to `unit`."""
    return (value - unit.offset) / unit.factor


def convert(value: Decimal, frm: Unit, to: Unit) -> Decimal:
    """Convert `value` from `frm` to `to`.

    Raises IncompatibleUnitsError if the units have different dimensions.
    """
    if not is_compatible(frm, to):
        raise IncompatibleUnitsError(frm, to)
    return from_base(to_base(value, frm), to)