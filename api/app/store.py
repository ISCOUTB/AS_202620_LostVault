"""Almacén de objetos, reclamaciones y sesiones."""

import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone


@dataclass
class LostObject:
    id: str
    name: str
    claimed_by: str | None = None
    description: str | None = None
    reported_by: str | None = None
    delivered: bool = False
    approved: bool = False
    found_at: str | None = None
    location: str | None = None
    photo_url: str | None = None
    received_at: str | None = None
    history: list[dict[str, str]] = field(default_factory=list)

    def record(self, action: str, actor: str, now: float, reason: str = "") -> None:
        event = {
            "action": action,
            "actor": actor,
            "at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
        }
        if reason:
            event["reason"] = reason
        self.history.append(event)



def default_objects() -> list[LostObject]:
    return [LostObject(id="1", name="Termo negro")]


class ClaimStore:
    def __init__(
        self,
        objects: list[LostObject] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._lock = threading.Lock()
        self.suspended: dict[str, bool] = {}
        self.session_versions: dict[str, int] = {}
        self.clock = clock
        self.objects: dict[str, LostObject] = {
            o.id: o for o in (objects if objects is not None else default_objects())
        }
        # (userId, Idempotency-Key) -> (objectId, expira_en)
        self.idempotency: dict[tuple[str, str], tuple[str, float]] = {}

    @contextmanager
    def transaction(self):
        with self._lock:
            yield

    def user_session(self, user_id: str) -> tuple[bool, int]:
        with self.transaction():
            return self.suspended.get(user_id, False), self.session_versions.get(user_id, 0)

    def set_suspended(self, user_id: str, suspended: bool) -> bool:
        with self.transaction():
            if self.suspended.get(user_id, False) != suspended:
                self.suspended[user_id] = suspended
                if suspended:
                    self.session_versions[user_id] = self.session_versions.get(user_id, 0) + 1
            return suspended

    def purge_expired_keys(self, now: float) -> None:
        expired = [k for k, (_, exp) in self.idempotency.items() if exp <= now]
        for k in expired:
            del self.idempotency[k]


class PostgresClaimStore(ClaimStore):
    # El corte usa una fila de estado, bloqueada durante cada operación.
    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url
        self._initialized = False

    def _snapshot(self) -> dict:
        return {
            "objects": [asdict(obj) for obj in self.objects.values()],
            "idempotency": [[*key, *value] for key, value in self.idempotency.items()],
            "suspended": self.suspended,
            "session_versions": self.session_versions,
        }

    @contextmanager
    def transaction(self):
        import psycopg
        from psycopg.types.json import Jsonb

        with self._lock, psycopg.connect(self.url, connect_timeout=5) as conn:
            if not self._initialized:
                conn.execute("SELECT pg_advisory_xact_lock(1901712026)")
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS lostvault_state "
                    "(id integer PRIMARY KEY, data jsonb NOT NULL)"
                )
                conn.execute(
                    "INSERT INTO lostvault_state VALUES (1, %s) ON CONFLICT DO NOTHING",
                    (Jsonb(self._snapshot()),),
                )
                conn.commit()
                self._initialized = True

            snapshot = conn.execute(
                "SELECT data FROM lostvault_state WHERE id = 1 FOR UPDATE"
            ).fetchone()[0]
            self.objects = {item["id"]: LostObject(**deepcopy(item)) for item in snapshot["objects"]}
            self.idempotency = {(u, k): (o, t) for u, k, o, t in snapshot["idempotency"]}
            self.suspended = snapshot.get("suspended", {}).copy()
            self.session_versions = snapshot.get("session_versions", {}).copy()
            yield
            updated = self._snapshot()
            if updated != snapshot:
                conn.execute("UPDATE lostvault_state SET data = %s WHERE id = 1", (Jsonb(updated),))
