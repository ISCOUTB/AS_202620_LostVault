from conftest import auth


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
    for _ in range(2):
        delivered = client.post(path, headers=headers)
        assert delivered.status_code == 200
        assert delivered.json()["status"] == "delivered"
    assert client.get("/v1/admin/objects", headers=headers).json()[0] == delivered.json()
    assert client.post(
        f"/v1/objects/{object_id}/claims", headers=auth()
    ).status_code == 409
