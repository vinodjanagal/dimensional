import pytest


@pytest.mark.asyncio
async def test_create_quantity(authenticated_client, test_user, db):
    from app.models import Note
    note = Note(owner_id=test_user.id, title="Physics", content="...")
    db.add(note)
    await db.commit()
    await db.refresh(note)

    response = await authenticated_client.post(
        f"/notes/{note.id}/quantities",
        json={"value": "9.81", "unit_symbol": "m"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["value"] == "9.81"
    assert body["unit"]["symbol"] == "m"


@pytest.mark.asyncio
async def test_create_quantity_unknown_unit(authenticated_client, test_user, db):
    from app.models import Note
    note = Note(owner_id=test_user.id, title="Physics", content="...")
    db.add(note)
    await db.commit()
    await db.refresh(note)

    response = await authenticated_client.post(
        f"/notes/{note.id}/quantities",
        json={"value": "1", "unit_symbol": "zzz"},
    )
    assert response.status_code == 404