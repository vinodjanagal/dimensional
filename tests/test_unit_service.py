from decimal import Decimal

import pytest

from app.models import Unit
from app.services.unit_service import (
    IncompatibleUnitsError,
    convert,
    from_base,
    is_compatible,
    to_base,
)


# ---------- Test doubles ----------
# We do not touch the DB. We build Unit objects in-memory.

def make_unit(
    symbol: str,
    dimension: list[int],
    factor: str = "1",
    offset: str = "0",
    is_base: bool = False,
) -> Unit:
    return Unit(
        symbol=symbol,
        name=symbol,
        dimension=dimension,
        factor=Decimal(factor),
        offset=Decimal(offset),
        is_base=is_base,
    )


KG = make_unit("kg", [1, 0, 0, 0, 0, 0, 0], factor="1", is_base=True)
G  = make_unit("g",  [1, 0, 0, 0, 0, 0, 0], factor="0.001")
M  = make_unit("m",  [0, 1, 0, 0, 0, 0, 0], factor="1", is_base=True)
KM = make_unit("km", [0, 1, 0, 0, 0, 0, 0], factor="1000")
CM = make_unit("cm", [0, 1, 0, 0, 0, 0, 0], factor="0.01")
K  = make_unit("K",  [0, 0, 0, 0, 1, 0, 0], factor="1", is_base=True)
C  = make_unit("°C", [0, 0, 0, 0, 1, 0, 0], factor="1", offset="273.15")


# ---------- is_compatible ----------

def test_same_dimension_is_compatible():
    assert is_compatible(KM, M)
    assert is_compatible(M, CM)
    assert is_compatible(KG, G)


def test_different_dimension_is_incompatible():
    assert not is_compatible(KG, M)
    assert not is_compatible(M, K)


# ---------- to_base / from_base ----------

def test_to_base_kilometer_to_meter():
    assert to_base(Decimal("5"), KM) == Decimal("5000")


def test_from_base_meter_to_kilometer():
    assert from_base(Decimal("5000"), KM) == Decimal("5")


def test_to_base_celsius_to_kelvin():
    assert to_base(Decimal("0"), C) == Decimal("273.15")
    assert to_base(Decimal("100"), C) == Decimal("373.15")


def test_from_base_kelvin_to_celsius():
    assert from_base(Decimal("273.15"), C) == Decimal("0")
    assert from_base(Decimal("373.15"), C) == Decimal("100")


# ---------- convert ----------

def test_km_to_m():
    assert convert(Decimal("5"), KM, M) == Decimal("5000")


def test_m_to_km():
    assert convert(Decimal("5000"), M, KM) == Decimal("5")


def test_km_to_cm():
    assert convert(Decimal("1"), KM, CM) == Decimal("100000")


def test_g_to_kg():
    assert convert(Decimal("2500"), G, KG) == Decimal("2.5")


def test_celsius_to_kelvin():
    assert convert(Decimal("0"), C, K) == Decimal("273.15")
    assert convert(Decimal("100"), C, K) == Decimal("373.15")


def test_kelvin_to_celsius():
    assert convert(Decimal("273.15"), K, C) == Decimal("0")


def test_negative_celsius_to_kelvin():
    # -40 °C is famously equal to -40 °F; to Kelvin it is 233.15
    assert convert(Decimal("-40"), C, K) == Decimal("233.15")


# ---------- round trip ----------

@pytest.mark.parametrize("value", ["0", "1", "100", "0.001", "-42.5"])
def test_round_trip_km_m(value):
    v = Decimal(value)
    assert convert(convert(v, KM, M), M, KM) == v


@pytest.mark.parametrize("value", ["0", "100", "-40", "37"])
def test_round_trip_celsius_kelvin(value):
    v = Decimal(value)
    assert convert(convert(v, C, K), K, C) == v


# ---------- errors ----------

def test_convert_incompatible_raises():
    with pytest.raises(IncompatibleUnitsError) as exc_info:
        convert(Decimal("1"), KG, M)

    err = exc_info.value
    assert err.a is KG
    assert err.b is M
    assert "kg" in str(err)
    assert "m" in str(err)