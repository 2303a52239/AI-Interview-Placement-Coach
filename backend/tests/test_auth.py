def test_register_creates_user_and_returns_token(client):
    resp = client.post("/auth/register", json={
        "name": "Alice", "email": "alice@example.com", "password": "SecurePass1",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["email"] == "alice@example.com"
    assert data["access_token"]


def test_register_duplicate_email_fails(client):
    client.post("/auth/register", json={"name": "Bob", "email": "bob@example.com", "password": "Password1"})
    resp = client.post("/auth/register", json={"name": "Bob2", "email": "bob@example.com", "password": "Password2"})
    assert resp.status_code == 400


def test_login_success(client):
    client.post("/auth/register", json={"name": "Carl", "email": "carl@example.com", "password": "MyPassword1"})
    resp = client.post("/auth/login", json={"email": "carl@example.com", "password": "MyPassword1"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_invalid_password_fails(client):
    client.post("/auth/register", json={"name": "Dana", "email": "dana@example.com", "password": "RightPass1"})
    resp = client.post("/auth/login", json={"email": "dana@example.com", "password": "WrongPass1"})
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_protected_route_with_valid_token(client, auth_headers, registered_user):
    resp = client.get("/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == registered_user["user"]["email"]
