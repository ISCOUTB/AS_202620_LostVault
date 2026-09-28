# Evidencias — Despliegue y operación (Semana 8)

Documento único con todo lo que pide la Evidencia S8: URL pública, health
check, logs, métrica p95, protección de secretos y estimación de costo. Cada
afirmación aquí está respaldada por una petición real o una referencia a
código/prueba concreta — no hay números inventados.

## 1. URL del sistema desplegado y accesible desde fuera de la universidad

**`https://backend-nu-self-91.vercel.app`** — Vercel, plan Hobby, función
serverless Python 3.12 (Zero-Config). Verificado desde este entorno de
trabajo (fuera de la red de la universidad):

```
GET /            → 200 {"name":"LostVault API","status":"online","docs":"/docs","health":"/health"}
GET /health      → 200 {"status":"ok"}
GET /objects     → 200 {"items":[{"id":"obj-001","title":"Termo negro", ...}],"page":1,"pageSize":20,"total":1}
GET /docs        → Swagger UI (interactivo)
```

Decisión de plataforma documentada en
[ADR 0003](../adr/0003-plataforma-despliegue-vercel.md); vista completa en
[arc42 §7](../arc42/07_vista_despliegue.md).

## 2. Health check en producción

`GET /health` responde `200 {"status":"ok"}` de forma consistente (verificado
en múltiples peticiones en distintos momentos durante esta entrega). El
comentario `TODO` en `backend/main.py` línea 175 documenta honestamente que,
al no existir base de datos todavía, el check no tiene una dependencia
externa que verificar — responde sobre la disponibilidad del proceso, no de
un almacenamiento.

## 3. Logs en producción

El middleware `measure_latency` (`backend/main.py:103-129`) registra un
evento JSON estructurado por cada request, con: `time`, `level`, `message`,
`request_id`, `endpoint` (ruta con plantilla, no la ruta cruda —
p. ej. `/v1/objects/{object_id}/claims`, no `/v1/objects/obj-001/claims`),
`method`, `status_code`, `duration_ms`. Cada respuesta además incluye el
encabezado `X-Request-ID`, visible en cualquier petición real:

```
GET /health → header de respuesta: x-request-id: <uuid generado por request>
```

**Protección de secretos en logs:** `backend/test_api.py::test_logs_never_contain_the_token`
prueba explícitamente que el token JWT nunca aparece en la salida de logs, y
`test_request_log_is_structured_json` prueba el formato JSON línea por línea.
Ambas corren en CI en cada push (`.github/workflows/backend.yml`).

En Vercel, esta salida (stdout) es la que aparece en la pestaña "Logs" del
dashboard del proyecto para cada invocación — acceso al dashboard es del
equipo, no de este entorno de trabajo.

## 4. Métrica p95 en producción

`GET /metrics` existe, responde con el esquema correcto y su cálculo es
correcto — pero **no puede mostrar un valor no-nulo con el diseño actual en
producción**, y esto queda documentado en vez de ocultado:

```
GET /metrics → {"/health":{"p95_ms":null,"samples":1},
                "/objects":{"p95_ms":null,"samples":1}, ...}
```

Se intentó generar evidencia de un p95 real: múltiples peticiones
secuenciales y en paralelo (7 a `/health`, 5 a `/objects`, con parámetros de
consulta distintos para evitar cualquier caché intermedio) seguidas de
`GET /metrics`. En todos los intentos, `samples` se mantuvo en 1 por
endpoint. La causa es arquitectónica, no un defecto de código: Vercel no
garantiza reutilizar el mismo proceso entre invocaciones bajo tráfico ligero
y espaciado, así que el diccionario en memoria `_durations_by_endpoint` se
reinicia en cada petición. `_p95()` (línea 96-100) exige al menos 2 muestras
en la misma ventana para calcular un percentil — condición que nunca se
cumple entre peticiones reales separadas.

**Lo que sí es evidencia verificable de que el mecanismo funciona:**

- `backend/test_api.py::test_metrics_groups_by_route_template_not_raw_path`
  prueba, dentro de un mismo proceso, que tras varias peticiones
  `data["/objects"]["p95_ms"] is not None` — es decir, el cálculo es correcto
  cuando el estado se comparte, como ocurriría en un proceso persistente
  (contenedor, servidor tradicional) o si se agrega un almacén externo.
- El endpoint en producción responde 200 con el esquema esperado
  (`p95_ms`, `samples`), solo que con `samples: 1`.

**Recomendación documentada** (no implementada en esta entrega, requiere
aprovisionar un servicio adicional y credenciales del equipo): mover el
conteo de latencias a un almacén compartido entre invocaciones (Vercel KV /
Upstash Redis), o calcularlo agregando los `duration_ms` que ya se emiten en
los logs estructurados. Detalle en
[arc42 §7](../arc42/07_vista_despliegue.md) y
[ADR 0003](../adr/0003-plataforma-despliegue-vercel.md).

## 5. Protección de secretos

- `JWT_SECRET` se lee únicamente del entorno (`jwt_secret()`,
  `backend/main.py:50-55`); nunca está escrito en el código ni en el
  repositorio. Si falta, el proceso **no arranca** (`lifespan`, línea 58-62)
  — falla rápido y explícito, no en la primera petición de un usuario.
- En Vercel, `JWT_SECRET` está configurado como variable de entorno del
  proyecto (`backend/DEPLOY_VERCEL.md`, sección 3) — no versionada.
- En CI, el valor usado es un secreto de prueba fijo
  (`ci-test-secret-0123456789abcdef`, `.github/workflows/backend.yml`), no el
  secreto real de producción.
- `backend/.env.example` documenta qué variables se necesitan sin exponer
  valores reales.
- El token nunca aparece en logs (ver sección 3).

