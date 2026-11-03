"""Pruebas de login, creación y borrado de objetos."""

import pytest

from tests.conftest import auth, make_token

EMAIL = "estudiante@utb.edu.co"
PASSWORD = "clave-de-pruebas-123"


@pytest.fixture(autouse=True)
def single_user_env(monkeypatch):
    monkeypatch.setenv("AUTH_USER_EMAIL", EMAIL)
    monkeypatch.setenv("AUTH_USER_PASSWORD", PASSWORD)
    monkeypatch.setenv("AUTH_USER_ID", "student-42")


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/v1/auth/login", json={"email": email, "password": password})


# --- login -------------------------------------------------------------

def test_login_ok_returns_usable_token(client):
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["tokenType"] == "bearer" and body["expiresIn"] > 0
    # el token sirve para reclamar (el correo es institucional)
    claim = client.post("/v1/objects/1/claims", headers=auth(body["accessToken"]))
    assert claim.status_code == 201
    assert claim.json()["userId"] == "student-42"


def test_login_email_is_case_insensitive(client):
    assert login(client, email=EMAIL.upper()).status_code == 200


@pytest.mark.parametrize(
    "email,password",
    [(EMAIL, "mala"), ("otro@utb.edu.co", PASSWORD), ("estudiante@gmail.com", PASSWORD), ("sin-arroba", PASSWORD)],
)
def test_login_wrong_credentials_is_401(client, email, password):
    r = login(client, email, password)
    assert r.status_code == 401
    assert r.json()["code"] == "INVALID_CREDENTIALS"


def test_login_invalid_body_is_422(client):
    r = client.post("/v1/auth/login", json={"email": EMAIL})
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_login_not_configured_is_503(client, monkeypatch):
    monkeypatch.delenv("AUTH_USER_EMAIL")
    r = login(client)
    assert r.status_code == 503
    assert r.json()["code"] == "AUTH_NOT_CONFIGURED"


# --- crear -------------------------------------------------------------

def test_create_object_requires_auth(client):
    r = client.post("/v1/objects", json={"name": "Llaves"})
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"


def test_create_object_ok_and_claimable(client):
    r = client.post(
        "/v1/objects", json={"name": "  Llaves  ", "description": "Con llavero rojo"}, headers=auth()
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Llaves"
    assert body["description"] == "Con llavero rojo"
    assert body["reportedBy"] == "student-42"
    assert body["claimedBy"] is None and body["id"]
    other = auth(make_token(sub="student-7", email="otro@utb.edu.co"))
    assert client.post(f"/v1/objects/{body['id']}/claims", headers=other).status_code == 201


@pytest.mark.parametrize("payload", [{}, {"name": ""}, {"name": "   "}, {"name": "x", "extra": 1}])
def test_create_object_invalid_is_422(client, payload):
    r = client.post("/v1/objects", json=payload, headers=auth())
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"


# --- borrar ------------------------------------------------------------

def _create(client, headers=None):
    return client.post("/v1/objects", json={"name": "Termo"}, headers=headers or auth()).json()["id"]


def test_delete_object_requires_auth(client):
    assert client.delete("/v1/objects/1").status_code == 401


def test_delete_own_object(client):
    oid = _create(client)
    r = client.delete(f"/v1/objects/{oid}", headers=auth())
    assert r.status_code == 204 and r.content == b""
    assert client.delete(f"/v1/objects/{oid}", headers=auth()).status_code == 404


def test_delete_missing_is_404(client):
    r = client.delete("/v1/objects/nope", headers=auth())
    assert r.status_code == 404 and r.json()["code"] == "OBJECT_NOT_FOUND"


def test_delete_object_of_another_user_is_403(client):
    oid = _create(client)
    other = auth(make_token(sub="student-7", email="otro@utb.edu.co"))
    r = client.delete(f"/v1/objects/{oid}", headers=other)
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"


def test_delete_object_without_owner_is_403(client):
    # los objetos sembrados no tienen dueño: nadie puede borrarlos por la API
    assert client.delete("/v1/objects/1", headers=auth()).status_code == 403


def test_delete_claimed_object_is_409(client):
    oid = _create(client)
    other = auth(make_token(sub="student-7", email="otro@utb.edu.co"))
    client.post(f"/v1/objects/{oid}/claims", headers=other)
    r = client.delete(f"/v1/objects/{oid}", headers=auth())
    assert r.status_code == 409 and r.json()["code"] == "OBJECT_ALREADY_CLAIMED"
