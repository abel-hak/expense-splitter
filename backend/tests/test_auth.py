def test_register(client):
    res = client.post("/api/auth/register", json={
        "email": "new@example.com", "password": "pass1234", "name": "New User"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["name"] == "New User"


def test_register_duplicate(client):
    client.post("/api/auth/register", json={
        "email": "dup@example.com", "password": "pass1234"
    })
    res = client.post("/api/auth/register", json={
        "email": "dup@example.com", "password": "pass1234"
    })
    assert res.status_code == 400
    assert "already registered" in res.json()["detail"]


def test_login_success(client):
    client.post("/api/auth/register", json={
        "email": "login@example.com", "password": "pass1234"
    })
    res = client.post("/api/auth/login", json={
        "email": "login@example.com", "password": "pass1234"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "email": "wrong@example.com", "password": "pass1234"
    })
    res = client.post("/api/auth/login", json={
        "email": "wrong@example.com", "password": "wrongpass"
    })
    assert res.status_code == 401


def test_protected_route_no_token(client):
    res = client.get("/api/groups")
    assert res.status_code == 401
