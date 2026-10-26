# Evidencia S13 — Aviso asíncrono `ClaimCreated` (outbox)

Decisión: [ADR 0007](../adr/0007-aviso-reclamacion-asincrono.md) · Contrato:
[`claim-created.asyncapi.yaml`](../contracts/claim-created.asyncapi.yaml) ·
Código: `backend/outbox.py`, enganche en `backend/main.py` (`create_claim`) ·
Pruebas: `backend/test_outbox.py`

## 1. Operación elegida y por qué

Aviso a la oficina de objetos perdidos tras una reclamación. Es la única operación del proyecto
con desacoplamiento temporal real: el estudiante necesita su 201 inmediato; la oficina tolera
minutos de retraso (C10); el proveedor de correo puede fallar sin invalidar la reclamación. La
reclamación misma **no** se hace asíncrona (ADR 0002).

## 2. Mapa requisito → evidencia

| # | Requisito | Dónde |
|---|---|---|
| 1 | Contrato y compatibilidad | AsyncAPI (reglas en `info.description`); `test_message_built_by_producer_matches_contract`, `test_consumer_tolerates_additional_fields_compatible_change`, `test_incompatible_message_goes_to_dead_letter_without_retries` (4 casos) |
| 2 | Garantía de entrega | Al menos una vez; ADR 0007 (tabla) y `eventos.md` §3 |
| 3 | Duplicados | `test_duplicate_delivery_has_a_single_effect`, `test_publisher_crash_between_send_and_mark_resends_but_effect_is_once`, `test_outbox_rejects_same_event_id_twice`, `test_http_replay_does_not_create_second_event` |
| 4 | Reintentos, backoff, DLQ | `Publisher.run_once`, `backoff_delay`; `test_recoverable_failure_is_retried_with_backoff_and_then_delivered`, `test_backoff_has_cap_and_jitter_bounds`, `test_exhausted_retries_move_message_to_dead_letter` |
| 5 | Duplicado + fallo recuperable | Las pruebas anteriores de 3 y 4; `test_claim_succeeds_even_if_notification_provider_is_down` prueba que el fallo no deshace la reclamación |
| 6 | Seguimiento productor→consumidor | `test_log_follows_message_from_request_to_consumer`, `test_metrics_expose_outbox_counters`; traza en §4 |
| 7 | ADR vs. síncrona | ADR 0007, sección «Alternativa síncrona considerada» |

## 3. Ejecución de pruebas

```text
$ cd backend && JWT_SECRET=... python -m pytest test_outbox.py -v
test_outbox.py::test_message_built_by_producer_matches_contract PASSED   [  5%]
test_outbox.py::test_event_id_is_deterministic_per_claim PASSED          [ 11%]
test_outbox.py::test_consumer_tolerates_additional_fields_compatible_change PASSED [ 16%]
test_outbox.py::test_incompatible_message_goes_to_dead_letter_without_retries[<lambda>0] PASSED [ 22%]
test_outbox.py::test_incompatible_message_goes_to_dead_letter_without_retries[<lambda>1] PASSED [ 27%]
test_outbox.py::test_incompatible_message_goes_to_dead_letter_without_retries[<lambda>2] PASSED [ 33%]
test_outbox.py::test_incompatible_message_goes_to_dead_letter_without_retries[<lambda>3] PASSED [ 38%]
test_outbox.py::test_duplicate_delivery_has_a_single_effect PASSED       [ 44%]
test_outbox.py::test_publisher_crash_between_send_and_mark_resends_but_effect_is_once PASSED [ 50%]
test_outbox.py::test_outbox_rejects_same_event_id_twice PASSED           [ 55%]
test_outbox.py::test_http_replay_does_not_create_second_event PASSED     [ 61%]
test_outbox.py::test_recoverable_failure_is_retried_with_backoff_and_then_delivered PASSED [ 66%]
test_outbox.py::test_backoff_has_cap_and_jitter_bounds PASSED            [ 72%]
test_outbox.py::test_exhausted_retries_move_message_to_dead_letter PASSED [ 77%]
test_outbox.py::test_failed_event_blocks_later_events_of_same_object_but_not_other_objects PASSED [ 83%]
test_outbox.py::test_claim_succeeds_even_if_notification_provider_is_down PASSED [ 88%]
test_outbox.py::test_log_follows_message_from_request_to_consumer PASSED [ 94%]
test_outbox.py::test_metrics_expose_outbox_counters PASSED               [100%]
======================== 18 passed, 1 warning in 0.32s =========================
```

Suite completa como en CI (desde la raíz): `pytest backend/test_api.py backend/test_outbox.py`
→ **45 passed** (27 previas + 18 nuevas); `outbox.py` 100 % de líneas cubiertas.

