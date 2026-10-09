import pytest
from sqlalchemy import select

from app.models import Unit
from scripts.seed_units import BASE_UNITS, DERIVED_UNITS, seed_units


@pytest.mark.asyncio
async def test_seed_units_is_idempotent(db):
    result = await db.execute(select(Unit))
    initial_units = result.scalars().all()

    expected_count = len(BASE_UNITS) + len(DERIVED_UNITS)
    assert len(initial_units) == expected_count

    total = await seed_units(db)
    await db.commit()

    result = await db.execute(select(Unit))
    final_units = result.scalars().all()

    assert total == expected_count
    assert len(final_units) == expected_count
