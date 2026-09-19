import pytest

from app.services.dimension import DIMENSIONLESS
from app.services.expression import (
    ExpressionError,
    evaluate_dimension,
)


# Dimension lookup table for tests — do not touch the DB.
LOOKUP = {
    "kg":  (1, 0, 0, 0, 0, 0, 0),
    "m":   (0, 1, 0, 0, 0, 0, 0),
    "s":   (0, 0, 1, 0, 0, 0, 0),
    "A":   (0, 0, 0, 1, 0, 0, 0),
    "K":   (0, 0, 0, 0, 1, 0, 0),
    "N":   (1, 1, -2, 0, 0, 0, 0),
    "J":   (1, 2, -2, 0, 0, 0, 0),
    "W":   (1, 2, -3, 0, 0, 0, 0),
    "Pa":  (1, -1, -2, 0, 0, 0, 0),
}


def dim(expr: str) -> tuple[int, ...]:
    return evaluate_dimension(expr, LOOKUP.__getitem__)


# ---------- names ----------

def test_single_name():
    assert dim("kg") == (1, 0, 0, 0, 0, 0, 0)
    assert dim("m")  == (0, 1, 0, 0, 0, 0, 0)


def test_unknown_name_raises():
    with pytest.raises(ExpressionError, match="Unknown unit"):
        dim("furlong")


# ---------- multiplication ----------

def test_kg_times_m():
    assert dim("kg * m") == (1, 1, 0, 0, 0, 0, 0)


def test_mult_chain():
    assert dim("kg * m * s") == (1, 1, 1, 0, 0, 0, 0)


# ---------- division ----------

def test_speed():
    assert dim("m / s") == (0, 1, -1, 0, 0, 0, 0)


def test_acceleration():
    assert dim("m / s / s") == (0, 1, -2, 0, 0, 0, 0)


def test_force_derived():
    assert dim("kg * m / s ** 2") == (1, 1, -2, 0, 0, 0, 0)


def test_energy_derived():
    assert dim("kg * m ** 2 / s ** 2") == (1, 2, -2, 0, 0, 0, 0)


# ---------- power ----------

def test_power_positive():
    assert dim("m ** 2") == (0, 2, 0, 0, 0, 0, 0)


def test_power_negative():
    assert dim("s ** -1") == (0, 0, -1, 0, 0, 0, 0)


def test_power_zero_gives_dimensionless():
    assert dim("kg ** 0") == DIMENSIONLESS


def test_power_of_expression():
    assert dim("(kg * m) ** 2") == (2, 2, 0, 0, 0, 0, 0)


# ---------- parentheses ----------

def test_parentheses_change_grouping():
    # (kg / m) / s vs kg / (m / s)
    a = dim("(kg / m) / s")
    b = dim("kg / (m / s)")
    assert a != b
    assert a == (1, -1, -1, 0, 0, 0, 0)
    assert b == (1, -1, 1, 0, 0, 0, 0)


# ---------- numbers ----------

def test_number_is_dimensionless():
    assert dim("2") == DIMENSIONLESS
    assert dim("3.14") == DIMENSIONLESS


def test_number_times_unit_preserves_dimension():
    assert dim("2 * kg") == (1, 0, 0, 0, 0, 0, 0)
    assert dim("0.5 * m ** 2") == (0, 2, 0, 0, 0, 0, 0)


# ---------- unary ----------

def test_unary_minus_preserves_dimension():
    assert dim("-kg") == (1, 0, 0, 0, 0, 0, 0)


def test_unary_plus_preserves_dimension():
    assert dim("+m") == (0, 1, 0, 0, 0, 0, 0)


# ---------- addition / subtraction ----------

def test_add_same_dimension_ok():
    # Both sides have dimension kg
    assert dim("kg + kg") == (1, 0, 0, 0, 0, 0, 0)


def test_add_different_dimensions_raises():
    with pytest.raises(ExpressionError, match="Cannot add"):
        dim("kg + m")


def test_sub_different_dimensions_raises():
    with pytest.raises(ExpressionError, match="Cannot subtract"):
        dim("kg - m")


# ---------- parse errors ----------

def test_syntax_error_raises():
    with pytest.raises(ExpressionError, match="Syntax error"):
        dim("kg * * m")


def test_empty_expression_raises():
    with pytest.raises(ExpressionError):
        dim("")


def test_unsupported_call_raises():
    with pytest.raises(ExpressionError, match="Unsupported"):
        dim("foo(kg)")


def test_unsupported_attribute_raises():
    with pytest.raises(ExpressionError, match="Unsupported"):
        dim("kg.attribute")


# ---------- malformed exponents ----------

def test_float_exponent_raises():
    with pytest.raises(ExpressionError, match="integer"):
        dim("m ** 1.5")


def test_variable_exponent_raises():
    with pytest.raises(ExpressionError, match="integer"):
        dim("m ** s")


# ---------- physics: catch the missing-square bug ----------

def test_kinetic_energy_with_v_squared_is_valid():
    # E = m * v**2 has dimension of energy [J] = (1, 2, -2, 0, 0, 0, 0)
    # Here we express it purely in base dimensions.
    assert dim("kg * (m / s) ** 2") == (1, 2, -2, 0, 0, 0, 0)


def test_kinetic_energy_with_v_not_squared_is_wrong():
    # E = m * v has dimension (1, 1, -1, 0, 0, 0, 0), not energy.
    assert dim("kg * (m / s)") == (1, 1, -1, 0, 0, 0, 0)
    assert dim("kg * (m / s)") != dim("J")