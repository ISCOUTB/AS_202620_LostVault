from conftest import auth, make_token


def test_office_registers_and_delivers_an_object(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "oficina@utb.edu.co")
    monkeypatch.setenv("ADMIN_PASSWORD", "cuenta-de-pruebas")
    assert "Acceso del encargado" in client.get("/admin").text
    assert client.get("/v1/admin/objects").status_code == 401
    assert client.get("/v1/admin/objects", headers=auth()).status_code == 403
    assert client.post(
        "/v1/admin/objects", headers=auth(), json={"name": "No permitido"}
    ).status_code == 403
    assert client.post("/v1/admin/objects/1/deliver", headers=auth()).status_code == 403

    login = client.post(
        "/v1/admin/login",
        json={"email": "oficina@utb.edu.co", "password": "cuenta-de-pruebas"},
    )
    assert login.status_code == 200
    headers = auth(login.json()["accessToken"])
    created = client.post("/v1/admin/objects", headers=headers, json={"name": "Paraguas"})
    assert created.status_code == 201
    assert created.json()["status"] == "available"
    object_id = created.json()["id"]

    inventory = client.get("/v1/admin/objects", headers=headers)
    assert inventory.status_code == 200
    assert inventory.json()[0] == created.json()
    assert inventory.headers["cache-control"] == "no-store"

    path = f"/v1/admin/objects/{object_id}/deliver"
    assert client.post(path, headers=headers).status_code == 409
    claim_path = f"/v1/objects/{object_id}/claims"
    assert client.post(claim_path, headers=auth()).status_code == 201
    review_path = f"/v1/admin/objects/{object_id}/review"
    assert client.post(review_path, headers=headers, json={"decision": "reject"}).status_code == 422
    rejected = client.post(review_path, headers=headers, json={"decision": "reject", "reason": "No coincide"})
    assert rejected.json()["status"] == "available"
    assert client.post(claim_path, headers=auth()).status_code == 201
    assert client.post(review_path, headers=headers, json={"decision": "approve"}).json()["status"] == "approved"
    for _ in range(2):
        delivered = client.post(path, headers=headers)
        assert delivered.status_code == 200
        assert delivered.json()["status"] == "delivered"
    assert client.get("/v1/admin/objects", headers=headers).json()[0] == delivered.json()
    assert client.post(
        f"/v1/objects/{object_id}/claims", headers=auth(make_token(sub="other-student"))
    ).status_code == 409
    assert [e["action"] for e in delivered.json()["history"]] == [
        "registrado", "reclamado", "rechazado", "reclamado", "aprobado", "entregado"
    ]


def test_suspension_blocks_login_and_invalidates_existing_tokens(client, monkeypatch):
    for name, value in {
        "ADMIN_EMAIL": "oficina@utb.edu.co", "ADMIN_PASSWORD": "admin-test",
        "AUTH_USER_EMAIL": "demo@utb.edu.co", "AUTH_USER_PASSWORD": "student-test",
        "AUTH_USER_ID": "demo",
    }.items():
        monkeypatch.setenv(name, value)

    credentials = {"email": "demo@utb.edu.co", "password": "student-test"}
    student_login = lambda: client.post("/v1/auth/login", json=credentials)
    old_headers = auth(student_login().json()["accessToken"])
    grant = client.post("/v1/admin/login", json={"email": "oficina@utb.edu.co", "password": "admin-test"})
    admin_headers = auth(grant.json()["accessToken"])
    url = "/v1/admin/users/demo/suspension"
    assert client.post(url, headers=old_headers, json={"suspended": True}).status_code == 403
    assert client.get("/v1/admin/users", headers=admin_headers).json()[0]["suspended"] is False
    assert client.post(url, headers=admin_headers, json={"suspended": True}).json()["suspended"]
    assert student_login().status_code == 403
    assert client.post("/v1/objects", headers=old_headers, json={"name": "Test"}).status_code == 401
    assert not client.post(url, headers=admin_headers, json={"suspended": False}).json()["suspended"]
    assert client.post("/v1/objects", headers=old_headers, json={"name": "Test"}).status_code == 401
    fresh_headers = auth(student_login().json()["accessToken"])
    assert client.post("/v1/objects", headers=fresh_headers, json={"name": "Test"}).status_code == 201
