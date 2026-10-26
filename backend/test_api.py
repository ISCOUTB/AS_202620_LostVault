import json
import logging
import os
import time
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
    main._idempotency.clear()


@pytest.fixture
def client():
    with TestClient(main.app) as c:  # ejecuta lifespan (valida JWT_SECRET)
        yield c


def token(sub="student-42", ttl_seconds=3600):
    claims = {"sub": sub, "exp": int(time.time()) + ttl_seconds}
    return jwt.encode(claims, os.environ["JWT_SECRET"], algorithm="HS256")


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


def test_claim_401_with_token_without_exp(client):
    sin_exp = jwt.encode({"sub": "student-42"}, os.environ["JWT_SECRET"], algorithm="HS256")
    r = client.post(
        "/v1/objects/obj-001/claims", headers={"Authorization": f"Bearer {sin_exp}"}
    )
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"
    assert main._objects["obj-001"]["status"] == "available"


def test_claim_401_with_expired_token(client):
    vencido = token(ttl_seconds=-60)
    r = client.post(
        "/v1/objects/obj-001/claims", headers={"Authorization": f"Bearer {vencido}"}
    )
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"
    assert main._objects["obj-001"]["status"] == "available"


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


#idempotencia: fallos parciales de la integración (Evidencia S11)
def test_retry_with_same_key_replays_original_201_without_duplicating(client):
    # Responde tarde: el cliente agota su timeout y reintenta con la misma clave
    headers = {**auth(), "Idempotency-Key": "k-123"}
    first = client.post("/v1/objects/obj-001/claims", headers=headers)
    retry = client.post("/v1/objects/obj-001/claims", headers=headers)
    assert first.status_code == retry.status_code == 201
    assert retry.json() == first.json()
    assert retry.headers["Idempotent-Replayed"] == "true"
    schema("Claim").validate(retry.json())
    assert len(main._claims) == 1


def test_same_user_repeating_without_key_gets_200_not_409(client):
    # Responde dos veces / doble toque: antes devolvía 409 al propio dueño
    assert client.post("/v1/objects/obj-001/claims", headers=auth()).status_code == 201
    r = client.post("/v1/objects/obj-001/claims", headers=auth())
    assert r.status_code == 200
    assert r.json() == {"objectId": "obj-001", "userId": "student-42", "verified": True}
    assert len(main._claims) == 1


def test_idempotency_does_not_let_another_user_take_the_object(client):
    assert client.post(
        "/v1/objects/obj-001/claims", headers={**auth(), "Idempotency-Key": "k-1"}
    ).status_code == 201
    r = client.post(
        "/v1/objects/obj-001/claims",
        headers={**auth("otro-usuario"), "Idempotency-Key": "k-1"},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "OBJECT_ALREADY_CLAIMED"


def test_key_reused_for_another_object_is_rejected(client):
    main._objects["obj-002"] = {
        "id": "obj-002", "title": "Llaves", "description": "Aula 3", "status": "available"
    }
    headers = {**auth(), "Idempotency-Key": "k-1"}
    assert client.post("/v1/objects/obj-001/claims", headers=headers).status_code == 201
    r = client.post("/v1/objects/obj-002/claims", headers=headers)
    assert r.status_code == 422
    schema("Problem").validate(r.json())
    assert r.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert main._objects["obj-002"]["status"] == "available"


def test_invalid_idempotency_key_is_400(client):
    r = client.post(
        "/v1/objects/obj-001/claims", headers={**auth(), "Idempotency-Key": "x" * 256}
    )
    assert r.status_code == 400
    schema("Problem").validate(r.json())
    assert r.json()["code"] == "INVALID_IDEMPOTENCY_KEY"


def test_failed_claim_is_not_cached_so_retry_can_succeed(client):
    # Un 404 no se guarda: si el objeto aparece después, el reintento sí lo crea
    headers = {**auth(), "Idempotency-Key": "k-9"}
    assert client.post("/v1/objects/obj-009/claims", headers=headers).status_code == 404
    main._objects["obj-009"] = {
        "id": "obj-009", "title": "Gafas", "description": "Cafetería", "status": "available"
    }
    assert client.post("/v1/objects/obj-009/claims", headers=headers).status_code == 201


def test_expired_key_is_purged(client, monkeypatch):
    headers = {**auth(), "Idempotency-Key": "k-old"}
    assert client.post("/v1/objects/obj-001/claims", headers=headers).status_code == 201
    later = main._now() + main.IDEMPOTENCY_TTL_SECONDS + 1
    monkeypatch.setattr(main, "_now", lambda: later)
    # Vencida la clave, cae en la deduplicación natural: sigue sin duplicar
    r = client.post("/v1/objects/obj-001/claims", headers=headers)
    assert r.status_code == 200
    assert ("student-42", "k-old") not in main._idempotency
    assert len(main._claims) == 1


def test_concurrent_claims_produce_exactly_one_201():
    from concurrent.futures import ThreadPoolExecutor

    def claim_as(user):
        # un TestClient por hilo: cada uno tiene su propio portal de eventos
        return TestClient(main.app).post(
            "/v1/objects/obj-001/claims", headers=auth(user)
        ).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(claim_as, [f"student-{i}" for i in range(10)]))
    assert codes.count(201) == 1
    assert codes.count(409) == 9
    assert len(main._claims) == 1


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
    secreto = token()
    with caplog.at_level(logging.INFO, logger="lostvault"):
        client.post(
            "/v1/objects/obj-001/claims", headers={"Authorization": f"Bearer {secreto}"}
        )
    dumped = " ".join(
        main.JsonFormatter().format(r) for r in caplog.records if r.name == "lostvault"
    )
    assert secreto not in dumped


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

# Política de caché (docs/datos/cache.md)
def test_objects_listing_is_cacheable_only_in_the_cdn(client):
    r = client.get("/objects", params={"q": "termo"})
    cache = r.headers["cache-control"]
    assert "public" in cache
    assert "s-maxage=30" in cache
    assert "stale-while-revalidate=60" in cache
    assert "max-age=0" in cache  # el navegador no guarda una segunda copia


def test_claim_responses_are_never_cached(client):
    ok = client.post("/v1/objects/obj-001/claims", headers=auth())
    replay = client.post("/v1/objects/obj-001/claims", headers=auth())
    conflict = client.post("/v1/objects/obj-001/claims", headers=auth("otro"))
    unauthenticated = client.post("/v1/objects/obj-001/claims")
    for r in (ok, replay, conflict, unauthenticated):
        assert r.headers["cache-control"] == "no-store", r.status_code


def test_health_and_metrics_are_not_cached(client):
    assert client.get("/health").headers["cache-control"] == "no-store"
    assert client.get("/metrics").headers["cache-control"] == "no-store"
