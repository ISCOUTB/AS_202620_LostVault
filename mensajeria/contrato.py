"""Contrato de los eventos: construcción y validación contra el JSON Schema."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "contracts"
    / "claim-events.v1.schema.json"
)
SCHEMA_VERSION = 1

_validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


class ContratoInvalido(Exception):
    """El mensaje no cumple el contrato. No se reintenta: va directo a fallidos."""


def nuevo_evento(tipo: str, object_id: str, user_id: str, correlation_id: str, **extra) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "type": tipo,
        "schema_version": SCHEMA_VERSION,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
        "aggregate_id": object_id,
        "data": {"objectId": object_id, "userId": user_id, **extra},
    }


def validar(evento: dict) -> None:
    errores = sorted(_validator.iter_errors(evento), key=lambda e: list(e.path))
    if errores:
        detalle = "; ".join(f"{'/'.join(map(str, e.path)) or '(raíz)'}: {e.message}" for e in errores)
        raise ContratoInvalido(detalle)
