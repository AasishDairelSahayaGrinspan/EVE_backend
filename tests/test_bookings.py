"""Bookings: happy path, validation, price snapshot, state machine, authz."""
import uuid
from decimal import Decimal

from tests.conftest import (
    auth_headers,
    make_booking,
    make_centre,
    make_offering,
    make_test,
    signup,
)


def _setup(client):
    signup(client, "b@example.com")
    h = auth_headers(client, "b@example.com")
    c = make_centre(client, h)
    t = make_test(client, h)
    make_offering(client, h, c["id"], t["id"], "499.00")
    return h, c, t


def test_create_valid_booking_snapshots_price(client):
    h, c, t = _setup(client)
    b = make_booking(client, h, c["id"], t["id"])
    assert b["status"] == "PENDING"
    assert Decimal(b["amount"]) == Decimal("499.00")


def test_booking_unauthenticated(client):
    assert client.post("/bookings", json={}).status_code in {401, 403, 422}


def test_booking_nonexistent_centre_or_test(client):
    h, c, t = _setup(client)
    r = client.post(
        "/bookings",
        json={"centre_id": str(uuid.uuid4()), "test_id": t["id"], "appointment_at": "2030-01-01T10:00:00Z"},
        headers=h,
    )
    assert r.status_code == 404
    r = client.post(
        "/bookings",
        json={"centre_id": c["id"], "test_id": str(uuid.uuid4()), "appointment_at": "2030-01-01T10:00:00Z"},
        headers=h,
    )
    assert r.status_code == 404


def test_booking_test_not_offered(client):
    signup(client, "n@example.com")
    h = auth_headers(client, "n@example.com")
    c = make_centre(client, h, "C1")
    t = make_test(client, h, "T-orphan")
    r = client.post(
        "/bookings",
        json={"centre_id": c["id"], "test_id": t["id"], "appointment_at": "2030-01-01T10:00:00Z"},
        headers=h,
    )
    assert r.status_code == 400


def test_booking_past_appointment_rejected(client):
    h, c, t = _setup(client)
    r = client.post(
        "/bookings",
        json={"centre_id": c["id"], "test_id": t["id"], "appointment_at": "2020-01-01T10:00:00Z"},
        headers=h,
    )
    assert r.status_code == 400


def test_price_snapshot_survives_offering_change(client):
    h, c, t = _setup(client)
    b = make_booking(client, h, c["id"], t["id"])
    make_offering(client, h, c["id"], t["id"], "999.00")  # price hike
    r = client.get(f"/bookings/{b['id']}", headers=h)
    assert Decimal(r.json()["amount"]) == Decimal("499.00")


def test_cancel_and_invalid_transition(client):
    h, c, t = _setup(client)
    b = make_booking(client, h, c["id"], t["id"])
    r = client.post(f"/bookings/{b['id']}/cancel", headers=h)
    assert r.json()["status"] == "CANCELLED"
    r2 = client.post(f"/bookings/{b['id']}/cancel", headers=h)
    assert r2.status_code == 409  # terminal state
