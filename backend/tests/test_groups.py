def test_create_group(client, auth_headers):
    res = client.post("/api/groups", json={
        "name": "Trip", "description": "Weekend trip", "member_ids": []
    }, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Trip"
    assert len(data["member_ids"]) == 1  # creator auto-added


def test_list_groups(client, auth_headers):
    client.post("/api/groups", json={"name": "G1", "member_ids": []}, headers=auth_headers)
    client.post("/api/groups", json={"name": "G2", "member_ids": []}, headers=auth_headers)
    res = client.get("/api/groups", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_update_group(client, auth_headers):
    res = client.post("/api/groups", json={"name": "Old", "member_ids": []}, headers=auth_headers)
    gid = res.json()["id"]
    res = client.patch(f"/api/groups/{gid}", json={"name": "New"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "New"


def test_delete_group(client, auth_headers):
    res = client.post("/api/groups", json={"name": "Del", "member_ids": []}, headers=auth_headers)
    gid = res.json()["id"]
    res = client.delete(f"/api/groups/{gid}", headers=auth_headers)
    assert res.status_code == 204
    res = client.get("/api/groups", headers=auth_headers)
    assert len(res.json()) == 0


def test_add_member_by_email(client, auth_headers, second_user):
    res = client.post("/api/groups", json={"name": "G", "member_ids": []}, headers=auth_headers)
    gid = res.json()["id"]
    res = client.post(f"/api/groups/{gid}/members", json={"email": "user2@example.com"}, headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["member_ids"]) == 2


def test_remove_member(client, auth_headers, second_user):
    res = client.post("/api/groups", json={"name": "G", "member_ids": []}, headers=auth_headers)
    gid = res.json()["id"]
    client.post(f"/api/groups/{gid}/members", json={"email": "user2@example.com"}, headers=auth_headers)
    res = client.delete(f"/api/groups/{gid}/members/{second_user['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["member_ids"]) == 1
