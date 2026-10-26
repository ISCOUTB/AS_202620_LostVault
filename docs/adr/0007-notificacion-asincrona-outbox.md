# ADR 0007: Notificar las reclamaciones por mensajes (outbox) y no con una llamada síncrona

- **Estado**: Propuesto
- **Fecha**: 2026-10-25
- **Decisores**: Equipo LostVault
- **Relacionado**: [ADR 0002](0002-integracion-reclamacion-api.md) (reclamación síncrona),
  [ADR 0006](0006-postgresql-fuente-de-verdad.md) (PostgreSQL),
  [eventos.md](../datos/eventos.md), [Taller de mensajería](../mensajeria/taller-mensajeria.md),
  [Evidencia S11](../fallos-parciales/s11-fallos-parciales.md)

## Contexto

Cuando un estudiante reclama un objeto, la oficina de objetos perdidos debe
enterarse para preparar la entrega, y cuando se bloquea un intento, debe quedar
para revisión (Escenario 3: "marca el intento para revisión"). Hoy no existe
ningún aviso.

La reclamación en sí es síncrona y debe confirmarse al instante
([ADR 0002](0002-integracion-reclamacion-api.md)). La pregunta es cómo hacer el
**aviso**: dentro de la misma petición o fuera de ella.

## Opciones

### A. Síncrona: `POST /claims` llama al servicio de correo antes de responder

```text
POST /claims → verificar → reservar objeto → COMMIT → enviar correo → 201
```

### B. Asíncrona con outbox (elegida)

```text
POST /claims → verificar → reservar objeto + INSERT outbox → COMMIT → 201
Despachador (periódico) → outbox → consumidor idempotente → aviso
```

## Comparación

| Criterio | A. Síncrona | B. Outbox (asíncrona) |
|---|---|---|
| **Disponibilidad de la reclamación** (Escenario 1) | Depende del correo: si el correo cae, o se rechaza la reclamación o se responde `201` sin aviso. La disponibilidad es el producto de las dos. | No depende del correo. Si cae, los avisos esperan en el outbox y se reintentan. |
| **Latencia de `POST /claims`** | Suma la llamada al correo (cientos de ms a segundos), con timeout. Sobre un arranque en frío de Vercel acerca el p95 al límite. | Solo un `INSERT` más dentro de la transacción existente. |
| **Consistencia reclamación ↔ aviso** | Hay dos sistemas sin transacción común. Si el `COMMIT` funciona y el correo falla, queda una reclamación sin aviso; si el correo sale y luego el `COMMIT` falla, hay aviso de algo que no ocurrió. | Evento y reclamación en la **misma transacción**: o ambos o ninguno. |
| **Duplicados** | Un reintento del cliente (S11, F2) podría reenviar el correo; habría que deduplicar igual. | Previstos y resueltos: consumidor idempotente por `event_id`. |
| **Inmediatez del aviso** | Inmediato. | Retrasado hasta la siguiente vuelta del despachador (≤ 15 min). |
| **Complejidad** | Baja: una llamada HTTP más. | Mayor: tabla outbox, despachador programado, reintentos, cola de fallidos, consumidor idempotente. |
| **Observabilidad** | Un log en la petición. | Requiere seguir el mensaje entre componentes: `correlation_id` en cada etapa. |

## Decisión

**Opción B: outbox + despachador + consumidor idempotente**, con entrega al
menos una vez, reintentos con backoff exponencial y jitter (5 intentos) y cola
de fallidos con reprocesamiento manual. Implementado y verificado como
simulador local en `mensajeria/` ([taller](../mensajeria/taller-mensajeria.md)).

El factor decisivo es la **consistencia**: con la opción A no hay forma de que
la reclamación y el aviso queden de acuerdo sin una transacción distribuida, y
el aviso es justo lo que permite a la oficina entregar el objeto correcto. El
retraso de hasta 15 minutos es aceptable porque la entrega física ocurre en
horario de oficina, horas después.

## Consecuencias

**Positivas**
- La reclamación no pierde disponibilidad ni latencia por el correo.
- Ningún aviso se pierde ni se refiere a una reclamación que no existe.
- Queda la base para otros efectos asíncronos (purga de caché, auditoría).

**Negativas**
- Aviso no inmediato; la UI debe decir "la oficina será notificada", no "notificada".
- Más piezas que operar: el despachador programado y la revisión de fallidos.
- La garantía completa depende de PostgreSQL (ADR 0006); hasta entonces solo
  existe en el simulador.

## Cuándo revisar

- Si la oficina necesita el aviso en segundos (p. ej. entregas en el momento),
  reducir el periodo del despachador o pasar a un broker con push; la opción A
  sigue descartada por la consistencia.
- Si el volumen crece a miles de eventos por hora o aparecen varios
  consumidores, evaluar un broker gestionado (cola SQS / Pub/Sub) alimentado por
  el mismo outbox.
