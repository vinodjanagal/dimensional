from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

import app.main as main_module


@pytest.mark.asyncio
async def test_lifespan_closes_redis_and_disposes_engine(monkeypatch):
    pool = SimpleNamespace(close=AsyncMock())
    dispose = AsyncMock()
    create_pool = AsyncMock(return_value=pool)

    monkeypatch.setattr(main_module, "create_pool", create_pool)
    monkeypatch.setattr(main_module, "engine", SimpleNamespace(dispose=dispose))

    test_app = FastAPI()

    async with main_module.lifespan(test_app):
        assert test_app.state.arq_pool is pool

    create_pool.assert_awaited_once()
    pool.close.assert_awaited_once()
    dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_disposes_engine_if_redis_startup_fails(monkeypatch):
    dispose = AsyncMock()
    create_pool = AsyncMock(side_effect=RuntimeError("Redis unavailable"))

    monkeypatch.setattr(main_module, "create_pool", create_pool)
    monkeypatch.setattr(main_module, "engine", SimpleNamespace(dispose=dispose))

    test_app = FastAPI()

    with pytest.raises(RuntimeError, match="Redis unavailable"):
        async with main_module.lifespan(test_app):
            pass

    dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_disposes_engine_if_redis_close_fails(monkeypatch):
    pool = SimpleNamespace(
        close=AsyncMock(side_effect=RuntimeError("Redis close failed"))
    )
    dispose = AsyncMock()
    create_pool = AsyncMock(return_value=pool)

    monkeypatch.setattr(main_module, "create_pool", create_pool)
    monkeypatch.setattr(main_module, "engine", SimpleNamespace(dispose=dispose))

    test_app = FastAPI()

    with pytest.raises(RuntimeError, match="Redis close failed"):
        async with main_module.lifespan(test_app):
            pass

    pool.close.assert_awaited_once()
    dispose.assert_awaited_once()
