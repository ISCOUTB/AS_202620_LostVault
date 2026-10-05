import json
import logging
import os
from pathlib import Path

import jwt
import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

import main

CONTRACT = (
    Path(__file__).resolve().parents[1] / "docs" / "contracts" / "lostvault-api.yaml"
)


@pytest.fixture(autouse=True)
def fresh_state():
    main._objects.clear()
    main._objects["obj-001"] = {
        "id": "obj-001",
        "title": "Termo negro",
        "description": "Encontrado cerca de la biblioteca.",
        "status": "available",
    }
    main._claims.clear()


@pytest.fixture
def client():
    with TestClient(main.app) as c:  # ejecuta lifespan (valida JWT_SECRET)
        yield c


def token(sub="student-42"):
    return jwt.encode({"sub": sub}, os.environ["JWT_SECRET"], algorithm="HS256")


def auth(sub="student-42"):
    return {"Authorization": f"Bearer {token(sub)}"}


def schema(name):
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return Draft202012Validator(spec["components"]["schemas"][name])


#health y listado 
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_search_objects(client):
    r = client.get("/objects")
    assert r.status_code == 200
    assert [o["id"] for o in r.json()["items"]] == ["obj-001"]
    assert client.get("/objects?q=termo").json()["total"] == 1
    assert client.get("/objects?q=zzz").json()["total"] == 0


def test_metrics_groups_by_route_template_not_raw_path(client):
    for i in range(3):
        client.get("/objects")
        client.post(f"/v1/objects/x{i}/claims", headers=auth())
    data = client.get("/metrics").json()
    assert data["/objects"]["samples"] >= 3
    assert data["/objects"]["p95_ms"] is not None
    assert "/v1/objects/{object_id}/claims" in data
    assert not any(k.startswith("/v1/objects/x") for k in data)


#reclamación: un test por respuesta del contrato
def test_claim_201_and_matches_contract_schema(client):
    r = client.post("/v1/objects/obj-001/claims", headers=auth())
    assert r.status_code == 201
    schema("Claim").validate(r.json())
    assert r.json() == {"objectId": "obj-001", "userId": "student-42", "verified": True}


def test_claim_401_without_token(client):
    r = client.post("/v1/objects/obj-001/claims")
    assert r.status_code == 401
    schema("Problem").validate(r.json())
    assert r.json()["code"] == "UNAUTHENTICATED"


def test_claim_401_with_invalid_token(client):
    r = client.post(
        "/v1/objects/obj-001/claims", headers={"Authorization": "Bearer basura"}
    )
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"


def test_claim_404_object_not_found(client):
    r = client.post("/v1/objects/no-existe/claims", headers=auth())
    assert r.status_code == 404
    schema("Problem").validate(r.json())
    assert r.json()["code"] == "OBJECT_NOT_FOUND"


def test_claim_409_already_claimed(client):
    assert client.post("/v1/objects/obj-001/claims", headers=auth()).status_code == 201
    r = client.post("/v1/objects/obj-001/claims", headers=auth("otro-usuario"))
    assert r.status_code == 409
    schema("Problem").validate(r.json())
    assert r.json()["code"] == "OBJECT_ALREADY_CLAIMED"


def test_claim_422_identity_not_verified(client):
    r = client.post("/v1/objects/obj-001/claims", headers=auth("   "))
    assert r.status_code == 422
    schema("Problem").validate(r.json())
    assert r.json()["code"] == "IDENTITY_NOT_VERIFIED"
    # una reclamación rechazada no debe cambiar el estado del objeto
    assert main._objects["obj-001"]["status"] == "available"


#logs estructurados 
def test_request_log_is_structured_json(client, caplog):
    with caplog.at_level(logging.INFO, logger="lostvault"):
        client.get("/health")
    record = next(r for r in caplog.records if r.getMessage() == "request")
    line = json.loads(main.JsonFormatter().format(record))
    assert line["endpoint"] == "/health"
    assert line["status_code"] == 200
    assert line["method"] == "GET"
    assert isinstance(line["duration_ms"], float)
    assert "request_id" in line and "time" in line


def test_logs_never_contain_the_token(client, caplog):
    with caplog.at_level(logging.INFO, logger="lostvault"):
        client.post("/v1/objects/obj-001/claims", headers=auth())
    dumped = " ".join(
        main.JsonFormatter().format(r) for r in caplog.records if r.name == "lostvault"
    )
    assert token() not in dumped


def test_root_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "LostVault API"
    assert data["status"] == "online"
    assert data["docs"] == "/docs"


def test_cors_headers_present(client):
    r = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"

def test_p95_calculation_with_known_values(client):
    from collections import deque

    main._durations_by_endpoint["/objects"] = deque(range(1, 101))
    data = client.get("/metrics").json()["/objects"]
    assert data["p95_ms"] == 95.95
    assert data["objective_ms"] == 2000 and data["met"] is True

    main._durations_by_endpoint["/objects"] = deque([3000] * 10)
    data = client.get("/metrics").json()["/objects"]
    assert data["p95_ms"] == 3000 and data["met"] is False