## 6. Guía de despliegue

Existe y está actualizada en `backend/DEPLOY_VERCEL.md`: URL, endpoints,
variables de entorno, y dos vías de redeploy (CLI `npx vercel --prod`, o
automático en cada push a `main` vía integración de Git). Complementada por
[arc42 §7](../arc42/07_vista_despliegue.md), que agrega el mapa completo de
dónde corre cada pieza del sistema (no solo la API).

## 7. Estimación de costo mensual

Corregida y disponible en `docs/despliegue/estimacion-costo-mensual.md`:
resultado esperado **$0/mes** con el volumen estimado (~6,000
operaciones/mes), dentro de la capa gratuita de Vercel (Hobby). La versión
anterior de este documento asumía "servidor del laboratorio" como plataforma
de la API; se corrigió para reflejar el despliegue real, con la decisión
formalizada en [ADR 0003](../adr/0003-plataforma-despliegue-vercel.md).

## 8. Calidad de código (SonarCloud)

`sonar-project.properties` tenía `sonar.sources` y la cobertura sin
configurar — el análisis corría prácticamente sobre nada. Se corrigió para
esta entrega:

- `sonar.sources=lib,backend`, con tests y exclusiones explícitas.
- `sonar.python.coverage.reportPaths=backend/coverage.xml`, generado por
  `pytest --cov` en `.github/workflows/backend.yml` y también antes del
  análisis en `.github/workflows/build.yml`.
- `sonar.dart.coverage.reportPaths=coverage/lcov.info`, generado por
  `flutter test --coverage` en `.github/workflows/build.yml` (a verificar en
  el dashboard si el plan de SonarCloud del proyecto reconoce Dart).
- `.github/workflows/build.yml` pasó de `windows-latest` (solo build de
  Flutter, sin pruebas, sin backend) a `ubuntu-latest`, ahora corre pruebas
  de Flutter con cobertura y pruebas del backend con cobertura antes de
  enviar el análisis a SonarCloud.
- Se agregó `SonarSource/sonarqube-quality-gate-action` después del escaneo,
  para que el pipeline **falle explícitamente** si el Quality Gate queda en
  rojo, en vez de solo mostrarlo en el dashboard sin bloquear nada.

**Hallazgo adicional, distinto del anterior:** los builds del PR #10
(`Fausto-4:main` → `main`) fallaban con `sonar-scanner.bat failed with exit
code 1` y la advertencia `Running this GitHub Action without SONAR_TOKEN is
not recommended`. Causa: GitHub no expone los secrets del repositorio (como
`SONAR_TOKEN`) a workflows disparados por `pull_request` cuando el PR viene
de un fork — es una protección de seguridad de GitHub, no un defecto del
pipeline. Se corrigió agregando una condición a nivel de job en
`.github/workflows/build.yml` (`if: github.event_name == 'push' ||
github.event.pull_request.head.repo.full_name == github.repository`) para
que el análisis de SonarCloud se salte en PRs desde forks y solo corra en
push a `main` o en PRs desde ramas dentro del propio repositorio.
`flutter.yml` y `backend.yml` no usan secrets, así que siguen validando cada
PR (incluidos los de forks) sin este problema.

**Lo que no se puede verificar desde este entorno de trabajo:** el resultado
real del próximo análisis en el dashboard de SonarCloud (`sonarcloud.io`) no
es accesible aquí — su API está bloqueada por política de red del entorno.
El equipo debe hacer push de estos cambios y revisar el Quality Gate en
`sonarcloud.io/organizations/isco-utb` después de que corra el pipeline.

## 9. Qué falta y quién lo hace

| Pendiente | Por qué no se hizo aquí | Quién lo hace |
|---|---|---|
| Confirmar que el próximo pipeline pasa en verde y que SonarCloud queda en verde | Requiere hacer push y ver el resultado real en GitHub/SonarCloud, ninguno accesible desde este entorno | El equipo, después de aplicar estos cambios |
| Screenshot(s) del dashboard de SonarCloud y de logs de Vercel para el profesor, si la rúbrica los pide como imagen | Requiere sesión autenticada en esos dashboards | El equipo |
| p95 real acumulado en producción | Limitación arquitectónica documentada en la sección 4; requiere un almacén externo que nadie aprovisionó | Decisión del equipo si se prioriza para una entrega futura |
| Publicar el sitio Flutter web (GitHub Pages o equivalente) | No estaba desplegado antes de esta entrega y no era uno de los criterios en rojo señalados | El equipo, si la rúbrica lo requiere explícitamente |
| Protección de rama `main` (branch protection exigiendo que el pipeline pase) | Configuración de GitHub que no se puede aplicar sin acceso al repositorio real | El equipo, en Settings → Branches del repositorio |

## 10. Trazabilidad de archivos tocados en esta entrega

- `sonar-project.properties`, `backend/requirements-dev.txt`,
  `.github/workflows/backend.yml`, `.github/workflows/build.yml` — Quality
  Gate.
- `docs/arc42/07_vista_despliegue.md` (nuevo) — vista de despliegue real.
- `docs/adr/0003-plataforma-despliegue-vercel.md` (nuevo) — decisión de
  plataforma.
- `docs/adr/0002-integracion-reclamacion-api.md` — línea final actualizada
  para reflejar que el proveedor ya está desplegado.
- `docs/arc42/09_decisiones.md` — tabla de ADRs actualizada.
- `docs/despliegue/estimacion-costo-mensual.md` — corregido para reflejar
  Vercel en vez de "servidor del laboratorio".
- `backend/vercel.json` (nuevo), `infra/terraform/` (nuevo, opcional) — IaC
  versionada.
- `docs/despliegue/evidencias-profesor.md` (este documento, nuevo).