**Mutaciones (las pruebas detectan la regresión):**

| Cambio al código | Resultado |
|---|---|
| Desactivar la deduplicación del consumidor | 2 pruebas fallan (`..._single_effect`, `..._crash_between_send_and_mark...`) |
| Reintentar sin espera (sin backoff) | 1 prueba falla (`..._retried_with_backoff...`) |

## 4. Traza de un mensaje (corrida real, un fallo recuperable)

`X-Request-ID: req-demo-001` entra por HTTP y sale como `correlation_id` en cada etapa:

```text
{"time": "2026-10-26 03:32:05,119", "level": "INFO", "message": "startup", "event": "startup"}
{"time": "2026-10-26 03:32:05,121", "level": "INFO", "message": "claim_event_enqueued", "request_id": "req-demo-001", "event": "claim_event_enqueued", "event_id": "86f92620-8c6c-5ee1-afb5-388c2d9d31f3", "correlation_id": "req-demo-001"}
HTTP 201 {'objectId': 'obj-001', 'userId': 'student-42', 'verified': True}
{"time": "2026-10-26 03:32:05,123", "level": "WARNING", "message": "publisher_retry_scheduled", "event": "publisher_retry_scheduled", "event_id": "86f92620-8c6c-5ee1-afb5-388c2d9d31f3", "correlation_id": "req-demo-001", "attempt": 1, "retry_in_s": 35.4}
run_once #1 -> {'published': 0, 'retried': 1, 'dead_lettered': 0, 'skipped': 0}
{"time": "2026-10-26 03:32:05,123", "level": "INFO", "message": "office_notice_sent", "event": "office_notice_sent", "event_id": "86f92620-8c6c-5ee1-afb5-388c2d9d31f3", "correlation_id": "req-demo-001"}
{"time": "2026-10-26 03:32:05,123", "level": "INFO", "message": "consumer_processed", "event": "consumer_processed", "event_id": "86f92620-8c6c-5ee1-afb5-388c2d9d31f3", "correlation_id": "req-demo-001"}
{"time": "2026-10-26 03:32:05,123", "level": "INFO", "message": "publisher_published", "event": "publisher_published", "event_id": "86f92620-8c6c-5ee1-afb5-388c2d9d31f3", "correlation_id": "req-demo-001", "attempt": 2}
run_once #2 -> {'published': 1, 'retried': 0, 'dead_lettered': 0, 'skipped': 0}
metrics.outbox -> {'pending': 0, 'enqueued': 1, 'published': 1, 'retried': 1, 'dead_lettered': 0, 'duplicates_discarded': 0, 'oldest_pending_age_s': 0}
```

Lectura: `claim_event_enqueued` (productor, mismo 201) → `publisher_retry_scheduled` (intento 1 falla,
reintento en ~35 s = 30 s ±20 %) → `office_notice_sent` → `consumer_processed` →
`publisher_published` (intento 2). Para seguir un mensaje se filtra el log por `correlation_id` o
`event_id`. Métrica: `GET /metrics` → `outbox.{pending, enqueued, published, retried, dead_lettered,
duplicates_discarded, oldest_pending_age_s}`; `oldest_pending_age_s` es la que se compara con el
objetivo de ≤ 15 min.

## 5. Límites del experimento

- **Es un simulador en memoria**, no una cola durable. Si el proceso (o la instancia serverless) se
  reinicia, se pierden outbox y registro de procesados. Por tanto la garantía *al menos una vez*
  **solo está demostrada dentro de un proceso**; la durable requiere PostgreSQL con el evento en la
  misma transacción (ADR 0006, aún «Propuesto»).
- «Misma transacción» aquí es el mismo bloque `with _lock:`; no hay transacción real ni rollback.
- **No hay trabajo programado**: `run_once()` se invoca desde pruebas. Falta el cron (GitHub Actions
  o Vercel Cron) y un punto de entrada protegido; con varias instancias haría falta
  `FOR UPDATE SKIP LOCKED` para que dos publicadores no tomen el mismo evento.
- **El correo es simulado** (`_send_office_notice` solo escribe un log). Los fallos son inyectados,
  no medidos con un proveedor real; los tiempos de backoff se verificaron con reloj falso.
- El «exactamente una vez» es de *efecto* y solo mientras persista el registro de `eventId`;
  si el proveedor de correo no admite clave, un duplicado por caída entre enviar y marcar es posible.
- No se midió carga ni latencia; no se probó concurrencia entre publicadores.
- No hay alarma sobre la cola de fallidos: hoy se revisa a mano (`dead_letters()` / métrica).
- La app Flutter no participa: el cambio vive solo en `backend/`.
