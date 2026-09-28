# ADR 0003: Plataforma de despliegue de la API — Vercel (funciones serverless)

- **Estado**: Aceptado
- **Fecha**: 2026-09-27
- **Decisores**: Equipo LostVault
- **Relacionado**: [ADR 0002](0002-integracion-reclamacion-api.md), [arc42 §7 Vista de despliegue](../arc42/07_vista_despliegue.md)

## Contexto

La Evidencia S8 exige que el sistema esté "desplegado y accesible desde fuera
de la red de la universidad", con una URL pública verificable, health check,
logs y una métrica p95 en producción. `backend/main.py` (FastAPI) implementa
el proveedor HTTP definido en el [ADR 0002](0002-integracion-reclamacion-api.md).
Faltaba decidir y documentar formalmente dónde corre ese proceso.

Nota sobre un documento previo: `docs/despliegue/estimacion-costo-mensual.md`
(sección 1, versión anterior a esta entrega) asumía que la API correría en el
"servidor del laboratorio", con tráfico sostenido durante horario de clases.
Esa fila describía un plan, no lo que el equipo terminó desplegando. Este ADR
documenta la decisión real y `estimacion-costo-mensual.md` se corrige para
apuntar aquí.

Importante para no confundir dos entregas distintas: existe también
`docs/adr/0003-despliegue-busqueda-lostvault.md` (con un typo de numeración
histórico, "000.3"), que es el ejercicio comparativo de laboratorio (Railway
vs. Google Cloud Functions Gen2 para el endpoint de búsqueda), evaluado por
separado como el 15% del segundo corte. Ese documento no describe el sistema
real desplegado y no necesita coincidir con esta decisión — así lo aclara la
guía de la semana ("esta nota corresponde al análisis comparativo; la
evidencia S8 califica la operación del sistema real").

## Criterios usados (guía de la semana)

1. **¿El tráfico es esporádico o sostenido?** El tráfico real de este proyecto
   (curso, demostración, evaluación) es esporádico, no sostenido — no cumple
   el criterio que exigiría un proceso continuo.
2. **¿El p95 objetivo es compatible con el arranque en frío del candidato?**
   El Escenario 2 exige p95 ≤ 2s con 200 usuarios concurrentes para búsquedas.
   El arranque en frío de una función Python simple en Vercel es del orden de
   cientos de milisegundos, muy por debajo de ese umbral.
3. **Costo y fricción operativa para un proyecto académico**: sin tarjeta,
   sin servidor que alguien deba mantener encendido, con detección
   Zero-Config a partir de `backend/requirements.txt` y `backend/main.py:app`.

## Decisión

Se despliega la API en **Vercel**, como función serverless Python 3.12,
detectada automáticamente (Zero-Config) sin Docker ni configuración manual de
runtime.

- **URL de producción**: `https://backend-nu-self-91.vercel.app`
- **Proyecto Vercel**: `shamara-llorente-s-projects/backend`
- **Variables de entorno**: `JWT_SECRET` (obligatoria, validada en el
  `lifespan` de FastAPI; el proceso no arranca sin ella) y `LOG_LEVEL`
  (`INFO` por defecto).
- **Redeploy**: automático en cada push a `main` (Root Directory = `backend`
  en la configuración de Git del proyecto Vercel), o manual con
  `npx vercel --prod` desde `backend/`.

Detalle completo de endpoints y variables en `backend/DEPLOY_VERCEL.md`.

## Alternativas consideradas

**Servidor de laboratorio (proceso continuo).** Descartada: el requisito no
negociable de la Evidencia S8 es que el evaluador la abra "desde su casa", y
la accesibilidad del servidor del laboratorio desde fuera de la red
universitaria nunca se confirmó (quedó marcada como pendiente crítico en la
versión anterior de `estimacion-costo-mensual.md`). Además, un proceso
continuo para tráfico esporádico contradice el criterio 1 de la guía.

**Contenedor en un PaaS con proceso siempre activo (Render, Fly.io).**
Viable y sigue siendo la alternativa recomendada si el tráfico deja de ser
esporádico o si se necesita estado persistente en memoria entre peticiones
(ver limitación abajo). No se elige ahora porque añade un servicio adicional
a mantener sin necesidad, dado que Zero-Config en Vercel ya cumple los
criterios 1 y 2.

## Consecuencias

**Positivas**

- URL pública verificable sin infraestructura propia que mantener.
- Despliegue automático en cada push a `main`; sin paso manual salvo que se
  quiera forzar un redeploy.
- Costo $0 dentro del volumen estimado del proyecto.

**Costos aceptados — limitación descubierta durante esta entrega**

- Cada invocación de la función corre en una instancia potencialmente nueva:
  no hay estado compartido garantizado entre peticiones. Esto se comprobó
  empíricamente (ver [arc42 §7](../arc42/07_vista_despliegue.md)): múltiples
  peticiones a `/health` y `/objects`, seguidas de `GET /metrics`, mostraron
  siempre `"samples": 1` sin importar cuántas peticiones previas se hicieran.
- Consecuencia directa: **no hay base de datos real** — `_objects` y
  `_claims` son diccionarios en memoria que se reinician con cada instancia
  fría — y el mecanismo de p95 en `/metrics` no puede acumular muestras entre
  peticiones reales de producción, aunque su cálculo es correcto dentro de un
  mismo proceso (probado por `test_metrics_groups_by_route_template_not_raw_path`).
- Si el proyecto necesita persistencia real o métricas acumuladas entre
  peticiones, la vía recomendada es un almacén externo compartido (Vercel KV
  / Upstash Redis) o agregar los `duration_ms` desde los logs estructurados
  ya emitidos por request, no en memoria del proceso. Queda fuera del alcance
  de esta entrega por requerir aprovisionar un servicio adicional.

## Trazabilidad

- Configuración de despliegue: `backend/DEPLOY_VERCEL.md`.
- Runtime y endpoints: `backend/main.py`.
- Vista de despliegue completa: [arc42 §7](../arc42/07_vista_despliegue.md).
- Estimación de costo (corregida): `docs/despliegue/estimacion-costo-mensual.md`.
- Evidencia consolidada: `docs/despliegue/evidencias-profesor.md`.
