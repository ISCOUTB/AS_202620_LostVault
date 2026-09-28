"""API de LostVault.

Endpoints: /health, /metrics, /objects y el de reclamar un objeto
(POST /v1/objects/{objectId}/claims, definido en docs/contracts/lostvault-api.yaml).

Por ahora los datos viven en memoria y se pierden al reiniciar.
Falta conectar PostgreSQL.
"""
import json
import logging
import os
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
# Logs estructurados (una línea JSON por evento, a stdout)
# Aquí convierto cada log en un objeto JSON para que todos los eventos
        # tengan la misma estructura y sea más fácil analizarlos posteriormente.
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        entry.update(getattr(record, "fields", {}))
        return json.dumps(entry, ensure_ascii=False)


logger = logging.getLogger("lostvault")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(JsonFormatter())
    logger.addHandler(_handler)
    logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
  #Configuración y secretos: solo desde variables de entorno, sin defaults
def jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET no está definido en el entorno.")
    return secret


@asynccontextmanager
async def lifespan(_: FastAPI):
    jwt_secret()  # falla al arrancar si falta el secreto, no en la primera petición
    logger.info("startup", extra={"fields": {"event": "startup"}})
    yield


app = FastAPI(title="LostVault API", version="1.0.0", lifespan=lifespan)


 #Errores con el formato Problem del contrato: {"code": ..., "message": ...}
class ApiProblem(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


@app.exception_handler(ApiProblem)
async def api_problem_handler(_: Request, exc: ApiProblem):
    return JSONResponse(
        status_code=exc.status,
        content={"code": exc.code, "message": exc.message},
    )
# Dominio en memoria (espejo de LostObject / Claim / verificación en Dart)
_lock = threading.Lock()
_objects: dict[str, dict] = {
    "obj-001": {
        "id": "obj-001",
        "title": "Termo negro",
        "description": "Encontrado cerca de la biblioteca.",
        "status": "available",
    }
}
_claims: list[dict] = []


def verify_identity(user_id: str) -> bool:
    # Igual que InMemoryIdentityVerificationService: válida si el id no es vacío.
    return bool(user_id.strip())


def current_user_id(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiProblem(401, "UNAUTHENTICATED", "Debes iniciar sesión.")
    try:
        payload = jwt.decode(
            token, jwt_secret(), algorithms=["HS256"], options={"require": ["sub"]}
        )
    except jwt.PyJWTError:
        raise ApiProblem(401, "UNAUTHENTICATED", "Token inválido o expirado.")
    return str(payload["sub"])
# Middleware: un log JSON por request (endpoint, status, duration_ms)
@app.middleware("http")
async def access_log(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        route = request.scope.get("route")
        logger.info(
            "request",
            extra={
                "fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "endpoint": getattr(route, "path", request.url.path),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            },
        )
# Endpoints
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/v1/objects")
async def list_objects(status: str | None = None):
    with _lock:
        items = list(_objects.values())
    if status:
        items = [o for o in items if o["status"] == status]
    return items


@app.post("/v1/objects/{object_id}/claims", status_code=201)
async def create_claim(object_id: str, request: Request):
    user_id = current_user_id(request)

    with _lock:
        obj = _objects.get(object_id)
        if obj is None:
            raise ApiProblem(404, "OBJECT_NOT_FOUND", "El objeto solicitado no existe.")
        if obj["status"] != "available":
            raise ApiProblem(
                409, "OBJECT_ALREADY_CLAIMED", "El objeto ya fue reclamado."
            )
        if not verify_identity(user_id):
            raise ApiProblem(
                422, "IDENTITY_NOT_VERIFIED", "La identidad no pudo verificarse."
            )
        claim = {"objectId": object_id, "userId": user_id, "verified": True}
        _claims.append(claim)
        obj["status"] = "claimed"
    return claim
