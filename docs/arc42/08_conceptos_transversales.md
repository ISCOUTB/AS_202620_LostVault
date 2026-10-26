# 8. Conceptos transversales

Conceptos que aplican a varios módulos a la vez. El detalle de cada uno está en
el documento enlazado; aquí queda la regla que todo el equipo debe seguir.

## 8.1 Consistencia de datos

**Regla:** consistencia fuerte **solo** para la reclamación de un objeto y lo que
ocurre dentro de ella (verificar identidad, registrar la clave de idempotencia).
Todo lo que se lee antes de reclamar (búsqueda, listado, estado de un objeto) es
**eventual acotado a 90 s**, porque la reclamación vuelve a comprobar el estado
real al escribir y responde `409` si el objeto ya no está disponible.

| Nivel | Operaciones |
|---|---|
| Fuerte (transacción local) | Reclamar, registrar `Idempotency-Key`, verificar identidad |
| *Read-your-writes* | Confirmación de reclamación, publicación propia, perfil |
| Eventual ≤ 90 s | Buscar / listar objetos, visibilidad de un objeto recién publicado |
| Eventual ≤ 15 min, al menos una vez | Avisos a la oficina, registro de intentos bloqueados |
| Mejor esfuerzo | Métricas p95 |

- Tabla completa operación → garantía: [`docs/datos/consistencia.md`](../datos/consistencia.md).
- Almacén que sostiene la garantía fuerte: [ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md) (PostgreSQL gestionado, invariantes en el esquema).

## 8.2 Caché

**Regla:** solo se cachea `GET /objects`, en la CDN de Vercel, con
`Cache-Control: public, max-age=0, s-maxage=30, stale-while-revalidate=60`.
Cualquier otra respuesta es `no-store` por defecto (middleware `cache_policy`
en `backend/main.py`). No se usa caché en memoria del proceso: en serverless no
sobrevive entre invocaciones (misma causa que R7).

**Invalidación:** por expiración (TTL), sin purga explícita. Es seguro porque la
reclamación nunca lee de la caché. Quien escribe ve su propio cambio por la
respuesta de su escritura, no por el listado.

Diseño completo, alternativas descartadas y verificación (`x-vercel-cache`):
[`docs/datos/cache.md`](../datos/cache.md).

## 8.3 Idempotencia y reintentos

Toda operación que cambia estado acepta `Idempotency-Key` y deduplica por
usuario. Los clientes reintentan solo ante errores técnicos (timeout, red,
`5xx`) y con la misma clave. Ver
[Evidencia S11](../fallos-parciales/s11-fallos-parciales.md).

## 8.4 Eventos y efectos secundarios

Los efectos que no son parte de la regla de negocio (avisos, registro de
intentos bloqueados, purgas futuras) se publican con **patrón outbox**: el
evento se escribe en la misma transacción que la operación, y un publicador
periódico lo entrega. Garantías: **al menos una vez**, orden **por objeto**,
consumidores **idempotentes** por `event_id`; no se promete "exactamente una
vez". No hay broker dedicado. Ver [`docs/datos/eventos.md`](../datos/eventos.md).
Estado: implementado como simulador local en `mensajeria/`
([taller](../mensajeria/taller-mensajeria.md), [ADR 0007](../adr/0007-notificacion-asincrona-outbox.md));
pendiente de conectarlo a la API junto con PostgreSQL.

## 8.5 Persistencia

Una sola base PostgreSQL es la fuente de verdad; cada módulo es dueño de sus
tablas y los demás acceden a ellas solo por su `public/`, igual que en el código
([§5](05_vista_bloques.md), [ADR 0001](../adr/0001-estilo-arquitectonico.md)). Las
invariantes de negocio críticas viven también en el esquema (`UNIQUE`, `CHECK`),
no solo en el código. Estado: hoy la persistencia es en memoria
([§7](07_vista_despliegue.md)); la migración está decidida en el
[ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md).
