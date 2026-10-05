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
from collections import deque
from contextlib import asynccontextmanager
from statistics import quantiles

import jwt
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# Logs en JSON, una línea por evento
class JsonFormatter(logging.Formatter):
    FIELDS = ("request_id", "endpoint", "method", "status_code", "duration_ms", "event")

    def format(self, record):
        payload = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key in self.FIELDS:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger("lostvault")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())


def jwt_secret() -> str:
    # El secreto viene solo del entorno, nunca del código
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET no está definido en el entorno.")
    return secret


@asynccontextmanager
async def lifespan(_: FastAPI):
    jwt_secret()  # si falta, falla al arrancar y no en la primera petición
    logger.info("startup", extra={"event": "startup"})
    yield


app = FastAPI(title="LostVault API", version="1.0.0", lifespan=lifespan)

# Soporte de CORS para clientes web (p. ej. Flutter Web) y móviles
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApiProblem(Exception):
    """Error con el formato {code, message} que pide el contrato."""

    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


@app.exception_handler(ApiProblem)
async def api_problem_handler(_: Request, exc: ApiProblem):
    return JSONResponse(
        status_code=exc.status, content={"code": exc.code, "message": exc.message}
    )


# Latencias recientes por endpoint, para calcular el p95
_WINDOW_SIZE = 500
_durations_by_endpoint: dict[str, deque] = {}

# Objetivo de p95 (ms) por endpoint, tomado del Escenario 4 de calidad
# (docs/arc42/10_requisitos_calidad.md): búsqueda con p95 <= 2 s.
OBJECTIVES_MS = {"/objects": 2000}


def _p95(endpoint: str):
    bucket = _durations_by_endpoint.get(endpoint)
    if not bucket or len(bucket) < 2:
        return None
    return round(quantiles(list(bucket), n=100)[94], 2)


@app.middleware("http")
async def measure_latency(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        route = request.scope.get("route")
        # Se usa la ruta con {object_id}, no la real, para no crear un grupo por objeto
        endpoint = getattr(route, "path", request.url.path)
        bucket = _durations_by_endpoint.setdefault(endpoint, deque(maxlen=_WINDOW_SIZE))
        bucket.append(duration_ms)
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "endpoint": endpoint,
                "method": request.method,
                "status_code": status,
                "duration_ms": round(duration_ms, 2),
            },
        )


# Datos en memoria
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
    # Igual que en la app Flutter: es válida si el id no viene vacío
    return bool(user_id.strip())


def current_user_id(request: Request) -> str:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiProblem(401, "UNAUTHENTICATED", "Debes iniciar sesión.")
    try:
        payload = jwt.decode(
            token, jwt_secret(), algorithms=["HS256"], options={"require": ["sub"]}
        )
    except jwt.PyJWTError:
        raise ApiProblem(401, "UNAUTHENTICATED", "Token inválido o expirado.")
    return str(payload["sub"])


@app.get("/")
async def root():
    return {
        "name": "LostVault API",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    # TODO: cuando haya base de datos, revisarla aquí y devolver 503 si falla
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    content = {}
    for endpoint, bucket in _durations_by_endpoint.items():
        p95 = _p95(endpoint)
        entry = {"p95_ms": p95, "samples": len(bucket)}
        objective = OBJECTIVES_MS.get(endpoint)
        if objective is not None:
            # Ligar la medición al escenario: objetivo y si se cumple
            entry["objective_ms"] = objective
            entry["met"] = None if p95 is None else p95 <= objective
        content[endpoint] = entry
    return JSONResponse(content=content)


@app.get("/objects")
async def search_objects(status: str | None = None, q: str | None = None):
    with _lock:
        items = list(_objects.values())
    if status:
        items = [o for o in items if o["status"] == status]
    if q:
        needle = q.lower()
        items = [
            o for o in items
            if needle in o["title"].lower() or needle in o["description"].lower()
        ]
    return {"items": items, "page": 1, "pageSize": 20, "total": len(items)}


@app.post("/v1/objects/{object_id}/claims", status_code=201)
async def create_claim(object_id: str, request: Request):
    # Mismo orden que ClaimObjectUseCase: sesión, objeto, disponibilidad, identidad
    user_id = current_user_id(request)
    with _lock:
        obj = _objects.get(object_id)
        if obj is None:
            raise ApiProblem(404, "OBJECT_NOT_FOUND", "El objeto solicitado no existe.")
        if obj["status"] != "available":
            raise ApiProblem(409, "OBJECT_ALREADY_CLAIMED", "El objeto ya fue reclamado.")
        if not verify_identity(user_id):
            raise ApiProblem(
                422, "IDENTITY_NOT_VERIFIED", "La identidad no pudo verificarse."
            )
        claim = {"objectId": object_id, "userId": user_id, "verified": True}
        _claims.append(claim)
        obj["status"] = "claimed"
    return claim
