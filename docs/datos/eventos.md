# Evidencia S12 — Flujo por eventos y sus garantías

> **Estado: diseñado, no implementado.** Hoy ninguna operación publica eventos
> (lo dice la [S11 §5](../fallos-parciales/s11-fallos-parciales.md)). Este flujo se
> implementa junto con PostgreSQL ([ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md)),
> porque el outbox necesita la misma transacción que la reclamación.

## 1. Para qué hay eventos

La reclamación es síncrona y atómica ([ADR 0002](../adr/0002-integracion-reclamacion-api.md)).
Lo que **no** necesita ocurrir dentro de ella son sus efectos secundarios:

- avisar a la oficina de objetos perdidos que hay una reclamación para entregar (C10);
- registrar para revisión los intentos bloqueados (Escenario 3, C9);
- en el futuro, purgar la caché tras publicar un objeto ([cache.md §3](cache.md)).

Si esos efectos fallan, la reclamación no debe deshacerse, y tampoco debe
perderse el aviso.

## 2. Flujo

```text
POST /claims ──▶ transacción local en PostgreSQL
                  ├─ UPDATE objects  (available → claimed)
                  ├─ INSERT claims
                  ├─ INSERT idempotency_keys
                  └─ INSERT outbox (ClaimCreated, event_id = claim.id)
                 COMMIT ──▶ 201 al estudiante

Publicador (cada 5–15 min) ──▶ SELECT … FROM outbox WHERE published_at IS NULL
                                ORDER BY aggregate_id, created_at
                                FOR UPDATE SKIP LOCKED
                            ──▶ envía el aviso (correo a la oficina)
                            ──▶ UPDATE outbox SET published_at = now()
```

| Evento | Productor | Consumidor | Contenido |
|---|---|---|---|
| `ClaimCreated` | `claims` | Notificador → oficina | `event_id`, `objectId`, `userId`, `occurredAt` |
| `ClaimRejected` | `claims` | Registro de revisión (Escenario 3) | `event_id`, `objectId`, `userId`, `reason` (`IDENTITY_NOT_VERIFIED`, …), `occurredAt` |
| `ClaimCancelled` | `claims` (solo si existe la saga de [ADR 0005](../adr/0005-no-extraer-verificacion-identidad.md)) | Notificador | `event_id`, `objectId`, `occurredAt` |

**Broker: ninguno por ahora.** La tabla `outbox` cumple el papel de cola. Kafka o
RabbitMQ agregarían un servicio permanente para un volumen de decenas de eventos
al día, y la plataforma es serverless ([ADR 0003](../adr/0003-plataforma-despliegue-vercel.md)).
El publicador es un trabajo programado: un workflow de GitHub Actions con
`schedule:` cada 15 minutos (gratis en repositorio público), o Vercel Cron si el
plan lo permite. Ese retraso es el que fija el "≤ 15 min" de C9 y C10.

## 3. Garantías declaradas

| Garantía | Qué se promete | Cómo se logra |
|---|---|---|
| **Entrega: al menos una vez** | Ningún `ClaimCreated` confirmado se pierde. | El evento se escribe en la **misma transacción** que la reclamación (no hay reclamación sin evento ni evento de algo deshecho). Se marca `published_at` **después** de que el envío se confirme. Si el publicador muere entre enviar y marcar, el evento se reenvía. |
| *A lo sumo una vez* (*at-most-once*) | **Descartado** | Marcar antes de enviar perdería avisos si el envío falla. Un aviso perdido es peor que uno repetido. |
| **"Exactamente una vez"** | **No se promete.** Lo que se logra es *efecto* exactamente una vez. | Al menos una vez + **consumidor idempotente**: `event_id` (= id de la reclamación) viaja como clave de idempotencia del envío; el consumidor guarda los `event_id` procesados y descarta los repetidos. Si el proveedor de correo no admite clave, la oficina puede recibir un aviso duplicado (aceptado). |
| **Orden: por objeto** | Para un mismo `objectId`, los eventos se procesan en el orden en que se confirmaron (`ClaimCreated` antes que `ClaimCancelled`). | `ORDER BY aggregate_id, created_at` y, si un evento de un objeto falla, el publicador no sigue con los siguientes de **ese** objeto en esa vuelta. |
| **Orden global** | **No se garantiza.** | No hace falta: los eventos de objetos distintos son independientes. |
| **Fallos persistentes** | Tras 5 intentos un evento pasa a `failed` (cola de mensajes fallidos dentro de la misma tabla) y aparece para revisión manual. | Columnas `attempts` y `failed_at` en `outbox`. |

## 4. Esquema propuesto

```sql
CREATE TABLE outbox (
  id            uuid PRIMARY KEY,           -- event_id
  aggregate_id  uuid NOT NULL,              -- objectId
  type          text NOT NULL,              -- ClaimCreated | ClaimRejected | ClaimCancelled
  payload       jsonb NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  published_at  timestamptz,
  attempts      int NOT NULL DEFAULT 0,
  failed_at     timestamptz
);
CREATE INDEX outbox_pending ON outbox (aggregate_id, created_at)
  WHERE published_at IS NULL AND failed_at IS NULL;
```
