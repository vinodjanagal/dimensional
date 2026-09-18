"""Dimension algebra on 7-tuples of integer exponents.

Dimension order: (M, L, T, I, Θ, N, J)
    M = mass
    L = length
    T = time
    I = electric current
    Θ = thermodynamic temperature
    N = amount of substance
    J = luminous intensity

Every physical unit is a product of powers of the seven SI base units.
Multiplying units adds their dimension vectors; dividing subtracts;
raising to a power multiplies the vector by the exponent.
"""

from typing import TypeAlias


DIMENSION_LEN = 7

Dimension: TypeAlias = tuple[int, int, int, int, int, int, int]

DIMENSIONLESS: Dimension = (0, 0, 0, 0, 0, 0, 0)


class DimensionError(ValueError):
    """Raised when a dimension operation is invalid."""


def _check(dim: tuple[int, ...]) -> Dimension:
    if len(dim) != DIMENSION_LEN:
        raise DimensionError(
            f"Dimension must have {DIMENSION_LEN} components, got {len(dim)}: {dim}"
        )
    return dim  # type: ignore[return-value]


def multiply(a: Dimension, b: Dimension) -> Dimension:
    """Dimension of a * b. Vector addition."""
    _check(a)
    _check(b)
    return tuple(x + y for x, y in zip(a, b))  # type: ignore[return-value]


def divide(a: Dimension, b: Dimension) -> Dimension:
    """Dimension of a / b. Vector subtraction."""
    _check(a)
    _check(b)
    return tuple(x - y for x, y in zip(a, b))  # type: ignore[return-value]


def power(a: Dimension, n: int) -> Dimension:
    """Dimension of a ** n. Scalar multiplication."""
    _check(a)
    return tuple(x * n for x in a)  # type: ignore[return-value]


def is_dimensionless(a: Dimension) -> bool:
    return a == DIMENSIONLESS