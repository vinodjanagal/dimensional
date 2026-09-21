import pytest


@pytest.mark.asyncio
async def test_create_valid_formula(authenticated_client, test_user, db):
    # Create a note owned by test_user
    from app.models import Note
    note = Note(owner_id=test_user.id, title="Physics", content="...")
    db.add(note)
    await db.commit()
    await db.refresh(note)

    response = await authenticated_client.post(
        f"/notes/{note.id}/formulas",
        json={
            "name": "kinetic_energy",
            "expression": "kg * (m / s) ** 2",
            "result_unit_symbol": "J",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "kinetic_energy"
    assert body["result_unit"]["symbol"] == "J"


@pytest.mark.asyncio
async def test_create_invalid_formula_rejected(authenticated_client, test_user, db):
    """The Mars-orbiter test: a formula with the wrong dimension must be rejected."""
    from app.models import Note, Formula
    from sqlalchemy import select, func

    note = Note(owner_id=test_user.id, title="Physics", content="...")
    db.add(note)
    await db.commit()
    await db.refresh(note)

    # E = m * v has dimension kg*m/s, not J. Reject.
    response = await authenticated_client.post(
        f"/notes/{note.id}/formulas",
        json={
            "name": "wrong_energy",
            "expression": "kg * (m / s)",
            "result_unit_symbol": "J",
        },
    )
    assert response.status_code == 422
    assert "dimension" in response.json()["detail"].lower()

    # Nothing was written
    count = await db.execute(select(func.count()).select_from(Formula))
    assert count.scalar_one() == 0


@pytest.mark.asyncio
async def test_create_formula_unknown_symbol_in_expression(
    authenticated_client, test_user, db
):
    from app.models import Note
    note = Note(owner_id=test_user.id, title="Physics", content="...")
    db.add(note)
    await db.commit()
    await db.refresh(note)

    response = await authenticated_client.post(
        f"/notes/{note.id}/formulas",
        json={
            "name": "bad",
            "expression": "foo * m",
            "result_unit_symbol": "m",
        },
    )
    assert response.status_code == 422
    assert "foo" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_formula_unknown_result_unit(
    authenticated_client, test_user, db
):
    from app.models import Note
    note = Note(owner_id=test_user.id, title="Physics", content="...")
    db.add(note)
    await db.commit()
    await db.refresh(note)

    response = await authenticated_client.post(
        f"/notes/{note.id}/formulas",
        json={
            "name": "bad",
            "expression": "m",
            "result_unit_symbol": "furlong",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_formula_duplicate_name(
    authenticated_client, test_user, db
):
    from app.models import Note
    note = Note(owner_id=test_user.id, title="Physics", content="...")
    db.add(note)
    await db.commit()
    await db.refresh(note)

    payload = {
        "name": "height",
        "expression": "m",
        "result_unit_symbol": "m",
    }
    r1 = await authenticated_client.post(f"/notes/{note.id}/formulas", json=payload)
    assert r1.status_code == 201

    r2 = await authenticated_client.post(f"/notes/{note.id}/formulas", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_formula_for_other_users_note(
    authenticated_client, test_user, db
):
    from app.models import Note, User
    other = User(email="other@example.com", password_hash="x")
    db.add(other)
    await db.commit()
    await db.refresh(other)

    note = Note(owner_id=other.id, title="Private", content="...")
    db.add(note)
    await db.commit()
    await db.refresh(note)

    response = await authenticated_client.post(
        f"/notes/{note.id}/formulas",
        json={
            "name": "x",
            "expression": "m",
            "result_unit_symbol": "m",
        },
    )
    # 404, not 403 — do not leak existence
    assert response.status_code == 404