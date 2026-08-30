import asyncio
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from domains.auth.dependencies import get_optional_user_id
from utils.rate_limit import rate_limit, reset_rate_limits  # type: ignore

TEST_PORT = 1234
TEST_IP = "1.2.3.4"
OTHER_IP = "5.6.7.8"
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
OTHER_USER_ID = UUID("87654321-4321-8765-4321-876543210987")


def build_app(limit: int = 2, window_seconds: int = 60, buckets: list[str] | None = None):
    app = FastAPI()

    for bucket in buckets or ["test"]:

        @app.get(f"/{bucket}/public", dependencies=[Depends(rate_limit(bucket, limit, window_seconds, public=True))])
        async def limited():
            return {"ok": True}

        @app.get(f"/{bucket}/private", dependencies=[Depends(rate_limit(bucket, limit, window_seconds))])
        async def private_limited():
            return {"ok": True}

    return app


def build_client(app: FastAPI, ip: str = TEST_IP):
    return TestClient(app, client=(ip, TEST_PORT))


def set_user_id(app: FastAPI, user_id: UUID | None = None):
    app.dependency_overrides[get_optional_user_id] = lambda: user_id


@pytest.fixture(autouse=True)
def clear_limits():
    reset_rate_limits()


def test_rate_limit_allows_under_limit():
    app = build_app()
    client = build_client(app)

    assert client.get("/test/public").status_code == 200
    assert client.get("/test/public").status_code == 200


def test_rate_limit_blocks_when_exceeded():
    app = build_app()
    client = TestClient(app)

    assert client.get("/test/public").status_code == 200
    assert client.get("/test/public").status_code == 200
    assert client.get("/test/public").status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_resets_after_window():
    # Use shorter window for the test
    app = build_app(limit=1, window_seconds=0)
    client = build_client(app)

    assert client.get("/test/public").status_code == 200
    await asyncio.sleep(0.05)
    assert client.get("/test/public").status_code == 200


def test_rate_limit_resets_after_clear():
    app = build_app(limit=1)
    client = build_client(app)

    assert client.get("/test/public").status_code == 200
    assert client.get("/test/public").status_code == 429

    reset_rate_limits()

    assert client.get("/test/public").status_code == 200


def test_rate_limit_resets_multiple_buckets():
    app = build_app(limit=1, buckets=["one", "two"])
    client = build_client(app)

    assert client.get("/one/public").status_code == 200
    assert client.get("/two/public").status_code == 200

    reset_rate_limits("one")

    assert client.get("/one/public").status_code == 200
    assert client.get("/two/public").status_code == 429


def test_private_api_rate_limit_same_user_multiple_ips():
    app = build_app(limit=1)
    client1 = build_client(app, TEST_IP)
    client2 = build_client(app, OTHER_IP)

    set_user_id(app, TEST_USER_ID)
    assert client1.get("/test/private").status_code == 200
    assert client2.get("/test/private").status_code == 429


def test_private_api_rate_limit_same_ip_multiple_users():
    app = build_app(limit=1)
    client = build_client(app, TEST_IP)

    set_user_id(app, TEST_USER_ID)
    assert client.get("/test/private").status_code == 200
    set_user_id(app, OTHER_USER_ID)
    assert client.get("/test/private").status_code == 200


def test_private_api_rate_limit_mix_auth_unauth():
    app = build_app(limit=1)
    client = build_client(app, TEST_IP)

    set_user_id(app, None)
    assert client.get("/test/private").status_code == 200
    assert client.get("/test/private").status_code == 429

    set_user_id(app, TEST_USER_ID)
    assert client.get("/test/private").status_code == 200
    assert client.get("/test/private").status_code == 429
