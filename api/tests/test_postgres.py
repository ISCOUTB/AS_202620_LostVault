import os

import pytest

from app.auth import AuthenticatedUser
from app.models import IntakeRequest
from app.objects import create_object, list_inventory, mark_delivered, review_claim
from app.service import create_claim
from app.store import PostgresClaimStore


@pytest.mark.skipif(not os.environ.get("LOSTVAULT_TEST_POSTGRES"), reason="requires test PostgreSQL")
def test_postgres_preserves_inventory_history_and_session_revocation():
    url = os.environ["LOSTVAULT_TEST_POSTGRES"]
    office = AuthenticatedUser("office-admin", "office@utb.edu.co", True)
    student = AuthenticatedUser("student-pg", "student@utb.edu.co")
    store = PostgresClaimStore(url)
    item = create_object(
        store, office, "Inventario persistente", None,
        intake=IntakeRequest(name="Inventario persistente", location="Estante B"),
    )
    assert create_claim(store, student, item.id, "persisted-claim").status_code == 201
    review_claim(store, item.id, office.id, True, "")
    mark_delivered(store, item.id, office.id)
    store.set_suspended(student.id, True)

    restarted = PostgresClaimStore(url)
    result = next(row for row in list_inventory(restarted) if row.id == item.id)
    assert result.location == "Estante B"
    assert result.status == "delivered"
    assert [event["action"] for event in result.history] == [
        "registrado", "reclamado", "aprobado", "entregado"
    ]
    assert restarted.user_session(student.id) == (True, 1)
    assert create_claim(restarted, student, item.id, "persisted-claim").replayed
