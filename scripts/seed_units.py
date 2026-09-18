"""Seed the unit system. Idempotent — safe to run repeatedly.

Run after `alembic upgrade head`.

  Host:       python -m scripts.seed_units
  Container:  docker compose run --rm api python -m scripts.seed_units
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models import Unit


# Dimension order: (M, L, T, I, Θ, N, J)
# fmt: off
BASE_UNITS = [
    {"name": "kilogram", "symbol": "kg",  "dimension": [1, 0, 0, 0, 0, 0, 0]},
    {"name": "meter",    "symbol": "m",   "dimension": [0, 1, 0, 0, 0, 0, 0]},
    {"name": "second",   "symbol": "s",   "dimension": [0, 0, 1, 0, 0, 0, 0]},
    {"name": "ampere",   "symbol": "A",   "dimension": [0, 0, 0, 1, 0, 0, 0]},
    {"name": "kelvin",   "symbol": "K",   "dimension": [0, 0, 0, 0, 1, 0, 0]},
    {"name": "mole",     "symbol": "mol", "dimension": [0, 0, 0, 0, 0, 1, 0]},
    {"name": "candela",  "symbol": "cd",  "dimension": [0, 0, 0, 0, 0, 0, 1]},
]

DERIVED_UNITS = [
    ("kilometer",      "km",  [0, 1, 0, 0, 0, 0, 0], Decimal("1000"),     Decimal("0"), "m"),
    ("centimeter",     "cm",  [0, 1, 0, 0, 0, 0, 0], Decimal("0.01"),     Decimal("0"), "m"),
    ("millimeter",     "mm",  [0, 1, 0, 0, 0, 0, 0], Decimal("0.001"),    Decimal("0"), "m"),
    ("gram",           "g",   [1, 0, 0, 0, 0, 0, 0], Decimal("0.001"),    Decimal("0"), "kg"),
    ("milligram",      "mg",  [1, 0, 0, 0, 0, 0, 0], Decimal("0.000001"), Decimal("0"), "kg"),
    ("minute",         "min", [0, 0, 1, 0, 0, 0, 0], Decimal("60"),       Decimal("0"), "s"),
    ("hour",           "h",   [0, 0, 1, 0, 0, 0, 0], Decimal("3600"),     Decimal("0"), "s"),
    ("day",            "d",   [0, 0, 1, 0, 0, 0, 0], Decimal("86400"),    Decimal("0"), "s"),
    ("degree Celsius", "°C",  [0, 0, 0, 0, 1, 0, 0], Decimal("1"),        Decimal("273.15"), "K"),
]
# fmt: on


async def seed_units(db: AsyncSession) -> int:
    """Seed base and derived units. Returns total count after seeding."""
    # Pass 1 — base units (no FK dependency)
    for u in BASE_UNITS:
        stmt = (
            insert(Unit)
            .values(
                name=u["name"],
                symbol=u["symbol"],
                dimension=u["dimension"],
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

    for name, symbol, dim, factor, offset, base_symbol in DERIVED_UNITS:
        base_id = base_by_symbol.get(base_symbol)
        if base_id is None:
            raise RuntimeError(
                f"Base unit {base_symbol!r} not found; seed base units first"
            )

        stmt = (
            insert(Unit)
            .values(
                name=name,
                symbol=symbol,
                dimension=dim,
                factor=factor,
                offset=offset,
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

        all_units = (await db.execute(select(Unit))).scalars().all()
        print(f"\nUnits in DB: {total}")
        for u in sorted(all_units, key=lambda x: x.symbol):
            print(
                f"  {u.symbol:5s} {u.name:20s} "
                f"dim={u.dimension} factor={u.factor} offset={u.offset}"
            )


if __name__ == "__main__":
    asyncio.run(_cli())