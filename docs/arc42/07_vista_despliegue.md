# 7. Vista de Despliegue

Esta sección documenta dónde corre **realmente** cada pieza del sistema hoy, no dónde
se planeó que corriera. La distinción importa: `docs/despliegue/estimacion-costo-mensual.md`
(sección 1) describe una decisión de plataforma que en parte quedó desactualizada
frente a lo que el equipo terminó desplegando; esta sección es la fuente de verdad
operativa y esa otra tabla se corrige para apuntar aquí.

## Mapa por pieza

| Pieza | Dónde corre hoy | Evidencia |
|---|---|---|
| **Sitio** (Flutter web / móvil) | No está desplegado públicamente todavía. Corre localmente (`flutter run`) o como build (`flutter build web`) generado en CI únicamente para que el análisis de SonarCloud tenga artefactos que revisar, sin publicarse a ningún hosting. | `.github/workflows/build.yml` (`flutter build web`, sin paso de publicación); no existe workflow de `actions/deploy-pages` ni configuración de GitHub Pages en el repo. |
| **API** (`objects` / `claims`, FastAPI) | **Vercel**, función serverless Python 3.12, detección Zero-Config a partir de `backend/requirements.txt` y `backend/main.py:app`. | `backend/DEPLOY_VERCEL.md`; verificado en vivo: `GET https://backend-nu-self-91.vercel.app/health` → `{"status":"ok"}`, `GET .../objects` → catálogo real. |
| **Base de datos** | No existe. El estado (`_objects`, `_claims`) vive en diccionarios de Python en memoria, dentro de `backend/main.py`. Se reinicia con cada instancia fría de la función. | `backend/main.py` (`_objects: dict[str, dict]`, `_claims: dict[...]`); confirmado empíricamente (ver "Limitación descubierta" abajo). |
| **Archivos/objetos** | No aplica. `LostObject` no tiene campo de imagen en este corte. | `lib/features/objects/domain/lost_object.dart`. |
| **Trabajos programados** | Ninguno configurado. | Ningún workflow en `.github/workflows/` usa el disparador `schedule:`. |
| **Pipeline** | GitHub Actions, repo público (sin costo de minutos): `flutter.yml` (analyze + test), `backend.yml` (pytest + cobertura), `build.yml` (build Flutter + análisis SonarCloud + verificación del Quality Gate). | `.github/workflows/*.yml`. |

## Por qué la API sí es función y el sitio (cuando se publique) también

Usando el mismo criterio de la guía de la semana ("¿el tráfico es esporádico o
sostenido?"): la API de LostVault en este corte tiene tráfico de demostración/curso,
no sostenido, y el arranque en frío medido de Vercel para una función Python simple
(cientos de ms) es compatible con el p95 objetivo de 2s del Escenario 2 — de ahí que
serverless sea una decisión razonable, a diferencia de lo que asumía la tabla de
costos original (que partía de "tráfico sostenido durante horario de clases" sin
haber corrido el sistema real todavía).

## Limitación descubierta: las métricas en memoria no acumulan entre invocaciones

Al generar evidencia de `p95` en producción para esta entrega se hicieron múltiples
peticiones (secuenciales y en paralelo, con parámetros distintos para evitar cachés
intermedios) contra `/health` y `/objects`, seguidas de `GET /metrics`:

```
GET /health   → 200 {"status":"ok"}          (x7, en distintos momentos)
GET /objects  → 200 {"items":[...],"total":1} (x5)
GET /metrics  → {"/health":{"p95_ms":null,"samples":1},
                 "/objects":{"p95_ms":null,"samples":1}, ...}
```

`samples` nunca superó 1 para ningún endpoint, sin importar cuántas peticiones
previas se hicieran. La causa raíz **no es un bug en el código** — el mecanismo de
`_p95()`/ventana deslizante en `backend/main.py` es correcto y está probado por
`test_metrics_groups_by_route_template_not_raw_path` en un único proceso — sino una
consecuencia de la arquitectura serverless: bajo el tráfico ligero y espaciado de
este proyecto, Vercel no reutiliza la misma instancia de proceso entre peticiones, así
que cada petición ve un diccionario `_p95` recién inicializado. Es el mismo motivo por
el que no hay "base de datos": cualquier estado en memoria de un proceso Python en
Vercel es efímero por invocación, no solo los contadores de métricas.

**Consecuencia para la evidencia de esta semana:** el número de `p95_ms` en
producción no puede mostrarse como no-nulo con el diseño actual, y no se puede
resolver generando más tráfico desde afuera. Lo que sí se puede evidenciar y se deja
documentado en `docs/despliegue/evidencias-profesor.md`: (a) el endpoint existe, responde
200 y tiene el esquema correcto; (b) el cálculo de p95 es correcto, verificado por
prueba unitaria en un solo proceso; (c) esta limitación arquitectónica en sí misma.

**Corrección real, fuera del alcance de esta entrega:** mover el conteo de latencias
a un almacén externo compartido entre invocaciones (Vercel KV / Upstash Redis, o
agregación desde los logs estructurados que sí se emiten por request). No se
implementa aquí porque requeriría credenciales y un servicio adicional que el equipo
debe decidir y aprovisionar; se deja como recomendación en el ADR de plataforma
([0003](../adr/0003-plataforma-despliegue-vercel.md)).

## Infraestructura como código

- `backend/vercel.json` fija explícitamente el runtime de la función
  (`python3.12`) en vez de depender solo de la detección automática de
  Vercel — es la IaC versionada mínima requerida por la guía de la semana.
- `infra/terraform/` es un espejo declarativo **opcional** de esa misma
  configuración usando el proveedor oficial de Vercel (`vercel/vercel`), por
  si el equipo quiere adoptar Terraform formalmente. No se aplicó desde este
  entorno (ver `infra/terraform/README.md` para el porqué).

## Relación con otras secciones

- La decisión de usar Vercel para la API se justifica formalmente en
  [ADR 0003](../adr/0003-plataforma-despliegue-vercel.md).
- El costo mensual estimado, corregido para reflejar esta vista, está en
  `docs/despliegue/estimacion-costo-mensual.md`.
- La evidencia consolidada para el profesor (URL, health, logs, protección de
  secretos, costo) está en `docs/despliegue/evidencias-profesor.md`.
