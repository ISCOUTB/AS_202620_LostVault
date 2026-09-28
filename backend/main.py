"""
LostVault API — esqueleto inicial (propuesta)

Este archivo es un punto de partida, no código integrado al proyecto todavía.
Antes de fusionarlo, confirma con el equipo si ya existe trabajo de FastAPI en
curso, para no duplicar esfuerzo.

Implementa:
- GET /objects  (búsqueda, según docs/contracts/lostvault-api.yaml de S7)
- GET /health   (health check, evidencia S8)
- Middleware que mide duration_ms por request y lo expone en /metrics,
  ligado al escenario de calidad: 95% de búsquedas en <=2s (p95) con 200
  usuarios concurrentes.
"""

import json
import time
import logging
from collections import deque
from statistics import quantiles

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="LostVault API", version="1.0.0")

# --- Logging estructurado -----------------------------------------------
# Cada línea de log es un objeto JSON; en producción esto se redirige a la
# salida estándar y el proveedor de despliegue lo recolecta.
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key in ("endpoint", "method", "status_code", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("lostvault")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False


# --- Métrica: p95 de latencia por endpoint -------------------------------
# Ventana simple en memoria de las últimas N duraciones, por endpoint.
# Suficiente para el volumen estimado del proyecto (ver
# docs/despliegue/estimacion-costo-mensual.md); si el volumen crece,
# esto debería moverse a un backend de métricas real (Prometheus, etc.).
_WINDOW_SIZE = 500
_durations_by_endpoint: dict[str, deque] = {}


@app.middleware("http")
async def measure_latency(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    endpoint = request.url.path
    bucket = _durations_by_endpoint.setdefault(endpoint, deque(maxlen=_WINDOW_SIZE))
    bucket.append(duration_ms)

    # Log estructurado por request (clave: valor, fácil de parsear)
    logger.info(
        "request",
        extra={
            "endpoint": endpoint,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )

    response.headers["X-Response-Time-ms"] = str(round(duration_ms, 2))
    return response


def _p95(endpoint: str) -> float | None:
    bucket = _durations_by_endpoint.get(endpoint)
    if not bucket or len(bucket) < 2:
        return None
    # quantiles con n=100 da percentiles; [94] ~ p95
    return round(quantiles(list(bucket), n=100)[94], 2)


# --- Health check ---------------------------------------------------------
@app.get("/health")
async def health():
    """
    Declara si la instancia está en condiciones de atender.
    TODO: cuando exista conexión real a base de datos, verificarla aquí
    y devolver 503 si falla (la guía sugiere probarlo apagando la DB).
    """
    return {"status": "ok"}


# --- Métrica consultable ---------------------------------------------------
@app.get("/metrics")
async def metrics():
    """
    Expone la latencia p95 por endpoint medida hasta ahora.
    Ligada al escenario de calidad: /objects debe mantenerse por debajo
    de 2000 ms en el p95.
    """
    data = {
        endpoint: {
            "p95_ms": _p95(endpoint),
            "samples": len(bucket),
        }
        for endpoint, bucket in _durations_by_endpoint.items()
    }
    return JSONResponse(content=data)


# --- Endpoint de negocio (según contrato OpenAPI de S7) -------------------
@app.get("/objects")
async def search_objects(status: str | None = None, q: str | None = None):
    """
    Placeholder: aquí se conectaría con la lógica real de búsqueda.
    Por ahora devuelve una lista vacía para que el middleware de métricas
    y el health check ya sean verificables end-to-end.
    """
    return {"items": [], "page": 1, "pageSize": 20, "total": 0}
