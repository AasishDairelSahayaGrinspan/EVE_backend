"""Webhook idempotency + edge cases: the most important suite."""
import uuid
from decimal import Decimal

from tests.conftest import auth_headers, make_booking, make_centre, make_offering, make_test, signup


def _setup(client):
    signup(client, "w@example.com")
    h = auth_headers(client, "w@example.com")
    c = make_centre(client, h)
    t = make_test(client, h)
    make_offering(client, h, c["id"], t["id"], "500.00")
    b = make_booking(client, h, c["id"], t["id"])
    return h, b


def _hook(client, **kw):
    return client.post("/payments/webhook/", json=kw)


def test_webhook_success_confirms(client):
    h, b = _setup(client)
    r = _hook(
        client,
        event_id="evt_1",
        event_type="payment.succeeded",
        payment_id="pay_ext_1",
        booking_id=b["id"],
        amount="500.00",
        status="SUCCESS",
    )
    assert r.status_code == 200 and r.json()["deduped"] is False
    assert client.get(f"/bookings/{b['id']}", headers=h).json()["status"] == "CONFIRMED"


def test_webhook_failed_marks_booking(client):
    _, b = _setup(client)
    r = _hook(
        client,
        event_id="evt_f1",
        event_type="payment.failed",
        payment_id="pay_ext_f1",
        booking_id=b["id"],
        amount="500.00",
        status="FAILED",
    )
    assert r.status_code == 200


def test_webhook_duplicate_event_idempotent(client):
    h, b = _setup(client)
    payload = dict(
        event_id="evt_dup",
        event_type="payment.succeeded",
        payment_id="pay_dup",
        booking_id=b["id"],
        amount="500.00",
        status="SUCCESS",
    )
    r1 = _hook(client, **payload)
    r2 = _hook(client, **payload)
    r3 = _hook(client, **payload)
    assert r1.json()["deduped"] is False
    assert r2.json()["deduped"] is True
    assert r3.json()["deduped"] is True
    # Exactly one payment row for that provider id
    from tests.conftest import TestingSession
    from app.models import Payment

    db = TestingSession()
    try:
        n = db.query(Payment).filter(Payment.provider_payment_id == "pay_dup").count()
    finally:
        db.close()
    assert n == 1


def test_webhook_invalid_payload(client):
    r = client.post("/payments/webhook/", json={"event_id": "x"})
    assert r.status_code == 422


def test_webhook_unknown_booking(client):
    r = _hook(
        client,
        event_id="evt_no_b",
        event_type="payment.succeeded",
        payment_id="pay_x",
        booking_id=str(uuid.uuid4()),
        amount="10.00",
        status="SUCCESS",
    )
    assert r.status_code == 404


def test_webhook_payment_belongs_to_other_booking(client):
    h, b = _setup(client)
    b2 = make_booking(client, h, b["centre_id"], b["test_id"])
    _hook(
        client,
        event_id="evt_a",
        event_type="payment.succeeded",
        payment_id="pay_shared",
        booking_id=b["id"],
        amount="500.00",
        status="SUCCESS",
    )
    r = _hook(
        client,
        event_id="evt_b",
        event_type="payment.succeeded",
        payment_id="pay_shared",
        booking_id=b2["id"],
        amount="500.00",
        status="SUCCESS",
    )
    assert r.status_code == 409


def test_webhook_after_cancel_does_not_resurrect(client):
    h, b = _setup(client)
    client.post(f"/bookings/{b['id']}/cancel", headers=h)
    r = _hook(
        client,
        event_id="evt_late",
        event_type="payment.succeeded",
        payment_id="pay_late",
        booking_id=b["id"],
        amount="500.00",
        status="SUCCESS",
    )
    assert r.status_code == 200
    assert client.get(f"/bookings/{b['id']}", headers=h).json()["status"] == "CANCELLED"
