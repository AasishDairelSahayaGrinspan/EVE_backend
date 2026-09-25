"""Edge cases: malformed input, bad UUIDs, wrong methods, request-id header."""
import uuid

from tests.conftest import auth_headers, signup


def test_malformed_json_and_types(client):
    signup(client, "e@example.com")
    h = auth_headers(client, "e@example.com")
    r = client.post(
        "/bookings",
        json={"centre_id": "not-a-uuid", "test_id": "x", "appointment_at": "garbage"},
        headers=h,
    )
    assert r.status_code == 422


def test_request_id_header_present(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers


def test_health_ok(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_unknown_centre_uuid_shape_ok_but_404(client):
    signup(client, "e2@example.com")
    h = auth_headers(client, "e2@example.com")
    assert client.get(f"/centres/{uuid.uuid4()}", headers=h).status_code == 404
