import pytest


@pytest.fixture
def setup_group(client, auth_headers, second_user):
    res = client.post("/api/groups", json={"name": "Test", "member_ids": []}, headers=auth_headers)
    gid = res.json()["id"]
    client.post(f"/api/groups/{gid}/members", json={"email": "user2@example.com"}, headers=auth_headers)
    login = client.post("/api/auth/login", json={"email": "test@example.com", "password": "testpass123"})
    uid1 = login.json()["user"]["id"]
    return gid, uid1, second_user["id"]


def test_settlements_balanced(client, auth_headers, setup_group):
    gid, uid1, uid2 = setup_group
    client.post("/api/expenses", json={
        "group_id": gid, "payer_id": uid1, "amount": 100.0,
        "description": "Dinner", "participant_ids": [uid1, uid2]
    }, headers=auth_headers)
    res = client.get(f"/api/settlements/group/{gid}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["settlements"]) == 1
    assert data["settlements"][0]["amount"] == 50.0


def test_record_payment(client, auth_headers, setup_group):
    gid, uid1, uid2 = setup_group
    client.post("/api/expenses", json={
        "group_id": gid, "payer_id": uid1, "amount": 100.0,
        "description": "Dinner", "participant_ids": [uid1, uid2]
    }, headers=auth_headers)
    res = client.post("/api/settlements/pay", json={
        "group_id": gid, "to_user_id": uid1, "amount": 50.0
    }, headers=auth_headers)
    assert res.status_code == 200

    res = client.get(f"/api/settlements/payments/{gid}", headers=auth_headers)
    payments = res.json()
    assert len(payments) == 1
    assert payments[0]["amount"] == 50.0


def test_dashboard(client, auth_headers, setup_group):
    gid, uid1, uid2 = setup_group
    client.post("/api/expenses", json={
        "group_id": gid, "payer_id": uid1, "amount": 60.0,
        "description": "Lunch", "participant_ids": [uid1, uid2], "category": "food"
    }, headers=auth_headers)
    client.post("/api/expenses", json={
        "group_id": gid, "payer_id": uid1, "amount": 40.0,
        "description": "Taxi", "participant_ids": [uid1, uid2], "category": "transport"
    }, headers=auth_headers)
    res = client.get(f"/api/settlements/dashboard/{gid}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_expenses"] == 100.0
    assert data["expense_count"] == 2
    assert data["category_totals"]["food"] == 60.0
    assert data["category_totals"]["transport"] == 40.0
