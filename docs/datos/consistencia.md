# Evidencia S12 — Consistencia por operación

Cada operación de LostVault se ubica en el espectro de consistencia según lo que
exige su escenario de calidad ([arc42 §10](../arc42/10_requisitos_calidad.md)), no
según lo que sería "más seguro" en abstracto. La regla que ordena toda la tabla:

> **Solo la reclamación necesita consistencia fuerte**, porque es la única
> operación donde un dato viejo produce un daño irreversible (entregar un objeto a
> quien no es su dueño, Escenario 3). Todo lo que se *lee* antes de reclamar puede
> estar un poco desactualizado, porque la reclamación vuelve a comprobar el estado
> real en el momento de escribir.

**Alcance.** La tabla describe `backend/` (FastAPI en Vercel), que es la API
desplegada ([arc42 §7](../arc42/07_vista_despliegue.md)). El repositorio tiene
además `api/`, una segunda implementación **solo** de la reclamación (PR #19):
no está desplegada ni corre en CI, y su almacén (`api/app/store.py`) también es
en memoria, así que tiene las mismas garantías que `backend/` en C1–C3 y C7, y
el mismo riesgo R1. Cuando haya dos implementaciones que difieren, manda
`backend/`; ver riesgo R10 en [arc42 §11](../arc42/11_riesgos.md).

## 1. Tabla operación → garantía

| # | Operación | Dónde | Garantía | Por qué (escenario) | Qué le exige al sistema | Estado en el repo |
|---|---|---|---|---|---|---|
| C1 | **Reclamar un objeto** | `POST /v1/objects/{id}/claims` | **Fuerte (linealizable por objeto)**: como máximo una reclamación por objeto, vista igual por todas las instancias | Escenario 3: 100 % de reclamaciones indebidas bloqueadas. Dos `201` para el mismo objeto = entrega indebida | Una transacción local con `UPDATE … WHERE status='available'` condicional + `UNIQUE(object_id)` en `claims` ([ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md)) | **Parcial.** Hoy la garantía es fuerte solo dentro de un proceso (`_lock` en `backend/main.py`, `test_concurrent_claims_produce_exactly_one_201`). Entre instancias serverless no se cumple: riesgo R1 |
| C2 | **Registrar y consultar la `Idempotency-Key`** | misma operación | **Fuerte, en la misma transacción que C1** | F2 de la [S11](../fallos-parciales/s11-fallos-parciales.md): si el reintento no ve la clave guardada, al dueño se le responde `409` | Tabla `idempotency_keys (user_id, key) PRIMARY KEY` escrita en la transacción de C1 | **Parcial.** Diccionario `_idempotency` en memoria; se pierde con cada instancia fría |
| C3 | **Verificar identidad** antes de reclamar | `identity_verification` (dentro de C1) | **Fuerte, leída dentro de la transacción de C1** | Escenario 3: no puede autorizarse con un estado de verificación viejo | Mantener el módulo en el mismo proceso ([ADR 0005](../adr/0005-no-extraer-verificacion-identidad.md)); si se extrae, la garantía pasa a una saga | Implementado en el proceso (`verify_identity`) |
| C4 | **Confirmación de mi reclamación** | respuesta `201`/`200` de C1 | **Leer lo que yo escribí** (*read-your-writes*) | Escenario 2: el estudiante debe ver al instante que reclamó | La UI usa el cuerpo de la respuesta, **no** vuelve a leer el listado cacheado. La respuesta es `no-store` | Implementado en el servidor (`test_claim_responses_are_never_cached`); adaptador HTTP del cliente pendiente |
| C5 | **Buscar / listar objetos** | `GET /objects` | **Eventual acotada: máximo 90 s** de atraso (30 s fresco + 60 s *stale-while-revalidate*) | Escenarios 4 (p95 ≤ 2 s con 200 usuarios) y 1 (disponibilidad). Ver un objeto como "Disponible" hasta 90 s después de reclamado **no causa daño**: C1 lo revalida y responde `409` | Caché en la CDN de Vercel ([cache.md](cache.md)) | **Implementado**: cabecera `Cache-Control` en `backend/main.py`, `test_objects_listing_is_cacheable_only_in_the_cdn` |
| C6 | **Publicar un objeto** | futuro `POST /objects` | Escritura **fuerte** (se confirma después del commit); visibilidad en la búsqueda **eventual ≤ 90 s**; *read-your-writes* para quien publica | Escenario 2: la confirmación debe ser inmediata; que otros lo vean 1 minuto después es aceptable | Commit antes del `201`; la UI muestra el objeto devuelto, no lo busca en el listado | Pendiente (el endpoint aún no existe) |
| C7 | **Validar la sesión** (JWT) | `current_user_id` | **Eventual hasta que vence el token**: revocar una sesión no tiene efecto inmediato | Costo aceptado a cambio de no consultar un almacén de sesiones en cada petición (serverless, sin estado) | Tokens de vida corta (≤ 1 h, claim `exp` obligatorio) | **Implementado**: `current_user_id` exige `sub` y `exp` (igual que `api/app/auth.py`); pruebas `test_claim_401_with_token_without_exp` y `test_claim_401_with_expired_token`. La vida máxima del token la fija quien lo emite (autenticación institucional, pendiente) |
| C8 | **Perfil del usuario** | módulo `users` | *Read-your-writes* | Cambiar el perfil y no verlo confunde al usuario | Sin caché compartida (`no-store`) | Pendiente (in-memory en Flutter) |
| C9 | **Marcar intento bloqueado para revisión** | Escenario 3 ("marca el intento") | **Eventual ≤ 15 min, entrega al menos una vez** | La oficina revisa en horas, no en segundos; lo que no se puede es *perder* el registro | Fila en `outbox` en la misma transacción ([eventos.md](eventos.md)) | Pendiente |
| C10 | **Notificar a la oficina / al estudiante** | efecto de C1 | **Eventual ≤ 15 min, al menos una vez**, consumidor idempotente | Ninguna regla de negocio depende del aviso | Patrón outbox ([eventos.md](eventos.md)) | Pendiente (diseñado) |
| C11 | **Métricas p95** | `GET /metrics` | **Mejor esfuerzo**: se tolera perder muestras | Solo sirven para observar el Escenario 4, no para decidir nada en línea | Hoy en memoria; no acumulan entre instancias (R7) | Implementado con la limitación R7 |

## 2. Cuánto cuesta cada nivel

| Nivel | Operaciones | Costo que pagamos |
|---|---|---|
| Fuerte | C1, C2, C3 | Una base de datos transaccional compartida entre instancias ([ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md)): conexión en cada reclamación, latencia de red a la BD, y si la BD no responde la reclamación falla (se prefiere fallar a entregar mal: **CP** sobre **AP** para C1). |
| *Read-your-writes* | C4, C6, C8 | Disciplina en el cliente: mostrar la respuesta de la escritura en vez de releer algo cacheado. Sin costo de infraestructura. |
| Eventual acotada | C5, C6 (visibilidad) | Un estudiante puede ver un objeto "Disponible" que ya no lo está y recibir `409` al reclamarlo. Se acepta porque C1 lo detecta. |
| Eventual + al menos una vez | C9, C10 | Tabla `outbox`, un publicador periódico y consumidores que toleran duplicados. |
| Mejor esfuerzo | C11 | Métricas incompletas en producción (R7). |

## 3. Decisiones y pendientes que salen de esta tabla

- La garantía fuerte de C1 y C2 **depende de la base de datos compartida**: es la
  decisión más cara de revertir del proyecto y se registra en el
  [ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md).
- C5 justifica cachear `GET /objects` y **solo eso**: ver [cache.md](cache.md).
- C7: resuelto en S12. Un token sin `exp` o vencido se rechaza con `401`, así que
  la ventana de revocación siempre tiene límite.
- `api/` duplica la lógica de C1–C3. Hay que decidir si se fusiona con `backend/` o se
  retira antes de conectar PostgreSQL, para no migrar dos almacenes (R10).
