import pytest


@pytest.fixture
def group_id(client, auth_headers):
    res = client.post("/api/groups", json={"name": "Test Group", "member_ids": []}, headers=auth_headers)
    return res.json()["id"]


@pytest.fixture
def payer_id(client, auth_headers):
    res = client.post("/api/auth/login", json={"email": "test@example.com", "password": "testpass123"})
    return res.json()["user"]["id"]


def test_create_expense(client, auth_headers, group_id, payer_id):
    res = client.post("/api/expenses", json={
        "group_id": group_id, "payer_id": payer_id, "amount": 50.0,
        "description": "Lunch", "participant_ids": [payer_id], "category": "food"
    }, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["amount"] == 50.0
    assert data["category"] == "food"
    assert data["split_type"] == "equal"


def test_list_expenses(client, auth_headers, group_id, payer_id):
    for i in range(3):
        client.post("/api/expenses", json={
            "group_id": group_id, "payer_id": payer_id, "amount": 10.0 * (i + 1),
            "description": f"Expense {i}", "participant_ids": [payer_id]
        }, headers=auth_headers)
    res = client.get(f"/api/expenses?group_id={group_id}", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_search_expenses(client, auth_headers, group_id, payer_id):
    client.post("/api/expenses", json={
        "group_id": group_id, "payer_id": payer_id, "amount": 20.0,
        "description": "Coffee", "participant_ids": [payer_id]
    }, headers=auth_headers)
    client.post("/api/expenses", json={
        "group_id": group_id, "payer_id": payer_id, "amount": 30.0,
        "description": "Pizza", "participant_ids": [payer_id]
    }, headers=auth_headers)
    res = client.get(f"/api/expenses?group_id={group_id}&search=coffee", headers=auth_headers)
    assert len(res.json()) == 1
    assert res.json()[0]["description"] == "Coffee"


def test_filter_by_category(client, auth_headers, group_id, payer_id):
    client.post("/api/expenses", json={
        "group_id": group_id, "payer_id": payer_id, "amount": 20.0,
        "description": "Bus", "participant_ids": [payer_id], "category": "transport"
    }, headers=auth_headers)
    client.post("/api/expenses", json={
        "group_id": group_id, "payer_id": payer_id, "amount": 30.0,
        "description": "Dinner", "participant_ids": [payer_id], "category": "food"
    }, headers=auth_headers)
    res = client.get(f"/api/expenses?group_id={group_id}&category=food", headers=auth_headers)
    assert len(res.json()) == 1


def test_update_expense(client, auth_headers, group_id, payer_id):
    res = client.post("/api/expenses", json={
        "group_id": group_id, "payer_id": payer_id, "amount": 25.0,
        "description": "Old", "participant_ids": [payer_id]
    }, headers=auth_headers)
    eid = res.json()["id"]
    res = client.patch(f"/api/expenses/{eid}", json={
        "amount": 30.0, "description": "Updated", "category": "food"
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["amount"] == 30.0
    assert res.json()["description"] == "Updated"
    assert res.json()["category"] == "food"


def test_delete_expense(client, auth_headers, group_id, payer_id):
    res = client.post("/api/expenses", json={
        "group_id": group_id, "payer_id": payer_id, "amount": 10.0,
        "description": "Del", "participant_ids": [payer_id]
    }, headers=auth_headers)
    eid = res.json()["id"]
    res = client.delete(f"/api/expenses/{eid}", headers=auth_headers)
    assert res.status_code == 204


def test_export_csv(client, auth_headers, group_id, payer_id):
    client.post("/api/expenses", json={
        "group_id": group_id, "payer_id": payer_id, "amount": 50.0,
        "description": "Dinner", "participant_ids": [payer_id], "category": "food"
    }, headers=auth_headers)
    res = client.get(f"/api/expenses/export?group_id={group_id}", headers=auth_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Dinner" in res.text
