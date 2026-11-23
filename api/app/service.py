"""Lógica de reclamación de objetos (operación createClaim del contrato)."""

from dataclasses import dataclass

from app.auth import AuthenticatedUser
from app.errors import ApiError
from app.identity import is_identity_verified
from app.models import Claim
from app.store import ClaimStore

IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60  # vigencia de 24 h por usuario
IDEMPOTENCY_KEY_MAX_LENGTH = 255


@dataclass(frozen=True)
class ClaimOutcome:
    claim: Claim
    status_code: int
    replayed: bool


def validate_idempotency_key(key: str | None) -> None:
    if key is None:
        return
    if not key.strip() or len(key) > IDEMPOTENCY_KEY_MAX_LENGTH:
        raise ApiError(
            400,
            "INVALID_IDEMPOTENCY_KEY",
            "La cabecera Idempotency-Key debe tener entre 1 y 255 caracteres.",
        )


def create_claim(
    store: ClaimStore,
    user: AuthenticatedUser,
    object_id: str,
    idempotency_key: str | None,
) -> ClaimOutcome:
    validate_idempotency_key(idempotency_key)

    with store.lock:
        now = store.clock()
        store.purge_expired_keys(now)

        lost_object = store.objects.get(object_id)
        if lost_object is None:
            raise ApiError(404, "OBJECT_NOT_FOUND", "El objeto solicitado no existe.")

        claim = Claim(objectId=object_id, userId=user.id)

        if idempotency_key is not None:
            entry = store.idempotency.get((user.id, idempotency_key))
            if entry is not None:
                previous_object_id, _ = entry
                if previous_object_id != object_id:
                    raise ApiError(
                        422,
                        "IDEMPOTENCY_KEY_REUSED",
                        "La Idempotency-Key ya se usó para reclamar otro objeto.",
                    )
                return ClaimOutcome(claim=claim, status_code=201, replayed=True)

        if lost_object.claimed_by is not None:
            if lost_object.claimed_by == user.id:
                return ClaimOutcome(claim=claim, status_code=200, replayed=False)
            raise ApiError(409, "OBJECT_ALREADY_CLAIMED", "El objeto ya fue reclamado.")

        if lost_object.delivered:
            raise ApiError(409, "OBJECT_ALREADY_CLAIMED", "El objeto ya fue entregado.")

        if not is_identity_verified(user):
            raise ApiError(
                422,
                "IDENTITY_NOT_VERIFIED",
                "No se pudo verificar la identidad del usuario.",
            )

        lost_object.claimed_by = user.id
        if idempotency_key is not None:
            store.idempotency[(user.id, idempotency_key)] = (
                object_id,
                now + IDEMPOTENCY_TTL_SECONDS,
            )
        return ClaimOutcome(claim=claim, status_code=201, replayed=False)
