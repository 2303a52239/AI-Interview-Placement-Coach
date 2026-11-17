import uuid


def _register(client, role_email=None):
    email = role_email or f"u{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"name": "T", "email": email, "password": "StrongPass1"})
    assert r.status_code == 201
    return r.json()


def test_register_returns_access_and_refresh(client):
    data = _register(client)
    assert data["access_token"] and data["refresh_token"] and data["user"]["role"] == "student"


def test_password_minimum_length_is_8(client):
    r = client.post("/auth/register", json={"name": "T", "email": "short@example.com", "password": "abc123"})
    assert r.status_code == 422


def test_refresh_rotates_token_and_old_one_is_rejected(client):
    data = _register(client)
    r1 = client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r1.status_code == 200 and r1.json()["refresh_token"] != data["refresh_token"]
    replay = client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert replay.status_code == 401
    # reuse detection revoked the whole family, including the newly issued token
    again = client.post("/auth/refresh", json={"refresh_token": r1.json()["refresh_token"]})
    assert again.status_code == 401


def test_access_token_cannot_be_used_as_refresh_and_vice_versa(client):
    data = _register(client)
    assert client.post("/auth/refresh", json={"refresh_token": data["access_token"]}).status_code == 401
    me = client.get("/users/me", headers={"Authorization": f"Bearer {data['refresh_token']}"})
    assert me.status_code == 401


def test_logout_revokes_refresh_token(client):
    data = _register(client)
    h = {"Authorization": f"Bearer {data['access_token']}"}
    assert client.post("/auth/logout", headers=h, json={"refresh_token": data["refresh_token"]}).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": data["refresh_token"]}).status_code == 401


def test_student_cannot_reach_admin_endpoints(client):
    data = _register(client)
    h = {"Authorization": f"Bearer {data['access_token']}"}
    assert client.get("/admin/candidates", headers=h).status_code == 403


def test_rate_limiter_returns_429(client, monkeypatch):
    from app.config import settings
    from app.utils import rate_limit
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 3)
    rate_limit._reset_for_tests() if hasattr(rate_limit, "_reset_for_tests") else None
    codes = [client.post("/auth/login", json={"email": "x@example.com", "password": "nope-nope"}).status_code for _ in range(6)]
    assert 429 in codes


def test_429_response_carries_cors_headers(client, monkeypatch):
    """A rate-limited response must still be readable by the browser (CORS headers present)."""
    from app.config import settings
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 1)
    origin = settings.cors_origins_list[0]
    last = None
    for _ in range(3):
        last = client.post("/auth/login", json={"email": "x@y.com", "password": "nopenope1"}, headers={"Origin": origin})
    assert last.status_code == 429
    assert last.headers.get("access-control-allow-origin") == origin
