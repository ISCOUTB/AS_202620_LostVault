"""Outbox, publicador y consumidor idempotente de ClaimCreated.

Contrato: docs/contracts/claim-created.asyncapi.yaml
Decisión: docs/adr/0007-aviso-reclamacion-asincrono.md
Garantías: docs/datos/eventos.md (al menos una vez + consumidor idempotente).

Es un simulador local: la "cola" es una lista en memoria con la misma forma que
la tabla `outbox` propuesta en eventos.md (attempts, published_at, failed_at).
Cuando exista PostgreSQL (ADR 0006), solo cambia `Outbox`; el publicador y el
consumidor no se tocan.
"""
from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger("lostvault")

EVENT_TYPE = "ClaimCreated"
SCHEMA_VERSION = 1
MAX_ATTEMPTS = 5
BASE_DELAY_SECONDS = 30.0   # 30 s, 60 s, 120 s, 240 s entre intentos
MAX_DELAY_SECONDS = 900.0   # tope = periodo del publicador (15 min)
JITTER = 0.2                # ±20 %


class TransientError(Exception):
    """Fallo recuperable (timeout, 5xx, proveedor de correo caído): se reintenta."""


class PermanentError(Exception):
    """Fallo no recuperable (mensaje inválido, destinatario inexistente): va a DLQ."""


def build_claim_created(claim: dict, request_id: str | None, now: float) -> dict:
    """Construye el mensaje según el contrato (versión 1).

    event_id es determinista a partir de la reclamación (objeto + usuario), así
    que un reintento HTTP que reproduce la misma reclamación no crea otro evento.
    """
    event_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"lostvault:claim:{claim['objectId']}:{claim['userId']}")
    )
    return {
        "eventId": event_id,
        "type": EVENT_TYPE,
        "schemaVersion": SCHEMA_VERSION,
        "occurredAt": now,
        "correlationId": request_id or event_id,
        "data": {"objectId": claim["objectId"], "userId": claim["userId"]},
    }


REQUIRED_FIELDS = {"eventId", "type", "schemaVersion", "occurredAt", "correlationId", "data"}


def validate(message: dict) -> None:
    """Compatibilidad del consumidor: exige los campos de la versión 1 y tolera
    campos adicionales (cambio compatible). Versión mayor desconocida = rechazo."""
    missing = REQUIRED_FIELDS - message.keys()
    if missing:
        raise PermanentError(f"faltan campos: {sorted(missing)}")
    if message["type"] != EVENT_TYPE:
        raise PermanentError(f"tipo desconocido: {message['type']}")
    if not isinstance(message["schemaVersion"], int) or message["schemaVersion"] > SCHEMA_VERSION:
        raise PermanentError(f"schemaVersion no soportada: {message['schemaVersion']}")
    data = message["data"]
    if not isinstance(data, dict) or not data.get("objectId") or not data.get("userId"):
        raise PermanentError("data.objectId y data.userId son obligatorios")


@dataclass
class OutboxRow:
    message: dict
    attempts: int = 0
    next_attempt_at: float = 0.0
    published_at: float | None = None
    failed_at: float | None = None
    last_error: str | None = None

    @property
    def event_id(self) -> str:
        return self.message.get("eventId", "?")

    @property
    def pending(self) -> bool:
        return self.published_at is None and self.failed_at is None


class Outbox:
    """Misma semántica que la tabla outbox: clave primaria = event_id."""

    def __init__(self) -> None:
        self._rows: dict[str, OutboxRow] = {}
        self._lock = threading.Lock()

    def add(self, message: dict) -> bool:
        """Inserta; False si el event_id ya existía (PRIMARY KEY)."""
        with self._lock:
            if message["eventId"] in self._rows:
                return False
            self._rows[message["eventId"]] = OutboxRow(message=message)
            return True

    def rows(self) -> list[OutboxRow]:
        with self._lock:
            return list(self._rows.values())

    def clear(self) -> None:
        with self._lock:
            self._rows.clear()


