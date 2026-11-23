"""Alta y baja de objetos perdidos."""

import uuid

from app.auth import AuthenticatedUser
from app.errors import ApiError
from app.models import IntakeRequest, InventoryItem, LostObjectOut
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
    *,
    intake: IntakeRequest | None = None,
) -> LostObjectOut | InventoryItem:
    name = name.strip()
    if not name:
        raise ApiError(422, "VALIDATION_ERROR", "name: no puede estar vacío.")
    description = description.strip() if description else None
    with store.transaction():
        obj = LostObject(
            id=uuid.uuid4().hex,
            name=name,
            description=description or None,
            reported_by=user.id,
            found_at=intake.foundAt if intake else None,
            location=intake.location if intake else None,
            photo_url=str(intake.photoUrl) if intake and intake.photoUrl else None,
        )
        obj.record("registrado", user.id, store.clock())
        obj.received_at = obj.history[-1]["at"] if intake else None
        store.objects[obj.id] = obj
        return _inventory_item(obj) if intake else _to_out(obj)


def delete_object(store: ClaimStore, user: AuthenticatedUser, object_id: str) -> None:
    with store.transaction():
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
    elif obj.approved:
        status = "approved"
    elif obj.claimed_by is not None:
        status = "claimed"
    return InventoryItem(
        id=obj.id, name=obj.name, description=obj.description, status=status,
        claimedBy=obj.claimed_by, foundAt=obj.found_at, location=obj.location,
        photoUrl=obj.photo_url, receivedAt=obj.received_at, history=obj.history.copy(),
    )


def list_inventory(store: ClaimStore) -> list[InventoryItem]:
    with store.transaction():
        return [_inventory_item(obj) for obj in reversed(list(store.objects.values()))]


def mark_delivered(store: ClaimStore, object_id: str, actor: str) -> InventoryItem:
    with store.transaction():
        obj = store.objects.get(object_id)
        if obj is None:
            raise ApiError(404, "OBJECT_NOT_FOUND", "El objeto solicitado no existe.")
        if not obj.delivered:
            if not obj.approved:
                raise ApiError(409, "FORBIDDEN", "Aprueba la reclamación antes de entregar.")
            obj.delivered = True
            obj.record("entregado", actor, store.clock())
        return _inventory_item(obj)


def review_claim(
    store: ClaimStore, object_id: str, actor: str, approve: bool, reason: str
) -> InventoryItem:
    with store.transaction():
        obj = store.objects.get(object_id)
        if obj is None:
            raise ApiError(404, "OBJECT_NOT_FOUND", "El objeto solicitado no existe.")
        if obj.claimed_by is None or obj.approved or obj.delivered:
            raise ApiError(409, "FORBIDDEN", "El objeto no tiene una reclamación pendiente.")
        if approve:
            obj.approved = True
        else:
            if not reason.strip():
                raise ApiError(422, "VALIDATION_ERROR", "Indica el motivo del rechazo.")
            obj.claimed_by = None
            store.idempotency = {
                key: entry for key, entry in store.idempotency.items() if entry[0] != object_id
            }
        obj.record("aprobado" if approve else "rechazado", actor, store.clock(), reason.strip())
        return _inventory_item(obj)
