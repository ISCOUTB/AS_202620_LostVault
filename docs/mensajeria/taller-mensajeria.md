# Taller — Sistemas de Mensajes (LostVault)

Implementa como **simulador local ejecutable** el flujo por eventos que la
Evidencia S12 dejó diseñado en [`docs/datos/eventos.md`](../datos/eventos.md):
cuando se reclama un objeto, la oficina recibe un aviso, y cuando se bloquea un
intento, queda registrado para revisión (Escenario 3).

```text
reclamar() ─┬─ UPDATE objects / INSERT claims ─┐
            └─ INSERT outbox (evento) ─────────┴─ una transacción (productor.py)
                          │
                 Despachador (despachador.py) ── reintentos + backoff ──▶ fallidos
                          │
                 Notificador (consumidor.py) ── dedup por event_id ──▶ avisos
```

| Pieza | Archivo |
|---|---|
| Contrato | [`docs/contracts/claim-events.v1.schema.json`](../contracts/claim-events.v1.schema.json), `mensajeria/contrato.py` |
| Productor (outbox) | `mensajeria/productor.py` |
| Despachador (reintentos, fallidos, orden) | `mensajeria/despachador.py` |
| Consumidor idempotente | `mensajeria/consumidor.py` |
| Logs y métricas | `mensajeria/trazas.py` |
| Pruebas (18) | `mensajeria/tests/test_mensajeria.py` |
| Demo / evidencia | `mensajeria/demo.py`, [`evidencia-ejecucion.md`](evidencia-ejecucion.md) |
| ADR | [ADR 0007](../adr/0007-notificacion-asincrona-outbox.md) |

**Tecnología:** Python + SQLite (biblioteca estándar). La tabla `outbox` del
productor hace de cola; no hay broker. Se eligió así porque SQLite da
transacciones reales, que es lo que hace verificable la propiedad central
(evento atómico con la reclamación), y es el mismo diseño que tendrá PostgreSQL
([ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md)).

## 1. Contrato del mensaje y criterio de compatibilidad

Sobre común para todos los eventos (`event_id`, `type`, `schema_version`,
`occurred_at`, `correlation_id`, `aggregate_id`) y cuerpo en `data`. Tipos:
`ClaimCreated` y `ClaimRejected` (este exige `data.reason`). El productor valida
cada evento antes de encolarlo y el consumidor lo valida al recibirlo.

**Criterio de compatibilidad:**

| Cambio | ¿Compatible? | Qué se hace |
|---|---|---|
| Agregar un campo **opcional** (en el sobre o en `data`) | Sí | Mismo `schema_version`. El consumidor **ignora lo que no conoce** (`additionalProperties: true`). Probado: `test_consumidor_acepta_campos_nuevos_opcionales`. |
| Agregar un tipo de evento nuevo | Sí, para consumidores que lo filtren | Se agrega al `enum`; consumidores viejos lo mandan a fallidos sin perderlo. |
| Quitar o renombrar un campo obligatorio, cambiar su tipo o su significado | **No** | Nuevo `schema_version: 2` y nuevo archivo de esquema; el productor publica v1 y v2 en paralelo hasta que todos los consumidores migren. |

Los cambios incompatibles se detectan en CI: `test_cambios_incompatibles_violan_el_contrato`
(quitar `event_id`, quitar `userId`, cambiar la versión, tipo desconocido).

## 2. Garantía de entrega: al menos una vez

- El evento se escribe en la **misma transacción** que la reclamación: o quedan
  los dos o ninguno (`test_si_la_transaccion_falla_no_queda_ni_reclamacion_ni_evento`).
- El despachador marca `publicado` **solo después** de que el consumidor
  confirma. Si se cae entre entregar y marcar, reenvía.

**Consecuencias asumidas:**

- El consumidor **va a recibir duplicados** y debe ser idempotente (§3).
- El aviso **no es inmediato**: llega en la siguiente vuelta del despachador
  (en producción, ≤ 15 min, operación C10 de
  [consistencia.md](../datos/consistencia.md)).
- Un mensaje puede quedar en fallidos y requerir intervención (§4).
- *A lo sumo una vez* se descartó: marcar antes de entregar pierde avisos si el
  envío falla. "Exactamente una vez" no se promete: lo que se logra es **efecto
  una sola vez** = al menos una vez + deduplicación.

## 3. Duplicados: consumidor idempotente

El consumidor guarda cada `event_id` en `eventos_procesados` **en la misma
transacción** que el aviso. Si el `event_id` ya existe, registra
`duplicado_ignorado` y no repite el efecto. Si el destino falla, la transacción
se deshace y el evento no queda marcado, así que el reintento sí se procesa.

