from fastapi.testclient import TestClient

from app.main import app 


def test_root_identifies_service():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200 
    assert response.json() == {"service": "dimensional", "status": "ok"}

def test_liveness_is_dependency_free():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

def test_request_id_header_present():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.headers.get("X-Request-ID")

    