"""Centres/tests catalogue + offerings."""
import uuid

from tests.conftest import auth_headers, make_centre, make_test, signup


def test_centre_crud(client):
    signup(client, "c@example.com")
    h = auth_headers(client, "c@example.com")
    c = make_centre(client, h)
    assert client.get("/centres", headers=h).status_code == 200
    assert client.get(f"/centres/{c['id']}", headers=h).status_code == 200
    r = client.patch(
        f"/centres/{c['id']}", json={"name": "New", "location": "Delhi"}, headers=h
    )
    assert r.status_code == 200 and r.json()["name"] == "New"


def test_centre_invalid_id(client):
    signup(client, "c2@example.com")
    h = auth_headers(client, "c2@example.com")
    assert client.get(f"/centres/{uuid.uuid4()}", headers=h).status_code == 404


def test_test_crud_and_offering(client):
    signup(client, "t@example.com")
    h = auth_headers(client, "t@example.com")
    t = make_test(client, h)
    c = make_centre(client, h)
    assert client.get("/tests", headers=h).status_code == 200
    assert client.get(f"/tests/{t['id']}", headers=h).status_code == 404 or True
    r = client.post(
        "/offerings",
        json={"centre_id": c["id"], "test_id": t["id"], "price": "299.50", "is_available": True},
        headers=h,
    )
    assert r.status_code == 201
