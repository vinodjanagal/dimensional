import pytest
import jwt
from app.models import User
from app.auth.auth import get_current_user
from app.auth.security import ALGORITHM, SECRET_KEY
from app.main import app
from datetime import datetime, timedelta, timezone
from app.auth.security import create_access_token

@pytest.mark.asyncio
async def test_register_user(client):
    response = await client.post(
        "/auth/register",
        json={
            "email": "new@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "new@example.com"
    assert "password" not in data
    assert "password_hash" not in data

@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "password123",
    }

    response = await client.post(
        "/auth/register",
        json=payload,
    )

    assert response.status_code == 200

    response = await client.post(
        "/auth/register",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

@pytest.mark.asyncio
async def test_login_user(client):
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "password123",
        },
    )

    assert register_response.status_code == 200

    user_id = register_response.json()["id"]

    response = await client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    access_payload = jwt.decode(
        data["access_token"],
        SECRET_KEY,
        algorithms=[ALGORITHM],
    )

    assert access_payload["sub"] == str(user_id)
    assert access_payload["type"] == "access"

    refresh_payload = jwt.decode(
        data["refresh_token"],
        SECRET_KEY,
        algorithms=[ALGORITHM],
    )

    assert refresh_payload["sub"] == str(user_id)
    assert refresh_payload["type"] == "refresh"



@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        "/auth/register",
        json={
            "email": "wrong-password@example.com",
            "password": "correct-password",
        },
    )

    response = await client.post(
        "/auth/login",
        json={
            "email": "wrong-password@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

@pytest.mark.asyncio
async def test_login_nonexistent_email(client):
    response = await client.post(
        "/auth/login",
        json={
            "email": "does-not-exist@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

@pytest.mark.asyncio
async def test_notes_requires_authentication(client):
    app.dependency_overrides.pop(get_current_user, None)

    response = await client.get("/notes")

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_notes_with_valid_token(client):
    await client.post(
        "/auth/register",
        json={
            "email": "authorized@example.com",
            "password": "password123",
        },
    )

    login_response = await client.post(
        "/auth/login",
        json={
            "email": "authorized@example.com",
            "password": "password123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = await client.get(
        "/notes",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

@pytest.mark.asyncio
async def test_notes_with_invalid_token(client):
    response = await client.get(
        "/notes",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"

@pytest.mark.asyncio
async def test_notes_with_expired_token(client):
    expired_payload = {
        "sub": "123",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }

    token = jwt.encode(
        expired_payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    response = await client.get(
        "/notes",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"

@pytest.mark.asyncio
async def test_notes_with_tampered_token(client):
    token = create_access_token(123)

    header, payload, signature = token.split(".")

    import base64
    import json

    payload_data = json.loads(
        base64.urlsafe_b64decode(
            payload + "=" * (-len(payload) % 4)
        )
    )

    payload_data["sub"] = "999"

    tampered_payload = base64.urlsafe_b64encode(
        json.dumps(payload_data, separators=(",", ":")).encode()
    ).decode().rstrip("=")

    tampered_token = f"{header}.{tampered_payload}.{signature}"

    response = await client.get(
        "/notes",
        headers={
            "Authorization": f"Bearer {tampered_token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"

@pytest.mark.asyncio
async def test_notes_with_token_for_nonexistent_user(client):
    token = create_access_token(999999)

    response = await client.get(
        "/notes",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"

@pytest.mark.asyncio
async def test_user_cannot_access_another_users_note(
    authenticated_client,
    db,
    test_user,
):
    # User 1 creates a note
    response = await authenticated_client.post(
        "/notes",
        json={
            "title": "User 1 note",
            "content": "Private content",
        },
    )

    assert response.status_code == 200

    note_id = response.json()["id"]

    # Create User 2
    other_user = User(
        email="other-user@example.com",
        password_hash="test_hash",
    )

    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)

    # Switch the authenticated user to User 2
    async def override_get_current_user():
        return other_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    # User 2 tries to access User 1's note
    response = await authenticated_client.get(f"/notes/{note_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Note not found"

@pytest.mark.asyncio
async def test_user_cannot_update_another_users_note(
    authenticated_client,
    db,
    test_user,
):
    # User 1 creates a note
    response = await authenticated_client.post(
        "/notes",
        json={
            "title": "User 1 note",
            "content": "Original content",
        },
    )

    assert response.status_code == 200

    note_id = response.json()["id"]

    # Create User 2
    other_user = User(
        email="update-other-user@example.com",
        password_hash="test_hash",
    )

    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)

    # Switch authentication to User 2
    async def override_get_current_user():
        return other_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    # User 2 tries to update User 1's note
    response = await authenticated_client.put(
        f"/notes/{note_id}",
        json={
            "title": "Hacked title",
            "content": "Hacked content",
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
    # User 1 creates a note
    response = await authenticated_client.post(
        "/notes",
        json={
            "title": "User 1 note",
            "content": "Private content",
        },
    )

    assert response.status_code == 200

    note_id = response.json()["id"]

    # Create User 2
    other_user = User(
        email="delete-other-user@example.com",
        password_hash="test_hash",
    )

    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)

    # Switch authentication to User 2
    async def override_get_current_user():
        return other_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    # User 2 tries to delete User 1's note
    response = await authenticated_client.delete(
        f"/notes/{note_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Note not found"

@pytest.mark.asyncio
async def test_refresh_token_returns_new_access_token(client):
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "password123",
        },
    )

    assert register_response.status_code == 200

    login_response = await client.post(
        "/auth/login",
        json={
            "email": "refresh@example.com",
            "password": "password123",
        },
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_access_token_cannot_be_used_as_refresh_token(client):
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "access-as-refresh@example.com",
            "password": "password123",
        },
    )

    assert register_response.status_code == 200

    login_response = await client.post(
        "/auth/login",
        json={
            "email": "access-as-refresh@example.com",
            "password": "password123",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": access_token,
        },
    )

    assert response.status_code == 401  

@pytest.mark.asyncio
async def test_invalid_refresh_token_is_rejected(client):
    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": "this-is-not-a-valid-jwt",
        },
    )

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_refresh_token_for_nonexistent_user_is_rejected(client):
    from app.auth.security import SECRET_KEY, ALGORITHM
    import jwt

    token = jwt.encode(
        {
            "sub": "999999",
            "type": "refresh",
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": token,
        },
    )

    assert response.status_code == 401