Pruebas: `test_duplicado_por_caida_tras_entregar_produce_un_solo_aviso` (el
duplicado real que produce el diseño) y
`test_mismo_mensaje_recibido_dos_veces_se_ignora_la_segunda`.

## 4. Reintentos, backoff y cola de fallidos

| Regla | Valor |
|---|---|
| Qué se reintenta | Cualquier fallo del consumidor **salvo** contrato inválido. |
| Backoff | Exponencial: techo = `base · 2^(intento−1)`, máximo `tope`. Espera = mitad del techo + aleatorio hasta el techo (*jitter*), para que los reintentos de muchos mensajes no coincidan. |
| Máximo | 5 intentos → estado `fallido` (cola de fallidos dentro del outbox). |
| Mensaje fuera de contrato | A fallidos en el **primer** intento: reintentar no lo arregla. |
| Orden | Por objeto: si un evento espera reintento, los siguientes **del mismo objeto** esperan; los de otros objetos siguen. |
| Recuperación | `Despachador.fallidos()` lista; `reprocesar(event_id)` lo devuelve a la cola cuando se corrige la causa. |

Parámetros: en el simulador `base = 1 s`, `tope = 60 s`. En producción el
despachador corre cada 15 min, así que un reintento ocurre en la primera vuelta
posterior a `proximo_intento`; con `base = 15 min` y `tope = 2 h` un mensaje
agota sus 5 intentos en unas 4 horas, dentro de la jornada de la oficina.

Pruebas: `test_fallo_recuperable_se_reintenta_con_backoff_y_se_entrega_una_vez`
(falla dos veces, no reintenta antes de tiempo, se entrega una vez),
`test_backoff_exponencial_con_tope_y_jitter`,
`test_tras_max_intentos_va_a_fallidos_y_no_se_reintenta` (incluye el
reprocesamiento), `test_mensaje_fuera_de_contrato_va_a_fallidos_sin_reintentar`,
`test_orden_por_objeto_se_respeta_y_otros_objetos_no_se_bloquean`.

## 5. Pruebas automatizadas

18 pruebas en `mensajeria/tests/test_mensajeria.py`, ejecutadas en CI (paso
*Messaging workshop tests* de `.github/workflows/backend.yml`). El tiempo se
controla con un reloj falso, así que son deterministas y tardan segundos.
Resultado en [evidencia-ejecucion.md](evidencia-ejecucion.md).

## 6. Seguimiento de un mensaje de productor a consumidor

Cada componente emite una línea JSON por etapa con `event_id`,
`correlation_id`, `type`, `aggregate_id` y `componente`. El `correlation_id`
es el `X-Request-ID` de la petición HTTP que originó la reclamación (el
middleware de `backend/main.py` ya lo genera), así que un mismo identificador
une el log de la API con el del consumidor.

Etapas: `producido` → `despachado` → `recibido` → `entregado` →
`confirmado_en_outbox`, más `reintento_programado`, `duplicado_ignorado` y
`enviado_a_fallidos`. El contador `metricas` acumula cuántas veces ocurre cada
etapa (la demo lo imprime al final).

Prueba: `test_un_mensaje_se_puede_seguir_por_correlation_id` exige la
secuencia completa, un solo `event_id` y los tres componentes.

## 7. ADR

[ADR 0007](../adr/0007-notificacion-asincrona-outbox.md): notificación
asíncrona con outbox frente a llamar al servicio de correo de forma síncrona
dentro de `POST /claims`.

## Límites del experimento

- **Es un simulador en un solo proceso.** Productor, despachador y consumidor son
  objetos en el mismo programa; no hay red entre ellos. Las caídas y fallos se
  **inyectan** (ganchos `antes_de_confirmar`, `caer_tras_entregar`, transporte que
  falla), no se provocan matando procesos.
- **No está conectado a la API desplegada.** `backend/main.py` sigue guardando en
  memoria y no escribe en el outbox; conectarlo depende de PostgreSQL (ADR 0006).
- **SQLite en vez de PostgreSQL.** La transacción y la deduplicación son reales,
  pero no se prueba concurrencia entre varios despachadores. En PostgreSQL se
  usaría `FOR UPDATE SKIP LOCKED`; aquí hay un solo despachador.
- **El efecto es una fila en la base del consumidor.** Por eso es exactamente una
  vez. Con un correo real, si el envío funciona y el proceso muere antes del
  COMMIT, se enviaría dos veces; la mitigación (pasar `event_id` como clave de
  idempotencia al proveedor) depende de que el proveedor la admita.
- **Sin carga ni volumen.** No se midió rendimiento; el volumen esperado es de
  decenas de eventos al día.
- **El tiempo es simulado.** El backoff se verifica con un reloj falso; no se
  midieron las esperas reales de un publicador programado cada 15 min.
