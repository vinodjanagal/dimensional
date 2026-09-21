"""Reusable Pydantic types for Dimensional."""

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer


def _trim_decimal(value: Decimal) -> str:
    """Serialize a Decimal without trailing zeros or scientific notation.

    Examples:
        Decimal("9.81000000000000000000") -> "9.81"
        Decimal("1.00000000000000000000") -> "1"
        Decimal("0E-20")                  -> "0"
        Decimal("100.000")                -> "100"
    """
    # normalize() strips trailing zeros, but can produce exponent form:
    #   Decimal("100").normalize() -> Decimal("1E+2")
    # format(..., "f") forces positional notation and removes the exponent.
    return format(value.normalize(), "f")


DecimalStr = Annotated[Decimal, PlainSerializer(_trim_decimal, return_type=str)]