
from app.main import app
from app.models import User
from app.database import get_current_user
import time


def test_get_notes(client):
    response = client.get("/notes")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_note(client):
    response = client.post(
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



def test_get_note_not_found(client):
    response = client.get("/notes/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Note not found"



def test_update_note(client):
    response = client.post(
        "/notes",
        json={
            "title": "before update",
            "content": "old content",
        },
    )

    assert response.status_code == 200
    note_id = response.json()["id"]

    response = client.put(
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



def test_delete_note(client):
    response = client.post(
        "/notes",
        json={
            "title": "to delete",
            "content": "temporary note",
        },
    )

    assert response.status_code == 200
    note_id = response.json()["id"]

    response = client.delete(f"/notes/{note_id}")

    assert response.status_code == 200
    assert response.json()["message"] == "Note deleted successfully"

    # Verify it is actually gone
    response = client.get(f"/notes/{note_id}")

    assert response.status_code == 404


def test_user_cannot_get_another_users_note(client, db, test_user):
    response = client.post(
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
    db.commit()
    db.refresh(other_user)

    app.dependency_overrides[get_current_user] = lambda: other_user

    response = client.get(f"/notes/{note_id}")

    assert response.status_code == 404


def test_user_cannot_update_another_users_note(client, db, test_user):
    # User 1 creates a note
    response = client.post(
        "/notes",
        json={
            "title": "before update",
            "content": "old content",
        },
    )

    assert response.status_code == 200
    note_id = response.json()["id"]

    # Create User 2
    other_user = User(
        email="other@example.com",
        password_hash="test_hash",
    )

    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    # Authenticate as User 2
    app.dependency_overrides[get_current_user] = lambda: other_user

    # User 2 tries to update User 1's note
    response = client.put(
        f"/notes/{note_id}",
        json={
            "title": "after update",
            "content": "new content",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Note not found"

def test_user_cannot_delete_another_users_note(client, db, test_user):
    # User 1 creates a note
    response = client.post(
        "/notes",
        json={
            "title": "to delete",
            "content": "temporary note",
        },
    )

    assert response.status_code == 200
    note_id = response.json()["id"]

    # Create User 2
    other_user = User(
        email="other@example.com",
        password_hash="test_hash",
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    # Authenticate as User 2
    app.dependency_overrides[get_current_user] = lambda: other_user

    # User 2 tries to delete User 1's note
    response = client.delete(f"/notes/{note_id}")
    assert response.status_code == 404

    # Switch back to User 1
    app.dependency_overrides[get_current_user] = lambda: test_user

    # Verify User 1's note still exists
    response = client.get(f"/notes/{note_id}")
    assert response.status_code == 200


def test_update_note_changes_updated_at(client):
    response = client.post(
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

    response = client.put(
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