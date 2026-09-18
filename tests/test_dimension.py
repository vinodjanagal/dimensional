from app.services.dimension import (
    DIMENSIONLESS,
    DimensionError,
    divide,
    is_dimensionless,
    multiply,
    power,
)


# Standard dimension tuples for readability
MASS = (1, 0, 0, 0, 0, 0, 0)
LENGTH = (0, 1, 0, 0, 0, 0, 0)
TIME = (0, 0, 1, 0, 0, 0, 0)
CURRENT = (0, 0, 0, 1, 0, 0, 0)
TEMPERATURE = (0, 0, 0, 0, 1, 0, 0)
AMOUNT = (0, 0, 0, 0, 0, 1, 0)
LUMINOUS = (0, 0, 0, 0, 0, 0, 1)


# ---------- multiply ----------

def test_multiply_kg_m():
    # kg * m -> (1, 1, 0, ...)
    assert multiply(MASS, LENGTH) == (1, 1, 0, 0, 0, 0, 0)


def test_multiply_is_commutative():
    assert multiply(MASS, LENGTH) == multiply(LENGTH, MASS)


def test_multiply_identity_is_dimensionless():
    assert multiply(MASS, DIMENSIONLESS) == MASS
    assert multiply(DIMENSIONLESS, LENGTH) == LENGTH


# ---------- divide ----------

def test_divide_m_by_s():
    # speed: m / s -> (0, 1, -1, 0, 0, 0, 0)
    assert divide(LENGTH, TIME) == (0, 1, -1, 0, 0, 0, 0)


def test_divide_self_is_dimensionless():
    assert divide(MASS, MASS) == DIMENSIONLESS


def test_divide_gives_inverse():
    # 1 / s -> (0, 0, -1, 0, 0, 0, 0)
    assert divide(DIMENSIONLESS, TIME) == (0, 0, -1, 0, 0, 0, 0)


# ---------- power ----------

def test_power_m_squared():
    # area: m ** 2
    assert power(LENGTH, 2) == (0, 2, 0, 0, 0, 0, 0)


def test_power_s_inverse_squared():
    # s ** -2
    assert power(TIME, -2) == (0, 0, -2, 0, 0, 0, 0)


def test_power_zero_is_dimensionless():
    assert power(LENGTH, 0) == DIMENSIONLESS
    assert power(MASS, 0) == DIMENSIONLESS


# ---------- derived physical units ----------

def test_newton_dimension():
    # N = kg * m / s ** 2
    force = divide(multiply(MASS, LENGTH), power(TIME, 2))
    assert force == (1, 1, -2, 0, 0, 0, 0)


def test_joule_dimension():
    # J = N * m
    force = (1, 1, -2, 0, 0, 0, 0)
    energy = multiply(force, LENGTH)
    assert energy == (1, 2, -2, 0, 0, 0, 0)


def test_watt_dimension():
    # W = J / s
    energy = (1, 2, -2, 0, 0, 0, 0)
    power_w = divide(energy, TIME)
    assert power_w == (1, 2, -3, 0, 0, 0, 0)


def test_pascal_dimension():
    # Pa = N / m ** 2
    force = (1, 1, -2, 0, 0, 0, 0)
    area = power(LENGTH, 2)
    pressure = divide(force, area)
    assert pressure == (1, -1, -2, 0, 0, 0, 0)


def test_hz_dimension():
    # Hz = 1 / s
    hz = divide(DIMENSIONLESS, TIME)
    assert hz == (0, 0, -1, 0, 0, 0, 0)


# ---------- dimensionless ----------

def test_is_dimensionless_true():
    assert is_dimensionless(DIMENSIONLESS)


def test_is_dimensionless_false():
    assert not is_dimensionless(MASS)
    assert not is_dimensionless((0, 0, 1, 0, 0, 0, 0))


def test_velocity_ratio_is_dimensionless():
    # (m / s) / (m / s) -> dimensionless
    speed = divide(LENGTH, TIME)
    assert divide(speed, speed) == DIMENSIONLESS


# ---------- errors ----------

def test_wrong_length_raises():
    import pytest
    with pytest.raises(DimensionError):
        multiply((1, 0, 0), MASS)

    with pytest.raises(DimensionError):
        divide(MASS, (1, 0, 0, 0, 0, 0, 0, 0))

    with pytest.raises(DimensionError):
        power((1, 2), 2)


# ---------- algebraic properties ----------

def test_multiply_associative():
    assert multiply(multiply(MASS, LENGTH), TIME) == multiply(MASS, multiply(LENGTH, TIME))


def test_multiply_divide_inverse():
    # (a * b) / b == a
    a = MASS
    b = LENGTH
    assert divide(multiply(a, b), b) == a


def test_power_distributes_over_multiply():
    # (a * b) ** n == (a ** n) * (b ** n)
    a = LENGTH
    b = TIME
    n = 3
    assert power(multiply(a, b), n) == multiply(power(a, n), power(b, n))