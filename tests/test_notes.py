import pytest
from app.main import app
from app.models import User
from app.auth.auth import get_current_user
import time

@pytest.mark.asyncio
async def test_get_notes(authenticated_client):
    response = await authenticated_client.get("/notes")

    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_create_note(authenticated_client):
    response = await authenticated_client.post(
        "/notes",
        json={
            "title": "pytest",
            "content": "testing note creation",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "pytest"
    assert data["content"] == "testing note creation"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

@pytest.mark.asyncio
async def test_get_note_not_found(authenticated_client):
    response = await authenticated_client.get("/notes/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Note not found"

@pytest.mark.asyncio
async def test_update_note(authenticated_client):
    response = await authenticated_client.post(
        "/notes",
        json={
            "title": "before update",
            "content": "old content",
        },
    )

    assert response.status_code == 200
    note_id = response.json()["id"]

    response = await authenticated_client.put(
        f"/notes/{note_id}",
        json={
            "title": "after update",
            "content": "new content",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == note_id
    assert data["title"] == "after update"
    assert data["content"] == "new content"

@pytest.mark.asyncio
async def test_delete_note(authenticated_client):
    response = await authenticated_client.post(
        "/notes",
        json={
            "title": "to delete",
            "content": "temporary note",
        },
    )

    assert response.status_code == 200
    note_id = response.json()["id"]

    response = await authenticated_client.delete(f"/notes/{note_id}")

    assert response.status_code == 200
    assert response.json()["message"] == "Note deleted successfully"

    response = await authenticated_client.get(f"/notes/{note_id}")

    assert response.status_code == 404

@pytest.mark.asyncio
async def test_user_cannot_get_another_users_note(
    authenticated_client,
    db,
    test_user,
):
    response = await authenticated_client.post(
        "/notes",
        json={
            "title": "private note",
            "content": "user 1 content",
        },
    )

    assert response.status_code == 200
    note_id = response.json()["id"]

    other_user = User(
        email="other@example.com",
        password_hash="test_hash",
    )

    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)

    app.dependency_overrides[get_current_user] = (
        lambda: other_user
    )

    response = await authenticated_client.get(
        f"/notes/{note_id}"
    )

    assert response.status_code == 404

@pytest.mark.asyncio
async def test_user_cannot_update_another_users_note(
    authenticated_client,
    db,
    test_user,
):
    response = await authenticated_client.post(
        "/notes",
        json={
            "title": "before update",
            "content": "old content",
        },
    )

    assert response.status_code == 200
    note_id = response.json()["id"]

    other_user = User(
        email="other@example.com",
        password_hash="test_hash",
    )

    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)

    app.dependency_overrides[get_current_user] = (
        lambda: other_user
    )

    response = await authenticated_client.put(
        f"/notes/{note_id}",
        json={
            "title": "after update",
            "content": "new content",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Note not found"

@pytest.mark.asyncio
async def test_user_cannot_delete_another_users_note(
    authenticated_client,
    db,
    test_user,
):
    response = await authenticated_client.post(
        "/notes",
        json={
            "title": "to delete",
            "content": "temporary note",
        },
    )

    assert response.status_code == 200
    note_id = response.json()["id"]

    other_user = User(
        email="other@example.com",
        password_hash="test_hash",
    )

    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)

    app.dependency_overrides[get_current_user] = (
        lambda: other_user
    )

    response = await authenticated_client.delete(
        f"/notes/{note_id}"
    )

    assert response.status_code == 404

    app.dependency_overrides[get_current_user] = (
        lambda: test_user
    )

    response = await authenticated_client.get(
        f"/notes/{note_id}"
    )

    assert response.status_code == 200

@pytest.mark.asyncio
async def test_update_note_changes_updated_at(authenticated_client):
    response = await authenticated_client.post(
        "/notes",
        json={
            "title": "original",
            "content": "original content",
        },
    )

    assert response.status_code == 200

    note = response.json()

    created_at = note["created_at"]
    updated_at = note["updated_at"]

    time.sleep(0.01)

    response = await authenticated_client.put(
        f"/notes/{note['id']}",
        json={
            "title": "updated",
            "content": "updated content",
        },
    )

    assert response.status_code == 200

    updated_note = response.json()

    assert updated_note["created_at"] == created_at
    assert updated_note["updated_at"] != updated_at
