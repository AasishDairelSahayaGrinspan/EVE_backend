"""Authorization: users cannot touch each other's bookings/payments."""
import uuid

from tests.conftest import auth_headers, make_booking, make_centre, make_offering, make_test, signup


def test_cross_user_booking_forbidden(client):
    signup(client, "a1@example.com")
    ha = auth_headers(client, "a1@example.com")
    c = make_centre(client, ha)
    t = make_test(client, ha)
    make_offering(client, ha, c["id"], t["id"])
    b = make_booking(client, ha, c["id"], t["id"])

    signup(client, "b1@example.com")
    hb = auth_headers(client, "b1@example.com")
    assert client.get(f"/bookings/{b['id']}", headers=hb).status_code == 403
    assert client.post(f"/bookings/{b['id']}/cancel", headers=hb).status_code == 403
    assert (
        client.post("/payments/", json={"booking_id": b["id"]}, headers=hb).status_code == 403
    )
    # Unknown booking -> 404, not leak
    assert client.get(f"/bookings/{uuid.uuid4()}", headers=hb).status_code == 404
