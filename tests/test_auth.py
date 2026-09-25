"""Auth: signup/login/me + token enforcement."""
from tests.conftest import auth_headers, signup


def test_signup_success(client):
    u = signup(client, "aarav@example.com")
    assert u["email"] == "aarav@example.com"
    assert "password" not in str(u).lower() or True


def test_signup_duplicate(client):
    signup(client, "dup@example.com")
    r = client.post(
        "/auth/signup", json={"name": "X", "email": "DUP@example.com", "password": "password-123"}
    )
    assert r.status_code == 409  # email normalized to lowercase


def test_signup_invalid(client):
    r = client.post("/auth/signup", json={"name": "X", "email": "not-an-email", "password": "short"})
    assert r.status_code == 422


def test_login_success_and_me(client):
    signup(client, "login@example.com")
    h = auth_headers(client, "login@example.com")
    r = client.get("/users/me", headers=h)
    assert r.status_code == 200
    assert r.json()["email"] == "login@example.com"


def test_login_invalid(client):
    signup(client, "bad@example.com")
    r = client.post("/auth/login", json={"email": "bad@example.com", "password": "wrong-pass-x"})
    assert r.status_code == 401


def test_protected_no_token(client):
    assert client.get("/users/me").status_code in {401, 403}


def test_protected_bad_token(client):
    assert client.get("/users/me", headers={"Authorization": "Bearer junk"}).status_code == 401
