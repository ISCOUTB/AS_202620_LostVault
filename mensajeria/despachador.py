"""Despachador del outbox: entrega al menos una vez, con reintentos y fallidos.

Política (docs/mensajeria/taller-mensajeria.md §4):
- Reintento solo ante fallos recuperables (cualquier excepción salvo ContratoInvalido).
- Backoff exponencial con jitter: base * 2^(intento-1), acotado por `tope`, y se
  espera entre la mitad y el total de ese valor (jitter "igual").
- Tras `max_intentos` el mensaje pasa a estado 'fallido' (cola de mensajes
  fallidos). Un mensaje fuera de contrato va a fallidos sin reintentar.
- Orden por objeto: si un evento de un objeto está esperando reintento, los
  siguientes de ese mismo objeto esperan; los de otros objetos siguen.
- El evento se marca 'publicado' DESPUÉS de que el consumidor confirma. Si el
  despachador se cae entre entregar y marcar, el evento se reenvía (por eso el
  consumidor deduplica).
"""

import json
import random
import sqlite3
import time
from collections.abc import Callable

from mensajeria.contrato import ContratoInvalido
from mensajeria.trazas import traza


class CaidaSimulada(Exception):
    """El proceso del despachador muere después de entregar y antes de marcar."""


class Despachador:
    def __init__(
        self,
        conn: sqlite3.Connection,
        consumidor,
        reloj: Callable[[], float] = time.time,
        aleatorio: Callable[[], float] = random.random,
        max_intentos: int = 5,
        base_segundos: float = 1.0,
        tope_segundos: float = 60.0,
    ) -> None:
        self.conn = conn
        self.consumidor = consumidor
        self.reloj = reloj
        self.aleatorio = aleatorio
        self.max_intentos = max_intentos
        self.base = base_segundos
        self.tope = tope_segundos
        # Gancho de prueba: si devuelve True, se simula la caída tras entregar.
        self.caer_tras_entregar: Callable[[dict], bool] = lambda evento: False

    def espera(self, intento: int) -> float:
        techo = min(self.tope, self.base * 2 ** (intento - 1))
        return techo / 2 + self.aleatorio() * techo / 2

    def despachar_pendientes(self) -> int:
        """Una vuelta del publicador. Devuelve cuántos eventos quedaron publicados."""
        ahora = self.reloj()
        pendientes = self.conn.execute(
            "SELECT * FROM outbox WHERE estado = 'pendiente' ORDER BY seq"
        ).fetchall()
        bloqueados: set[str] = set()
        publicados = 0
        for fila in pendientes:
            agregado = fila["aggregate_id"]
            if agregado in bloqueados:
                continue
            if fila["proximo_intento"] > ahora:
                bloqueados.add(agregado)  # respeta el orden dentro del objeto
                continue
            evento = json.loads(fila["payload"])
            intento = fila["intentos"] + 1
            traza("despachado", "despachador", evento, intento=intento)
            try:
                self.consumidor.recibir(evento)
            except ContratoInvalido as error:
                self._a_fallidos(fila, evento, intento, f"contrato: {error}")
                continue
            except Exception as error:  # fallo recuperable
                if intento >= self.max_intentos:
                    self._a_fallidos(fila, evento, intento, repr(error))
                else:
                    espera = self.espera(intento)
                    with self.conn:
                        self.conn.execute(
                            "UPDATE outbox SET intentos = ?, proximo_intento = ?, ultimo_error = ? "
                            "WHERE seq = ?",
                            (intento, ahora + espera, repr(error), fila["seq"]),
                        )
                    traza(
                        "reintento_programado", "despachador", evento,
                        intento=intento, espera_s=round(espera, 3), detalle=repr(error),
                    )
                    bloqueados.add(agregado)
                continue
            if self.caer_tras_entregar(evento):
                raise CaidaSimulada(evento["event_id"])
            with self.conn:
                self.conn.execute(
                    "UPDATE outbox SET estado = 'publicado', intentos = ? WHERE seq = ?",
                    (intento, fila["seq"]),
                )
            traza("confirmado_en_outbox", "despachador", evento, intento=intento)
            publicados += 1
        return publicados

    def _a_fallidos(self, fila, evento: dict, intento: int, error: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE outbox SET estado = 'fallido', intentos = ?, ultimo_error = ? WHERE seq = ?",
                (intento, error, fila["seq"]),
            )
        traza("enviado_a_fallidos", "despachador", evento, intento=intento, detalle=error)

    def fallidos(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT event_id, type, aggregate_id, intentos, ultimo_error FROM outbox "
            "WHERE estado = 'fallido' ORDER BY seq"
        ).fetchall()

    def reprocesar(self, event_id: str) -> None:
        """Devuelve un mensaje fallido a la cola tras corregir la causa (redrive manual)."""
        with self.conn:
            self.conn.execute(
                "UPDATE outbox SET estado = 'pendiente', intentos = 0, proximo_intento = 0 "
                "WHERE event_id = ? AND estado = 'fallido'",
                (event_id,),
            )
