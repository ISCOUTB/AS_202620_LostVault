# ADR 0008: Plataforma de despliegue de la API — servidor de la universidad

- **Estado**: Aceptado
- **Fecha**: 2026-11-23 (fecha de este registro; el cambio de plataforma consta desde el 2026-11-01 en [amenazas-dependencias-privacidad.md](../seguridad/amenazas-dependencias-privacidad.md))
- **Decisores**: Equipo LostVault
- **Reemplaza a**: [ADR 0003](0003-plataforma-despliegue-vercel.md)
- **Relacionado**: [ADR 0002](0002-integracion-reclamacion-api.md), [ADR 0006](0006-postgresql-fuente-de-verdad.md), [arc42 §7 Vista de despliegue](../arc42/07_vista_despliegue.md)

## Contexto

El [ADR 0003](0003-plataforma-despliegue-vercel.md) eligió Vercel (función serverless, plan gratuito)
para la entrega S8. Vercel fue una etapa intermedia: el equipo informó después que el
despliegue final es el **servidor que exige la universidad**, gestionado desde el panel
`https://panel.iscoutb.dev/` (Plataforma ISCOUTB / Dokploy Server).

Lo que se aprendió en Vercel y sigue vigente como antecedente:

- La medición S14 (`GET /objects`, Vercel) dio ~1.870 ms de p95 en estado estable y
  2.279 ms en la primera ráfaga; el objetivo del Escenario 4 es ≤ 2.000 ms
  ([S14](../medicion/s14-medicion-atributos.md)).
- Con 200 conexiones sostenidas falló el 44 % de las peticiones y Vercel bloqueó el
  tráfico con un 403 ([ADR 000.3](000.3-despliegue-busqueda-lostvault.md), sección 5.4).
- El estado (objetos, reclamaciones, claves de idempotencia) vivía en la memoria de cada
  instancia, que se reinicia con cada arranque en frío.

## Decisión

## Decisión

Se despliega la API en el **servidor de la universidad**, como contenedor Docker
administrado desde el panel (servicio `LostVault_Api`, proyecto `lostvault`, entorno `production`)[cite: 1].

- **Panel de administración**: `https://panel.iscoutb.dev/` (Plataforma ISCOUTB / Dokploy Server)[cite: 1].
- **URL pública activa**: `http://lostvault-lostvaultapi-1k8ly4-3d8075-144-24-4-187.sslip.io` (`Path: /`, `Port: 8000`, protocolo `HTTP`, `Cert: none`; verificada en vivo con `GET /health` devolviendo `{"status":"ok"}` y documentación Swagger UI disponible en `/docs`)[cite: 1, 6].
- **Código desplegado**: **`api/`** (`LostVault Claims API 1.0.0`, OAS 3.1, implementa el contrato `docs/contracts/lostvault-api.yaml` con `GET /health`, `POST /v1/auth/login`, `POST /v1/objects`, `DELETE /v1/objects/{objectId}` y `POST /v1/objects/{objectId}/claims`)[cite: 6]. El repositorio contiene dos implementaciones con `Dockerfile` (`backend/` y `api/`); el despliegue activo corresponde a `api/` (diseñada para panel con *Container Port* y *health checks*), por lo que no expone `GET /objects` ni la ruta sin versión `/objects` (que responde `{"detail":"Not Found"}`)[cite: 6].
- **Variables de entorno**: `JWT_SECRET` obligatoria, definida en el panel y no en el repositorio.
- **Base de datos**: el servidor ofrece una, pero el código **todavía no se conecta a ella**
  (el estado sigue en memoria). La persistencia queda como propuesta en el
  [ADR 0006](0006-postgresql-fuente-de-verdad.md).

## Alternativas consideradas

**Seguir en Vercel (ADR 0003).** Cumplía S8 sin infraestructura propia y con costo $0,
pero el plan gratuito no sostuvo la carga del Escenario 4 y el estado en memoria se
perdía entre instancias. Se conserva como antecedente medido, no como plataforma.

**Contenedor en un PaaS externo con proceso siempre activo (Render, Fly.io).** Viable
técnicamente, pero añade un proveedor y un costo que el equipo no necesita si la
universidad ya provee el servidor.

## Consecuencias

**Positivas**

- Despliegue en la plataforma que exige la universidad, sin cuota de un proveedor externo.
- Con un proceso de larga duración, el estado en memoria no se reinicia por arranques en
  frío (`api/README.md`: con un solo proceso la idempotencia es consistente).
- Hay una base de datos disponible para ejecutar el ADR 0006 cuando se conecte.

**Costos aceptados y límites**

- **No hay medición de rendimiento en este servidor.** Las cifras de S14 son de Vercel y
  no se pueden presentar como resultado de esta plataforma. La prueba de carga no se ha
  repetido contra el servidor de la universidad (requiere permiso de quien lo administra).
- **Tráfico sin cifrado TLS en la configuración observada:** el dominio `*.sslip.io` figura en el panel sobre `HTTP` con `Cert: none` (sin HTTPS forzado en esa vista)[cite: 1].
- El estado sigue en memoria: un reinicio del contenedor lo borra, y con más de un proceso
  (workers) el candado no se comparte (amenaza A5).
- Datos del servidor **sin confirmar** (no constan en el repositorio ni en la vista de dominios): número de workers, segundo factor del panel, ubicación física, política de registros y copias de seguridad.

## Qué debe cambiar por este ADR

- [ADR 0003](0003-plataforma-despliegue-vercel.md): estado "Reemplazado por el ADR 0008".
- arc42 §7, C4 niveles 2 y 3, `docs/aspectos.md` y `docs/despliegue/estimacion-costo-mensual.md`
  describen Vercel y deben alinearse con este ADR.

## Trazabilidad

- Antecedente medido: [S14](../medicion/s14-medicion-atributos.md) y [ADR 000.3](000.3-despliegue-busqueda-lostvault.md).
- Amenazas evaluadas contra este servidor: [amenazas-dependencias-privacidad.md](../seguridad/amenazas-dependencias-privacidad.md).
- Contenedores: `backend/Dockerfile`, `api/Dockerfile`, `docker-compose.yml`.
