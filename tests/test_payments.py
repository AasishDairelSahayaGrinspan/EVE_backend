"""Simulated payments: deterministic SUCCESS/FAILED, guards."""
import uuid

from tests.conftest import auth_headers, make_booking, make_centre, make_offering, make_test, signup


def _setup(client):
    signup(client, "p@example.com")
    h = auth_headers(client, "p@example.com")
    c = make_centre(client, h)
    t = make_test(client, h)
    make_offering(client, h, c["id"], t["id"], "250.00")
    return h, c, t


def test_payment_success_confirms(client):
    h, c, t = _setup(client)
    b = make_booking(client, h, c["id"], t["id"])
    r = client.post("/payments/", json={"booking_id": b["id"], "simulate_outcome": "SUCCESS"}, headers=h)
    assert r.status_code == 201
    assert r.json()["status"] == "SUCCESS"
    assert client.get(f"/bookings/{b['id']}", headers=h).json()["status"] == "CONFIRMED"


def test_payment_failed_marks_booking(client):
    h, c, t = _setup(client)
    b = make_booking(client, h, c["id"], t["id"])
    r = client.post("/payments/", json={"booking_id": b["id"], "simulate_outcome": "FAILED"}, headers=h)
    assert r.json()["status"] == "FAILED"
    assert client.get(f"/bookings/{b['id']}", headers=h).json()["status"] == "FAILED"


def test_payment_nonexistent_booking(client):
    _setup(client)
    h = auth_headers(client, "p@example.com")
    r = client.post("/payments/", json={"booking_id": str(uuid.uuid4())}, headers=h)
    assert r.status_code == 404


def test_duplicate_payment_rejected(client):
    h, c, t = _setup(client)
    b = make_booking(client, h, c["id"], t["id"])
    client.post("/payments/", json={"booking_id": b["id"], "simulate_outcome": "SUCCESS"}, headers=h)
    r = client.post("/payments/", json={"booking_id": b["id"], "simulate_outcome": "SUCCESS"}, headers=h)
    assert r.status_code == 409
