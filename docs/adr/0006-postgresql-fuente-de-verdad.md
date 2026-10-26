# ADR 0006: PostgreSQL gestionado como única fuente de verdad, con las invariantes en el esquema

- **Estado**: Propuesto
- **Fecha**: 2026-10-25
- **Decisores**: Equipo LostVault
- **Relacionado**: [ADR 0002](0002-integracion-reclamacion-api.md) (reclamación síncrona),
  [ADR 0003](0003-plataforma-despliegue-vercel.md) (Vercel serverless),
  [ADR 0005](0005-no-extraer-verificacion-identidad.md) (no extraer verificación),
  [consistencia.md](../datos/consistencia.md), [cache.md](../datos/cache.md),
  [eventos.md](../datos/eventos.md), [arc42 §11 R1](../arc42/11_riesgos.md)

## Contexto

LostVault no tiene base de datos: objetos, reclamaciones y claves de
idempotencia viven en diccionarios de `backend/main.py`
([arc42 §7](../arc42/07_vista_despliegue.md)). Con Vercel cada instancia tiene su
propia memoria, así que:

- la reclamación solo es consistente dentro de un proceso (riesgo **R1**: dos
  instancias pueden aceptar el mismo objeto, Escenario 3);
- la idempotencia de la S11 se pierde con cada instancia fría;
- los datos desaparecen al reiniciar.

La tabla de [consistencia](../datos/consistencia.md) exige **consistencia fuerte**
solo en la reclamación (C1–C3) y eventual en el resto. Hay que elegir el almacén
que la garantice.

**Por qué es la decisión de datos más cara de revertir.** Los endpoints y el
contrato OpenAPI no cambian si cambia el almacén; lo que queda atado es:

1. **Dónde viven las invariantes.** "Un objeto, una reclamación" y "una clave de
   idempotencia por usuario" quedan como restricciones del esquema (`UNIQUE`,
   `PRIMARY KEY`, `CHECK`). Cambiar a un almacén sin esas restricciones obliga a
   reimplementarlas en código y volver a probar el Escenario 3.
2. **Los datos personales migrados.** Usuarios y, más adelante, datos de
   verificación (Ley 1581 de 2012, [arc42 §2](../arc42/02_restricciones.md)) quedan en
   la región y el proveedor elegidos. Migrarlos después exige copiar, validar y
   borrar datos sensibles con el sistema en uso.
3. **El outbox** ([eventos.md](../datos/eventos.md)) depende de escribir el evento
   en la misma transacción que la reclamación.
4. **Los identificadores.** Se fijan en esta decisión (ver abajo) y aparecen en
   URL, eventos y enlaces ya compartidos.

## Decisión

Usar **PostgreSQL gestionado y compatible con serverless** (Neon, conectado por
la integración de Vercel) como **única fuente de verdad** de `objects`, `claims`,
`idempotency_keys`, `users` y `outbox`.

- La reclamación es **una transacción local** de *READ COMMITTED*:
  `UPDATE objects SET status='claimed' WHERE id=$1 AND status='available'`. Si no
  actualiza filas, se consulta si la reclamación es del mismo usuario (`200`) o
  de otro (`409`), como hace hoy `create_claim`. En la misma transacción se
  insertan la reclamación, la clave de idempotencia y el evento del outbox.
- Las invariantes van en el esquema, no solo en el código:

```sql
CREATE TABLE objects (
  id          uuid PRIMARY KEY,
  title       text NOT NULL,
  description text NOT NULL,
  status      text NOT NULL CHECK (status IN ('available', 'claimed')),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE claims (
  id         uuid PRIMARY KEY,
  object_id  uuid NOT NULL UNIQUE REFERENCES objects(id),  -- un objeto, una reclamación
  user_id    text NOT NULL,
  verified   boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE idempotency_keys (
  user_id    text         NOT NULL,
  key        varchar(255) NOT NULL,
  object_id  uuid         NOT NULL REFERENCES objects(id),
  response   jsonb        NOT NULL,
  created_at timestamptz  NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, key)
);
```

- **Identificadores UUID generados por el servidor** (los `obj-001` actuales son
  datos de ejemplo). No revelan cuántos objetos hay y se pueden crear sin
  consultar la BD.
- Conexiones por el **endpoint con *pooling*** del proveedor, porque cada
  invocación serverless abriría su propia conexión.
- Las lecturas del listado no van directo a la BD en cada petición: pasan por la
  caché de la CDN ([cache.md](../datos/cache.md)).

## Alternativas consideradas

| Opción | Ventaja | Por qué no |
|---|---|---|
| **A. PostgreSQL gestionado (elegida)** | Transacciones ACID y restricciones declarativas: R1 se cierra en el esquema. Outbox en la misma transacción. SQL para los reportes de la oficina. | Ver Consecuencias. |
| B. Base documental (Firestore / MongoDB Atlas) | Esquema flexible, buen SDK móvil. | La unicidad de "una reclamación por objeto" y la idempotencia quedarían en código y en transacciones del SDK. Los datos de LostVault (objetos, reclamaciones, usuarios) son relacionales y pequeños. |
| C. Clave-valor (Vercel KV / Upstash Redis) como almacén principal | Muy simple, ya sugerido para R7. | Sin restricciones ni consultas por filtros (búsqueda por `status` y texto). Durabilidad y transacciones limitadas para la fuente de verdad. Sigue siendo válido para métricas (R7). |
| D. Seguir en memoria | Cero costo y cero configuración. | Deja abierto R1 (Escenario 3) y pierde datos con cada instancia fría. No es un sistema usable. |
| E. PostgreSQL en servidor propio (laboratorio / VM) | Control total. | Hay que operarlo y mantenerlo disponible 24/7 (Escenario 1) con un equipo de 4 estudiantes. |

## Consecuencias

**Positivas**
- Cierra **R1**: dos instancias no pueden crear dos reclamaciones del mismo
  objeto; la segunda choca con el `UPDATE` condicional o con `UNIQUE(object_id)`.
- La idempotencia de la S11 pasa a ser durable y compartida entre instancias.
- Habilita el outbox para notificaciones y el registro de intentos bloqueados
  (C9, C10).

**Negativas / costos**
- **Dependencia nueva en el camino crítico**: si la BD no responde, la
  reclamación falla (`503`). Es la elección consciente de consistencia sobre
  disponibilidad para C1. El listado sigue sirviéndose desde la caché por hasta
  90 s.
- **Latencia**: una consulta de red por reclamación, más el arranque de la BD si
  el proveedor la suspende por inactividad (*scale to zero*). Hay que medirla
  contra el p95 ≤ 2 s; si no se cumple, desactivar la suspensión.
- `/health` debe comprobar la BD (TODO ya marcado en `backend/main.py`).
- Credenciales nuevas (`DATABASE_URL`) gestionadas como `JWT_SECRET`, solo en el
  entorno.
- Plan gratuito con límites de almacenamiento y cómputo; revisar
  `docs/despliegue/estimacion-costo-mensual.md`.

## Disparadores de revisión

- Volumen de búsqueda de texto que PostgreSQL (`ILIKE` / `tsvector`) no sirva
  dentro del p95: evaluar un índice de búsqueda aparte, alimentado por el outbox.
- Extracción de `identity_verification` (ADR 0005): su almacenamiento sería
  propio y la reclamación pasaría a saga.
