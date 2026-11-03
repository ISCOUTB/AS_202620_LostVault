"""Alta y baja de objetos perdidos."""

import uuid

from app.auth import AuthenticatedUser
from app.errors import ApiError
from app.models import LostObjectOut
from app.store import ClaimStore, LostObject


def _to_out(o: LostObject) -> LostObjectOut:
    return LostObjectOut(
        id=o.id,
        name=o.name,
        description=o.description,
        reportedBy=o.reported_by,
        claimedBy=o.claimed_by,
    )


def create_object(
    store: ClaimStore,
    user: AuthenticatedUser,
    name: str,
    description: str | None,
) -> LostObjectOut:
    name = name.strip()
    if not name:
        raise ApiError(422, "VALIDATION_ERROR", "name: no puede estar vacío.")
    description = description.strip() if description else None
    with store.lock:
        obj = LostObject(
            id=uuid.uuid4().hex,
            name=name,
            description=description or None,
            reported_by=user.id,
        )
        store.objects[obj.id] = obj
        return _to_out(obj)


def delete_object(store: ClaimStore, user: AuthenticatedUser, object_id: str) -> None:
    with store.lock:
        obj = store.objects.get(object_id)
        if obj is None:
            raise ApiError(404, "OBJECT_NOT_FOUND", "El objeto solicitado no existe.")
        if obj.reported_by != user.id:
            raise ApiError(403, "FORBIDDEN", "Solo quien reportó el objeto puede borrarlo.")
        if obj.claimed_by is not None:
            raise ApiError(
                409,
                "OBJECT_ALREADY_CLAIMED",
                "No se puede borrar un objeto que ya fue reclamado.",
            )
        del store.objects[object_id]
