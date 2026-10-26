# ADR 0007: Aviso a la oficina por evento asíncrono (outbox) en lugar de llamada síncrona

- **Estado**: Aceptado (simulador en memoria; el almacén durable depende del [ADR 0006](0006-postgresql-fuente-de-verdad.md))
- **Fecha**: 2026-10-25
- **Decisores**: Equipo LostVault
- **Contrato**: [`../contracts/claim-created.asyncapi.yaml`](../contracts/claim-created.asyncapi.yaml) v1.0.0
- **Relacionado**: [ADR 0002](0002-integracion-reclamacion-api.md) (la reclamación sigue síncrona),
  [eventos.md](../datos/eventos.md), [S11](../fallos-parciales/s11-fallos-parciales.md)

## Contexto

Al crearse una reclamación (`POST /v1/objects/{id}/claims`, 201) la oficina de objetos perdidos
debe enterarse para preparar la entrega (C10). El ADR 0002 ya anticipó que los efectos
secundarios no críticos podían ir por eventos. Esa es la única operación del proyecto con
**desacoplamiento temporal real**: el estudiante necesita su 201 ya, la oficina puede enterarse
minutos después, y el proveedor de correo puede estar caído sin que eso invalide la reclamación.

## Decisión

Al confirmar la reclamación, el backend escribe un mensaje `ClaimCreated` en un **outbox** dentro
del mismo bloque crítico (`with _lock:`) que la reclamación. Un **publicador** (`Publisher.run_once`,
pensado para un trabajo programado cada 5–15 min) lo entrega a un **consumidor idempotente**
(`OfficeNotifier`) que avisa a la oficina.

| Aspecto | Elección | Consecuencia asumida |
|---|---|---|
| Contrato | AsyncAPI 3.0, `schemaVersion` entero; campos nuevos opcionales = compatible; quitar/renombrar/cambiar tipo = nueva versión | El consumidor ignora campos desconocidos y manda a la cola de fallidos una versión mayor |
| Entrega | **Al menos una vez** | Puede haber un aviso repetido si el proceso muere entre enviar y marcar `published_at`; se acepta (peor es perderlo) |
| Duplicados | `eventId` = UUIDv5(objeto+usuario) + consumidor que guarda `eventId` procesados + `PRIMARY KEY` en outbox | Efecto exactamente una vez **solo mientras** el registro de procesados persista (hoy en memoria) |
| Reintentos | Hasta 5 intentos, espera 30 s·2ⁿ⁻¹ ±20 %, tope 900 s; solo ante `TransientError` | El aviso puede llegar con hasta ~15 min más de retraso (alineado con C9/C10) |
| Fallidos | A los 5 intentos o ante `PermanentError` → `failed_at` (DLQ en la misma tabla) | Requiere revisión manual; no hay alarma automática aún |
| Orden | Por `objectId`; un evento fallido frena los siguientes del mismo objeto | Sin orden global |
| Seguimiento | `correlationId` = `X-Request-ID` de la petición; logs JSON `claim_event_enqueued → office_notice_sent → consumer_processed → publisher_published` con `event_id`; `/metrics` → `outbox` | |

**Broker: ninguno.** El outbox cumple el papel de cola (ver eventos.md §2). No se justifica
RabbitMQ/Kafka para decenas de eventos al día en una plataforma serverless.

## Alternativa síncrona considerada

`create_claim` llama directamente al proveedor de correo antes de responder 201.

| Criterio | Síncrona | Outbox asíncrono (elegida) |
|---|---|---|
| Latencia del 201 | Suma la del correo (frío + SMTP) | Sin cambio |
| Correo caído | Hay que elegir: fallar la reclamación (inaceptable: el objeto no se reservaría por un problema ajeno) o ignorar el fallo (aviso perdido sin rastro) | La reclamación se confirma; el aviso se reintenta y, si no sale, queda en DLQ visible |
| Atomicidad reclamación + aviso | No hay: puede reclamarse sin avisar o avisar de algo que se revirtió | El evento nace en el mismo bloque que la reclamación |
| Retraso del aviso | Inmediato | Hasta ~15 min (backoff / periodo del publicador) |
| Complejidad | Mínima | Contrato, outbox, publicador, idempotencia, DLQ, pruebas |
| Depuración | Una traza | Hay que seguir `correlationId` entre dos fases |
| Consistencia visible | Oficina y estudiante coinciden al instante | Ventana de consistencia eventual de minutos |

Se prefiere la asíncrona porque la oficina **tolera** el retraso (C10 ≤ 15 min) y el estudiante
**no tolera** que su reclamación dependa del correo. Si la oficina exigiera aviso inmediato, la
síncrona con tiempo límite sería mejor y este ADR se revisaría.

## Lo que NO se vuelve asíncrono

La reclamación misma (ADR 0002): requiere respuesta inmediata para que dos estudiantes no
crean haber reclamado el mismo objeto.

## Evidencia

`backend/test_outbox.py` (18 pruebas) y `docs/fallos-parciales/s12-outbox-evidencia.md`.
