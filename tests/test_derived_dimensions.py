"""Cross-check our computed dimensions against physics textbooks.

These values are the canonical SI dimensions for named units.
If our algebra disagrees with a physics textbook, our algebra is wrong.

Reference: BIPM SI Brochure, 9th edition (2019).
"""

from scripts.seed_units import (
    DIM_CHARGE,
    DIM_CURRENT,
    DIM_ENERGY,
    DIM_FORCE,
    DIM_FREQUENCY,
    DIM_LENGTH,
    DIM_MASS,
    DIM_POWER,
    DIM_PRESSURE,
    DIM_RESISTANCE,
    DIM_TEMPERATURE,
    DIM_TIME,
    DIM_VOLTAGE,
)


def test_newton_is_kg_m_s_squared():
    # Newton: force = mass * acceleration
    assert DIM_FORCE == (1, 1, -2, 0, 0, 0, 0)


def test_joule_is_kg_m2_s2():
    # Joule: energy = force * distance
    assert DIM_ENERGY == (1, 2, -2, 0, 0, 0, 0)


def test_watt_is_kg_m2_s3():
    # Watt: power = energy / time
    assert DIM_POWER == (1, 2, -3, 0, 0, 0, 0)


def test_pascal_is_kg_m_inverse_s2():
    # Pascal: pressure = force / area
    assert DIM_PRESSURE == (1, -1, -2, 0, 0, 0, 0)


def test_hertz_is_inverse_second():
    # Hertz: frequency = 1 / time
    assert DIM_FREQUENCY == (0, 0, -1, 0, 0, 0, 0)


def test_coulomb_is_ampere_second():
    # Coulomb: charge = current * time
    assert DIM_CHARGE == (0, 0, 1, 1, 0, 0, 0)


def test_volt_is_kg_m2_s3_a_inverse():
    # Volt: voltage = power / current
    assert DIM_VOLTAGE == (1, 2, -3, -1, 0, 0, 0)


def test_ohm_is_kg_m2_s3_a_inverse_squared():
    # Ohm: resistance = voltage / current
    assert DIM_RESISTANCE == (1, 2, -3, -2, 0, 0, 0)