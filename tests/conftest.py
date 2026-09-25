"""Pytest setup: isolated Postgres test DB, TestClient with overridden get_db."""
import os
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-only")

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


def _test_engine():
    settings = get_settings()
    url = os.environ.get("TEST_DATABASE_URL", settings.TEST_DATABASE_URL)
    try:
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as c:
            c.execute(text("select 1"))
        return eng, False
    except Exception:
        # Fallback so `pytest` works without a running Postgres.
        path = "/tmp/eve_test_fallback.db"
        if os.path.exists(path):
            os.remove(path)
        return create_engine(f"sqlite:///{path}"), True


_engine, _is_sqlite = _test_engine()
TestingSession = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def _reset_db() -> None:
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    _reset_db()

    def _override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def signup(client: TestClient, email: str | None = None) -> dict:
    email = email or f"u_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/signup", json={"name": "Test User", "email": email, "password": "password-123"})
    assert r.status_code == 201, r.text
    return r.json()


def auth_headers(client: TestClient, email: str, password: str = "password-123") -> dict:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_centre(client: TestClient, h: dict, name: str = "CityCare") -> dict:
    r = client.post("/centres", json={"name": name, "location": "Bengaluru"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def make_test(client: TestClient, h: dict, name: str = "Lipid") -> dict:
    r = client.post("/tests", json={"name": name, "description": "panel"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def make_offering(client: TestClient, h: dict, centre_id: str, test_id: str, price: str = "499.00") -> dict:
    r = client.post(
        "/offerings",
        json={"centre_id": centre_id, "test_id": test_id, "price": price, "is_available": True},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


def make_booking(client: TestClient, h: dict, centre_id: str, test_id: str) -> dict:
    r = client.post(
        "/bookings",
        json={"centre_id": centre_id, "test_id": test_id, "appointment_at": "2030-05-01T10:00:00Z"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()
