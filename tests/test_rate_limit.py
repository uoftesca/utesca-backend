import asyncio

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from utils.rate_limit import rate_limit, reset_rate_limits  # type: ignore


def build_app():
    app = FastAPI()

    @app.get("/limited", dependencies=[Depends(rate_limit("test_bucket", limit=2, window_seconds=60))])
    async def limited():
        return {"ok": True}

    return app


@pytest.fixture(autouse=True)
def clear_limits():
    reset_rate_limits()


def test_rate_limit_allows_under_limit():
    app = build_app()
    client = TestClient(app)
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200


def test_rate_limit_blocks_when_exceeded(monkeypatch):
    app = build_app()
    client = TestClient(app)
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200
    resp = client.get("/limited")
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_resets_after_window(monkeypatch):
    # Use shorter window for the test
    app = FastAPI()

    @app.get("/short", dependencies=[Depends(rate_limit("short_bucket", limit=1, window_seconds=0))])
    async def short():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/short").status_code == 200
    await asyncio.sleep(0.05)
    assert client.get("/short").status_code == 200
