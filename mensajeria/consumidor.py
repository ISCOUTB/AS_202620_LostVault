"""Consumidor idempotente: deja un aviso para la oficina por cada evento, una sola vez.

Tiene su propia base (otro servicio). El efecto (fila en `avisos`) y el registro
del event_id en `eventos_procesados` se guardan en la misma transacción, así que
recibir el mismo evento N veces produce un solo aviso.
"""

import sqlite3
from collections.abc import Callable

from mensajeria.contrato import validar
from mensajeria.trazas import traza

ESQUEMA = """
CREATE TABLE IF NOT EXISTS eventos_procesados (
  event_id TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS avisos (
  event_id       TEXT PRIMARY KEY REFERENCES eventos_procesados(event_id),
  correlation_id TEXT NOT NULL,
  object_id      TEXT NOT NULL,
  texto          TEXT NOT NULL
);
"""


class ErrorTransitorio(Exception):
    """Fallo recuperable del destino (p. ej. el servicio de correo no responde)."""


def abrir(ruta: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.executescript(ESQUEMA)
    return conn


def _texto(evento: dict) -> str:
    d = evento["data"]
    if evento["type"] == "ClaimCreated":
        return f"Entregar objeto {d['objectId']} a {d['userId']} (identidad verificada)."
    return f"Revisar intento bloqueado sobre {d['objectId']} por {d['userId']}: {d['reason']}."


class Notificador:
    def __init__(
        self,
        conn: sqlite3.Connection,
        transporte: Callable[[dict], None] | None = None,
    ) -> None:
        self.conn = conn
        # Llamada al destino externo; puede lanzar ErrorTransitorio.
        self.transporte = transporte or (lambda evento: None)

    def recibir(self, evento: dict) -> bool:
        """Procesa el evento. Devuelve False si era un duplicado ya procesado."""
        validar(evento)  # ContratoInvalido -> el despachador lo manda a fallidos
        traza("recibido", "consumidor", evento)
        with self.conn:
            ya = self.conn.execute(
                "SELECT 1 FROM eventos_procesados WHERE event_id = ?", (evento["event_id"],)
            ).fetchone()
            if ya:
                traza("duplicado_ignorado", "consumidor", evento)
                return False
            self.transporte(evento)  # si falla, ROLLBACK: no queda marcado como procesado
            self.conn.execute(
                "INSERT INTO eventos_procesados (event_id) VALUES (?)", (evento["event_id"],)
            )
            self.conn.execute(
                "INSERT INTO avisos (event_id, correlation_id, object_id, texto) VALUES (?, ?, ?, ?)",
                (evento["event_id"], evento["correlation_id"], evento["aggregate_id"], _texto(evento)),
            )
        traza("entregado", "consumidor", evento)
        return True
