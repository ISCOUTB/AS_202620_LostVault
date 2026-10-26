"""Productor: la reclamación y su evento se escriben en la misma transacción (outbox).

El esquema replica el del ADR 0006 (objects, claims con UNIQUE(object_id)) más la
tabla outbox de docs/datos/eventos.md. Si la transacción se deshace, no queda ni
la reclamación ni el evento; si se confirma, quedan los dos.
"""

import json
import sqlite3
import uuid
from collections.abc import Callable

from mensajeria.contrato import nuevo_evento, validar
from mensajeria.trazas import traza

ESQUEMA = """
CREATE TABLE IF NOT EXISTS objects (
  id     TEXT PRIMARY KEY,
  title  TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('available', 'claimed'))
);
CREATE TABLE IF NOT EXISTS claims (
  id        TEXT PRIMARY KEY,
  object_id TEXT NOT NULL UNIQUE REFERENCES objects(id),
  user_id   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
  seq             INTEGER PRIMARY KEY AUTOINCREMENT,  -- orden de confirmación
  event_id        TEXT NOT NULL UNIQUE,
  aggregate_id    TEXT NOT NULL,
  type            TEXT NOT NULL,
  payload         TEXT NOT NULL,
  estado          TEXT NOT NULL DEFAULT 'pendiente'
                  CHECK (estado IN ('pendiente', 'publicado', 'fallido')),
  intentos        INTEGER NOT NULL DEFAULT 0,
  proximo_intento REAL NOT NULL DEFAULT 0,
  ultimo_error    TEXT
);
"""


class ObjetoNoEncontrado(Exception):
    pass


class ObjetoYaReclamado(Exception):
    pass


def abrir(ruta: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.executescript(ESQUEMA)
    return conn


def sembrar_objeto(conn: sqlite3.Connection, object_id: str, title: str) -> None:
    with conn:
        conn.execute(
            "INSERT INTO objects (id, title, status) VALUES (?, ?, 'available')",
            (object_id, title),
        )


def _encolar(conn: sqlite3.Connection, evento: dict) -> None:
    validar(evento)  # el productor nunca publica algo fuera de contrato
    conn.execute(
        "INSERT INTO outbox (event_id, aggregate_id, type, payload) VALUES (?, ?, ?, ?)",
        (evento["event_id"], evento["aggregate_id"], evento["type"], json.dumps(evento)),
    )


def reclamar(
    conn: sqlite3.Connection,
    object_id: str,
    user_id: str,
    correlation_id: str,
    identidad_valida: bool = True,
    antes_de_confirmar: Callable[[], None] | None = None,
) -> dict | None:
    """Reclama un objeto y deja el evento en el outbox, todo o nada.

    Devuelve la reclamación creada, o None si la identidad no es válida (en ese
    caso se publica ClaimRejected para que la oficina revise el intento).
    `antes_de_confirmar` permite simular una caída justo antes del COMMIT.
    """
    with conn:  # una transacción: COMMIT al salir, ROLLBACK si hay excepción
        fila = conn.execute("SELECT status FROM objects WHERE id = ?", (object_id,)).fetchone()
        if fila is None:
            raise ObjetoNoEncontrado(object_id)
        if fila["status"] != "available":
            raise ObjetoYaReclamado(object_id)

        if not identidad_valida:
            claim = None
            evento = nuevo_evento(
                "ClaimRejected", object_id, user_id, correlation_id,
                reason="IDENTITY_NOT_VERIFIED",
            )
        else:
            # UPDATE condicional: si otro proceso ya lo reclamó, no actualiza filas
            cur = conn.execute(
                "UPDATE objects SET status = 'claimed' WHERE id = ? AND status = 'available'",
                (object_id,),
            )
            if cur.rowcount == 0:
                raise ObjetoYaReclamado(object_id)
            claim = {"id": str(uuid.uuid4()), "objectId": object_id, "userId": user_id}
            conn.execute(
                "INSERT INTO claims (id, object_id, user_id) VALUES (?, ?, ?)",
                (claim["id"], object_id, user_id),
            )
            evento = nuevo_evento("ClaimCreated", object_id, user_id, correlation_id)
        _encolar(conn, evento)
        if antes_de_confirmar:
            antes_de_confirmar()
    traza("producido", "productor", evento)  # solo tras el COMMIT
    return claim
