"""Pruebas del aviso asíncrono ClaimCreated (ADR 0007).

Cubren: contrato y compatibilidad, duplicado, fallo recuperable con backoff,
cola de fallidos, orden por objeto, seguimiento por log y métrica.
El reloj es inyectado: ninguna prueba espera de verdad.
"""
import logging
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

import main
import outbox as ob
from test_api import auth  # reutiliza el generador de JWT del resto de pruebas

CONTRACT = Path(__file__).resolve().parents[1] / "docs" / "contracts" / "claim-created.asyncapi.yaml"


def contract_schema():
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return Draft202012Validator(spec["components"]["schemas"]["ClaimCreated"])


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def msg(object_id="obj-001", user_id="student-42", correlation="req-1", now=1_000_000.0):
    return ob.build_claim_created(
        {"objectId": object_id, "userId": user_id, "verified": True}, correlation, now
    )


class Harness:
    """Productor (outbox) + publicador + consumidor con envío simulado."""

    def __init__(self, script=None):
        self.clock = Clock()
        self.sent = []
        self.script = list(script or [])  # excepciones a lanzar, una por intento de envío
        self.outbox = ob.Outbox()

        def send(message):
            if self.script:
                outcome = self.script.pop(0)
                if outcome is not None:
                    raise outcome
            self.sent.append(message["eventId"])

        self.consumer = ob.OfficeNotifier(send=send)
        self.publisher = ob.Publisher(
            outbox=self.outbox, consumer=self.consumer, clock=self.clock, rng=lambda: 0.5
        )  # rng=0.5 => jitter 0, retrasos deterministas


@pytest.fixture(autouse=True)
def fresh_main_state():
    main._objects.clear()
    main._objects["obj-001"] = {
        "id": "obj-001", "title": "Termo negro",
        "description": "Encontrado cerca de la biblioteca.", "status": "available",
    }
    main._claims.clear()
    main._idempotency.clear()
    main._outbox.clear()
    main._notifier._processed.clear()
    main._publisher.counters = ob.Counters()


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


# 1. Contrato y compatibilidad -------------------------------------------------
def test_message_built_by_producer_matches_contract():
    contract_schema().validate(msg())


def test_event_id_is_deterministic_per_claim():
    assert msg()["eventId"] == msg(correlation="otro-request")["eventId"]
    assert msg()["eventId"] != msg(user_id="student-43")["eventId"]


def test_consumer_tolerates_additional_fields_compatible_change():
    h = Harness()
    m = msg()
    m["priority"] = "high"            # campo nuevo a nivel raíz
    m["data"]["building"] = "Bloque A"  # campo nuevo en data
    h.outbox.add(m)
    assert h.publisher.run_once()["published"] == 1
    assert h.sent == [m["eventId"]]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda m: m.pop("correlationId"),                 # quitar campo
        lambda m: m.update(schemaVersion=2),              # versión mayor desconocida
        lambda m: m["data"].pop("userId"),                # quitar campo anidado
        lambda m: m.update(type="ClaimCancelled"),        # tipo desconocido
    ],
)
def test_incompatible_message_goes_to_dead_letter_without_retries(mutate):
    h = Harness()
    m = msg()
    mutate(m)
    h.outbox.add(m)
    summary = h.publisher.run_once()
    assert summary["dead_lettered"] == 1 and summary["retried"] == 0
    row = h.publisher.dead_letters()[0]
    assert row.attempts == 1 and h.sent == []


# 2/3. Duplicados ------------------------------------------------------------
def test_duplicate_delivery_has_a_single_effect():
    h = Harness()
    m = msg()
    assert h.consumer.handle(m) == "processed"
    assert h.consumer.handle(m) == "duplicate"   # mismo eventId entregado dos veces
    assert h.sent == [m["eventId"]] and h.consumer.duplicates == 1


def test_publisher_crash_between_send_and_mark_resends_but_effect_is_once():
    """Escenario de 'al menos una vez': el aviso salió, pero published_at no se
    guardó. La vuelta siguiente reenvía; el consumidor descarta el duplicado."""
    h = Harness()
    m = msg()
    h.outbox.add(m)
    h.consumer.handle(m)                 # el consumidor procesó...
    assert h.outbox.rows()[0].pending    # ...pero el outbox sigue pendiente (crash simulado)
    h.publisher.run_once()
    assert h.sent == [m["eventId"]]      # un solo correo
    assert h.publisher.counters.duplicates_discarded == 1
    assert not h.outbox.rows()[0].pending


def test_outbox_rejects_same_event_id_twice():
    ob_ = ob.Outbox()
    assert ob_.add(msg()) is True
    assert ob_.add(msg()) is False


def test_http_replay_does_not_create_second_event(client):
    h = {**auth(), "Idempotency-Key": "k-1"}
    assert client.post("/v1/objects/obj-001/claims", headers=h).status_code == 201
    assert client.post("/v1/objects/obj-001/claims", headers=h).status_code == 201  # replay
    assert client.post("/v1/objects/obj-001/claims", headers=auth()).status_code == 200  # dedup
    assert len(main._outbox.rows()) == 1


