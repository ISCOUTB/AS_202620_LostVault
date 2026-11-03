"""Almacenamiento en memoria (mismo alcance que la línea base del repositorio).

Los datos se pierden al reiniciar el proceso. Para persistencia real, reemplaza
esta clase por un repositorio sobre una base de datos.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class LostObject:
    id: str
    name: str
    claimed_by: str | None = None
    description: str | None = None
    reported_by: str | None = None


def default_objects() -> list[LostObject]:
    return [LostObject(id="1", name="Termo negro")]


class ClaimStore:
    def __init__(
        self,
        objects: list[LostObject] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.lock = threading.Lock()
        self.clock = clock
        self.objects: dict[str, LostObject] = {
            o.id: o for o in (objects if objects is not None else default_objects())
        }
        # (userId, Idempotency-Key) -> (objectId, expira_en)
        self.idempotency: dict[tuple[str, str], tuple[str, float]] = {}

    def purge_expired_keys(self, now: float) -> None:
        expired = [k for k, (_, exp) in self.idempotency.items() if exp <= now]
        for k in expired:
            del self.idempotency[k]
