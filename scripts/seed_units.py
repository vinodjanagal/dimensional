"""Seed the unit system. Idempotent — safe to run repeatedly.

Derived units are *computed* from base dimensions, not hardcoded.
This eliminates the class of bug where a typo in a hardcoded vector
lies dormant until it silently corrupts a downstream calculation.

Run after `alembic upgrade head`:

  Host:       python -m scripts.seed_units
  Container:  docker compose run --rm api python -m scripts.seed_units
"""

import asyncio
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models import Unit
from app.services.dimension import (
    Dimension,
    divide,
    multiply,
    power,
)


# ---- Base dimension constants (the seven SI base dimensions) ----
# Order: (M, L, T, I, Θ, N, J)
DIM_MASS        = (1, 0, 0, 0, 0, 0, 0)
DIM_LENGTH      = (0, 1, 0, 0, 0, 0, 0)
DIM_TIME        = (0, 0, 1, 0, 0, 0, 0)
DIM_CURRENT     = (0, 0, 0, 1, 0, 0, 0)
DIM_TEMPERATURE = (0, 0, 0, 0, 1, 0, 0)
DIM_AMOUNT      = (0, 0, 0, 0, 0, 1, 0)
DIM_LUMINOUS    = (0, 0, 0, 0, 0, 0, 1)

# ---- Derived dimensions, computed from the base ones ----
DIM_FORCE     = divide(multiply(DIM_MASS, DIM_LENGTH), power(DIM_TIME, 2))   # N
DIM_ENERGY    = multiply(DIM_FORCE, DIM_LENGTH)                              # J
DIM_POWER     = divide(DIM_ENERGY, DIM_TIME)                                 # W
DIM_PRESSURE  = divide(DIM_FORCE, power(DIM_LENGTH, 2))                      # Pa
DIM_FREQUENCY = divide((0, 0, 0, 0, 0, 0, 0), DIM_TIME)                      # Hz
DIM_CHARGE    = multiply(DIM_CURRENT, DIM_TIME)                              # C
DIM_VOLTAGE   = divide(DIM_POWER, DIM_CURRENT)                               # V
DIM_RESISTANCE = divide(DIM_VOLTAGE, DIM_CURRENT)                            # Ω


class BaseUnit(NamedTuple):
    name: str
    symbol: str
    dimension: Dimension


class DerivedUnit(NamedTuple):
    name: str
    symbol: str
    dimension: Dimension
    factor: Decimal
    offset: Decimal
    base_symbol: str


BASE_UNITS: list[BaseUnit] = [
    BaseUnit("kilogram", "kg",  DIM_MASS),
    BaseUnit("meter",    "m",   DIM_LENGTH),
    BaseUnit("second",   "s",   DIM_TIME),
    BaseUnit("ampere",   "A",   DIM_CURRENT),
    BaseUnit("kelvin",   "K",   DIM_TEMPERATURE),
    BaseUnit("mole",     "mol", DIM_AMOUNT),
    BaseUnit("candela",  "cd",  DIM_LUMINOUS),
]

DERIVED_UNITS: list[DerivedUnit] = [
    # Prefixed length
    DerivedUnit("kilometer",  "km", DIM_LENGTH,  Decimal("1000"),     Decimal("0"), "m"),
    DerivedUnit("centimeter", "cm", DIM_LENGTH,  Decimal("0.01"),     Decimal("0"), "m"),
    DerivedUnit("millimeter", "mm", DIM_LENGTH,  Decimal("0.001"),    Decimal("0"), "m"),
    # Prefixed mass
    DerivedUnit("gram",       "g",  DIM_MASS,    Decimal("0.001"),    Decimal("0"), "kg"),
    DerivedUnit("milligram",  "mg", DIM_MASS,    Decimal("0.000001"), Decimal("0"), "kg"),
    # Time
    DerivedUnit("minute",     "min", DIM_TIME,   Decimal("60"),       Decimal("0"), "s"),
    DerivedUnit("hour",       "h",   DIM_TIME,   Decimal("3600"),     Decimal("0"), "s"),
    DerivedUnit("day",        "d",   DIM_TIME,   Decimal("86400"),    Decimal("0"), "s"),
    # Temperature (affine)
    DerivedUnit("degree Celsius", "°C", DIM_TEMPERATURE, Decimal("1"), Decimal("273.15"), "K"),
    # Named SI derived units
    DerivedUnit("newton",   "N",  DIM_FORCE,      Decimal("1"), Decimal("0"), "kg"),
    DerivedUnit("joule",    "J",  DIM_ENERGY,     Decimal("1"), Decimal("0"), "kg"),
    DerivedUnit("watt",     "W",  DIM_POWER,      Decimal("1"), Decimal("0"), "kg"),
    DerivedUnit("pascal",   "Pa", DIM_PRESSURE,   Decimal("1"), Decimal("0"), "kg"),
    DerivedUnit("hertz",    "Hz", DIM_FREQUENCY,  Decimal("1"), Decimal("0"), "s"),
    DerivedUnit("coulomb",  "C",  DIM_CHARGE,     Decimal("1"), Decimal("0"), "A"),
    DerivedUnit("volt",     "V",  DIM_VOLTAGE,    Decimal("1"), Decimal("0"), "kg"),
    DerivedUnit("ohm",      "Ω",  DIM_RESISTANCE, Decimal("1"), Decimal("0"), "kg"),
]


async def seed_units(db: AsyncSession) -> int:
    """Seed base and derived units. Returns total count after seeding."""
    # Pass 1 — base units (no FK dependency)
    for u in BASE_UNITS:
        stmt = (
            insert(Unit)
            .values(
                name=u.name,
                symbol=u.symbol,
                dimension=list(u.dimension),
                factor=Decimal("1"),
                offset=Decimal("0"),
                is_base=True,
                base_unit_id=None,
            )
            .on_conflict_do_nothing(index_elements=["symbol"])
        )
        await db.execute(stmt)
    await db.flush()

    # Pass 2 — derived units, pointing at their base
    result = await db.execute(select(Unit).where(Unit.is_base.is_(True)))
    base_by_symbol = {u.symbol: u.id for u in result.scalars().all()}

    for u in DERIVED_UNITS:
        base_id = base_by_symbol.get(u.base_symbol)
        if base_id is None:
            raise RuntimeError(
                f"Base unit {u.base_symbol!r} not found; seed base units first"
            )

        stmt = (
            insert(Unit)
            .values(
                name=u.name,
                symbol=u.symbol,
                dimension=list(u.dimension),
                factor=u.factor,
                offset=u.offset,
                is_base=False,
                base_unit_id=base_id,
            )
            .on_conflict_do_nothing(index_elements=["symbol"])
        )
        await db.execute(stmt)
    await db.flush()

    count_result = await db.execute(select(Unit))
    return len(count_result.scalars().all())


async def _cli() -> None:
    async with SessionLocal() as db:
        total = await seed_units(db)
        await db.commit()

        all_units = (await db.execute(select(Unit).order_by(Unit.symbol))).scalars().all()
        print(f"\nUnits in DB: {total}")
        for u in all_units:
            base = "base" if u.is_base else f"→ {u.base_unit_id}"
            print(f"  {u.symbol:5s} {u.name:18s} dim={u.dimension} {base}")


if __name__ == "__main__":
    asyncio.run(_cli())