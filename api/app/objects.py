"""Alta y baja de objetos perdidos."""

import uuid

from app.auth import AuthenticatedUser
from app.errors import ApiError
from app.models import InventoryItem, LostObjectOut
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
        if obj.claimed_by is not None or obj.delivered:
            raise ApiError(
                409,
                "OBJECT_ALREADY_CLAIMED",
                "No se puede borrar un objeto que ya fue reclamado.",
            )
        del store.objects[object_id]


def _inventory_item(obj: LostObject) -> InventoryItem:
    status = "available"
    if obj.delivered:
        status = "delivered"
    elif obj.claimed_by is not None:
        status = "claimed"
    return InventoryItem(
        id=obj.id, name=obj.name, description=obj.description, status=status
    )


def list_inventory(store: ClaimStore) -> list[InventoryItem]:
    with store.lock:
        return [_inventory_item(obj) for obj in reversed(list(store.objects.values()))]


def mark_delivered(store: ClaimStore, object_id: str) -> InventoryItem:
    with store.lock:
        obj = store.objects.get(object_id)
        if obj is None:
            raise ApiError(404, "OBJECT_NOT_FOUND", "El objeto solicitado no existe.")
        obj.delivered = True
        return _inventory_item(obj)
