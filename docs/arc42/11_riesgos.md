# 11. Riesgos y deuda técnica

Registro de riesgos técnicos vigentes. Los riesgos R1–R5 provienen del análisis
de fallos parciales de la integración `POST /v1/objects/{objectId}/claims`
(Evidencia S11); el detalle de cada modo de fallo (F1–F7) y su mitigación está en
[`../fallos-parciales/s11-fallos-parciales.md`](../fallos-parciales/s11-fallos-parciales.md).

Probabilidad e impacto: A = alto, M = medio, B = bajo.

| ID | Riesgo | Modos de fallo | Prob. | Impacto | Mitigación | Estado |
|---|---|---|---|---|---|---|
| R1 | Dos instancias serverless aceptan la reclamación del mismo objeto, porque el candado y el estado son por proceso. | F6 | M | A (entrega indebida, Escenario 3) | PostgreSQL con `UNIQUE(object_id)` en `claims` y claves de idempotencia en tabla; reserva + clave en una transacción local ([ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md)). | **Abierto / aceptado.** Solución decidida en S12. Bloqueado por la falta de base de datos ([§7](07_vista_despliegue.md)). Con el tráfico actual del curso la probabilidad real es baja. |
| R2 | Un reintento tras una respuesta tardía le informa al dueño que su objeto lo reclamó otra persona. | F2, F3 | A (arranques en frío frecuentes) | M | `Idempotency-Key` + deduplicación por usuario en el proveedor. | **Mitigado** en `backend/main.py`, con pruebas en `backend/test_api.py`. |
| R3 | La UI queda esperando sin límite cuando la API no responde. | F1, F5 | M | M (Escenario 2 de usabilidad) | Timeout de 5 s y circuit breaker (5 fallos → abierto 30 s) en el adaptador HTTP del cliente. | **Abierto.** Se implementa junto con el adaptador HTTP de Flutter (hoy los adaptadores son in-memory). |
| R4 | Reintentos inmediatos de muchos clientes prolongan una caída. | F4 | B | M | Backoff exponencial con jitter, máximo 3 intentos, solo ante errores técnicos (nunca ante `4xx`). | **Abierto**, mismo bloqueo que R3. El reintento ya es seguro en el servidor (R2). |
| R5 | Un cliente reutiliza una clave de idempotencia para otro objeto y recibe una respuesta ajena. | F7 | B | M | Clave ligada a `objectId` → `422 IDEMPOTENCY_KEY_REUSED`; clave inválida → `400`. | **Mitigado**, con pruebas. |
| R6 | Extraer un módulo a servicio antes de tiempo convierte la reclamación en una transacción distribuida (saga, estado pendiente, más modos de fallo). | — | B | A | Se decide **no extraer** por ahora, con disparadores de revisión explícitos. | **Decidido** en [ADR 0005](../adr/0005-no-extraer-verificacion-identidad.md). |
| R7 | Las métricas `p95` en memoria no acumulan entre invocaciones de la función. | — | A | B | Almacén compartido (Vercel KV / Upstash) o agregación desde los logs estructurados. | **Abierto**, documentado en [§7](07_vista_despliegue.md). |
| R8 | Un estudiante ve como "Disponible" un objeto ya reclamado (listado cacheado hasta 90 s) y recibe `409` al reclamarlo. | — | M | B (Escenario 2) | Consistencia eventual acotada y aceptada: la reclamación revalida contra la fuente de verdad; mensaje claro en el `409`. Purga explícita si la prueba de usabilidad lo exige. | **Aceptado** en S12 ([cache.md](../datos/cache.md)). |
| R9 | Con PostgreSQL en el camino crítico, una caída de la BD impide reclamar. | — | B | M | Se prefiere fallar (`503`) a entregar mal (consistencia sobre disponibilidad en C1). El listado sigue sirviéndose desde la CDN hasta 90 s. `/health` comprobará la BD. | **Aceptado** en [ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md). |
| R10 | Dos implementaciones de la reclamación (`backend/` desplegada y `api/` sin desplegar) divergen: hoy verifican la identidad distinto (id no vacío vs. dominio del correo) y guardan la idempotencia distinto. | — | A | M (confusión sobre qué se prueba y qué corre) | Decidir si `api/` se fusiona con `backend/` o se retira, antes de conectar PostgreSQL ([ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md)). Mientras tanto, la documentación toma `backend/` como fuente. | **Abierto**, identificado en S12. |

## Deuda técnica relacionada

- **Persistencia en memoria** (`_objects`, `_claims`, `_idempotency` en
  `backend/main.py`): los datos se pierden con cada instancia fría. Resolverla
  cierra R1 y hace durable la idempotencia (R2 queda mitigado solo dentro de una
  instancia).
- **Cliente sin adaptador HTTP**: el corte vertical de Flutter sigue usando
  servicios in-memory; las tácticas de cliente (R3, R4) están especificadas pero
  no implementadas.
- **Paso no atómico en `ClaimObjectUseCase`** (Flutter): crea la reclamación y
  después marca el objeto. Si el segundo paso fallara quedaría una reclamación
  con el objeto aún disponible. Con los adaptadores in-memory actuales solo
  pasaría en una carrera entre la comprobación de disponibilidad y
  `markAsClaimed`; desaparece cuando el cliente delegue la operación completa a
  la API, que sí la hace atómica.