class OfficeNotifier:
    """Consumidor: avisa a la oficina de objetos perdidos.

    Idempotente: guarda los eventId ya procesados y descarta los repetidos.
    `send` es el efecto externo (correo); se inyecta para poder simularlo.
    """

    def __init__(self, send: Callable[[dict], None]) -> None:
        self._send = send
        self._processed: set[str] = set()
        self._lock = threading.Lock()
        self.sent = 0
        self.duplicates = 0

    def handle(self, message: dict) -> str:
        validate(message)
        event_id = message["eventId"]
        with self._lock:
            if event_id in self._processed:
                self.duplicates += 1
                logger.info(
                    "consumer_duplicate_discarded",
                    extra={"event": "consumer_duplicate_discarded", "event_id": event_id,
                           "correlation_id": message["correlationId"]},
                )
                return "duplicate"
        # El envío va fuera del lock; se marca como procesado solo si tuvo éxito.
        # Si el proceso muere entre enviar y marcar, el evento se reenvía
        # (al menos una vez): el aviso duplicado a la oficina es el costo aceptado.
        self._send(message)
        with self._lock:
            self._processed.add(event_id)
            self.sent += 1
        logger.info(
            "consumer_processed",
            extra={"event": "consumer_processed", "event_id": event_id,
                   "correlation_id": message["correlationId"]},
        )
        return "processed"


def backoff_delay(attempts: int, rng: Callable[[], float] = random.random) -> float:
    """Retroceso exponencial con jitter: 30 s · 2^(attempts-1), tope 900 s, ±20 %."""
    base = min(BASE_DELAY_SECONDS * (2 ** (attempts - 1)), MAX_DELAY_SECONDS)
    return base * (1 + JITTER * (2 * rng() - 1))


@dataclass
class Counters:
    enqueued: int = 0
    published: int = 0
    retried: int = 0
    dead_lettered: int = 0
    duplicates_discarded: int = 0


@dataclass
class Publisher:
    outbox: Outbox
    consumer: OfficeNotifier
    clock: Callable[[], float] = time.time
    rng: Callable[[], float] = random.random
    counters: Counters = field(default_factory=Counters)

    def run_once(self) -> dict:
        """Una vuelta del trabajo programado. Devuelve un resumen de la vuelta."""
        now = self.clock()
        summary = {"published": 0, "retried": 0, "dead_lettered": 0, "skipped": 0}
        blocked_objects: set[str] = set()
        rows = sorted(
            (r for r in self.outbox.rows() if r.pending),
            key=lambda r: (r.message.get("data", {}).get("objectId", ""), r.message.get("occurredAt", 0)),
        )
        for row in rows:
            object_id = row.message.get("data", {}).get("objectId", "")
            # Orden por objeto: si un evento de este objeto falló, no se sigue con los demás.
            if object_id in blocked_objects or row.next_attempt_at > now:
                summary["skipped"] += 1
                if row.next_attempt_at > now:
                    blocked_objects.add(object_id)
                continue
            row.attempts += 1
            ctx = {"event_id": row.event_id,
                   "correlation_id": row.message.get("correlationId"),
                   "attempt": row.attempts}
            try:
                outcome = self.consumer.handle(row.message)
            except PermanentError as exc:
                self._dead_letter(row, str(exc), now, ctx)
                summary["dead_lettered"] += 1
                continue
            except TransientError as exc:
                row.last_error = str(exc)
                if row.attempts >= MAX_ATTEMPTS:
                    self._dead_letter(row, f"agotó {MAX_ATTEMPTS} intentos: {exc}", now, ctx)
                    summary["dead_lettered"] += 1
                else:
                    row.next_attempt_at = now + backoff_delay(row.attempts, self.rng)
                    self.counters.retried += 1
                    summary["retried"] += 1
                    logger.warning(
                        "publisher_retry_scheduled",
                        extra={"event": "publisher_retry_scheduled", **ctx,
                               "retry_in_s": round(row.next_attempt_at - now, 1)},
                    )
                blocked_objects.add(object_id)
                continue
            # Se marca published_at DESPUÉS de que el consumidor confirma.
            row.published_at = now
            if outcome == "duplicate":
                self.counters.duplicates_discarded += 1
            self.counters.published += 1
            summary["published"] += 1
            logger.info("publisher_published", extra={"event": "publisher_published", **ctx})
        return summary

    def _dead_letter(self, row: OutboxRow, reason: str, now: float, ctx: dict) -> None:
        row.failed_at = now
        row.last_error = reason
        self.counters.dead_lettered += 1
        logger.error(
            "publisher_dead_lettered",
            extra={"event": "publisher_dead_lettered", **ctx, "reason": reason},
        )

    def dead_letters(self) -> list[OutboxRow]:
        return [r for r in self.outbox.rows() if r.failed_at is not None]
