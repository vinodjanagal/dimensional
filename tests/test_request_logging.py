import json
import logging
import uuid

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.logging import configure_logging, request_id_var


@pytest.fixture
def logging_app():
    """Create an isolated app using the production request middleware."""
    from app.main import log_requests

    test_app = FastAPI()
    test_app.middleware("http")(log_requests)

    @test_app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @test_app.get("/expected-error")
    async def expected_error():
        raise HTTPException(
            status_code=400,
            detail="Expected test error",
        )

    @test_app.get("/unexpected-error")
    async def unexpected_error():
        raise RuntimeError("Deliberate test failure")

    return test_app


@pytest.mark.asyncio
async def test_request_logging_adds_request_id_and_logs_completion(
    logging_app, monkeypatch
):
    import app.main as main_module

    log_events = []
    original_info = main_module.logger.info

    def capture_info(message, *args, **kwargs):
        log_events.append(
            {
                "message": message,
                "extra": kwargs.get("extra", {}).copy(),
                "request_id": request_id_var.get(),
            }
        )
        return original_info(message, *args, **kwargs)

    monkeypatch.setattr(main_module.logger, "info", capture_info)
    configure_logging("INFO")

    transport = ASGITransport(app=logging_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/ok")

    assert response.status_code == 200

    request_id = response.headers["X-Request-ID"]
    uuid.UUID(request_id)

    started = next(
        event for event in log_events
        if event["message"] == "http.request.started"
    )
    completed = next(
        event for event in log_events
        if event["message"] == "http.request.completed"
    )

    assert started["request_id"] == request_id
    assert completed["request_id"] == request_id
    assert completed["extra"]["status_code"] == 200
    assert completed["extra"]["duration_ms"] >= 0
    assert request_id_var.get() is None


@pytest.mark.asyncio
async def test_request_logging_preserves_expected_http_error(logging_app):
    configure_logging("INFO")

    transport = ASGITransport(app=logging_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/expected-error")

    assert response.status_code == 400
    assert response.json()["detail"] == "Expected test error"


@pytest.mark.asyncio
async def test_unexpected_error_is_logged_and_returns_500(
    logging_app, monkeypatch
):
    import app.main as main_module

    captured = []
    original_exception = main_module.logger.exception

    def capture_exception(message, *args, **kwargs):
        captured.append(
            {
                "message": message,
                "extra": kwargs.get("extra", {}).copy(),
                "request_id": request_id_var.get(),
            }
        )
        return original_exception(message, *args, **kwargs)

    monkeypatch.setattr(
        main_module.logger,
        "exception",
        capture_exception,
    )

    configure_logging("INFO")

    transport = ASGITransport(
        app=logging_app,
        raise_app_exceptions=False,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/unexpected-error")

    assert response.status_code == 500

    failure = next(
        event for event in captured
        if event["message"] == "http.request.failed"
    )

    assert failure["extra"]["event"] == "http.request.failed"
    assert failure["extra"]["method"] == "GET"
    assert failure["extra"]["path"] == "/unexpected-error"
    assert failure["extra"]["duration_ms"] >= 0
    assert failure["request_id"] is not None
    assert request_id_var.get() is None