# 4. Fallo recuperable, backoff y cola de fallidos ---------------------------------
def test_recoverable_failure_is_retried_with_backoff_and_then_delivered():
    h = Harness(script=[ob.TransientError("smtp 503"), ob.TransientError("smtp 503"), None])
    m = msg()
    h.outbox.add(m)

    assert h.publisher.run_once()["retried"] == 1            # intento 1 falla
    row = h.outbox.rows()[0]
    assert row.next_attempt_at - h.clock() == pytest.approx(30)

    assert h.publisher.run_once()["skipped"] == 1             # aún no toca: no se reintenta
    assert row.attempts == 1

    h.clock.advance(30)
    assert h.publisher.run_once()["retried"] == 1             # intento 2 falla
    assert row.next_attempt_at - h.clock() == pytest.approx(60)  # retroceso exponencial

    h.clock.advance(60)
    assert h.publisher.run_once()["published"] == 1           # intento 3 funciona
    assert row.attempts == 3 and row.published_at is not None
    assert h.sent == [m["eventId"]]                           # un solo envío efectivo


def test_backoff_has_cap_and_jitter_bounds():
    assert ob.backoff_delay(1, rng=lambda: 0.5) == pytest.approx(30)
    assert ob.backoff_delay(4, rng=lambda: 0.5) == pytest.approx(240)
    assert ob.backoff_delay(9, rng=lambda: 0.5) == pytest.approx(900)  # tope
    assert ob.backoff_delay(1, rng=lambda: 0.0) == pytest.approx(24)   # -20 %
    assert ob.backoff_delay(1, rng=lambda: 1.0) == pytest.approx(36)   # +20 %


def test_exhausted_retries_move_message_to_dead_letter():
    h = Harness(script=[ob.TransientError("smtp caído")] * ob.MAX_ATTEMPTS)
    h.outbox.add(msg())
    for _ in range(ob.MAX_ATTEMPTS):
        h.publisher.run_once()
        h.clock.advance(ob.MAX_DELAY_SECONDS * 2)
    dead = h.publisher.dead_letters()
    assert len(dead) == 1 and dead[0].attempts == ob.MAX_ATTEMPTS
    assert "agotó" in dead[0].last_error
    assert h.publisher.counters.dead_lettered == 1
    h.publisher.run_once()                # una vuelta más no lo reintenta
    assert dead[0].attempts == ob.MAX_ATTEMPTS


def test_failed_event_blocks_later_events_of_same_object_but_not_other_objects():
    h = Harness(script=[ob.TransientError("smtp 503")])
    first = msg(object_id="obj-A", user_id="u1", now=1.0)
    second = msg(object_id="obj-A", user_id="u2", now=2.0)
    other = msg(object_id="obj-B", user_id="u3", now=3.0)
    for m in (first, second, other):
        h.outbox.add(m)
    summary = h.publisher.run_once()
    assert summary["retried"] == 1 and summary["published"] == 1
    assert h.sent == [other["eventId"]]          # obj-B pasó; obj-A espera su turno
    h.clock.advance(30)
    h.publisher.run_once()
    # obj-A se entrega completo y en orden: primero el que había fallado, luego el siguiente
    assert h.sent == [other["eventId"], first["eventId"], second["eventId"]]


# 5. El fallo de la notificación NO deshace la reclamación -----------------------
def test_claim_succeeds_even_if_notification_provider_is_down(client, monkeypatch):
    def broken(_message):
        raise ob.TransientError("smtp caído")

    monkeypatch.setattr(main, "_send_office_notice", broken)
    r = client.post("/v1/objects/obj-001/claims", headers=auth())
    assert r.status_code == 201                              # la reclamación no depende del correo
    assert main._objects["obj-001"]["status"] == "claimed"
    main._publisher.run_once()
    assert main._publisher.counters.retried == 1
    monkeypatch.undo()                                       # el proveedor se recupera
    row = main._outbox.rows()[0]
    row.next_attempt_at = 0                                  # "pasaron los 30 s"
    assert main._publisher.run_once()["published"] == 1
    assert main._notifier.sent == 1


# 6. Seguimiento de productor a consumidor: log y métrica -----------------------------
def test_log_follows_message_from_request_to_consumer(client, caplog):
    caplog.set_level(logging.INFO, logger="lostvault")
    r = client.post(
        "/v1/objects/obj-001/claims", headers={**auth(), "X-Request-ID": "req-trace-1"}
    )
    assert r.status_code == 201
    main._publisher.run_once()
    traced = [
        rec.event for rec in caplog.records
        if getattr(rec, "correlation_id", None) == "req-trace-1"
    ]
    assert traced == [
        "claim_event_enqueued", "office_notice_sent", "consumer_processed", "publisher_published",
    ]
    event_ids = {
        rec.event_id for rec in caplog.records if getattr(rec, "correlation_id", None) == "req-trace-1"
    }
    assert len(event_ids) == 1


def test_metrics_expose_outbox_counters(client):
    client.post("/v1/objects/obj-001/claims", headers=auth())
    before = client.get("/metrics").json()["outbox"]
    assert before["pending"] == 1 and before["enqueued"] == 1 and before["published"] == 0
    main._publisher.run_once()
    after = client.get("/metrics").json()["outbox"]
    assert after["pending"] == 0 and after["published"] == 1 and after["dead_lettered"] == 0
