# 7. Vista de Despliegue

Esta sección documenta dónde corre **realmente** cada pieza del sistema hoy, no dónde
se planeó que corriera. La distinción importa: `docs/despliegue/estimacion-costo-mensual.md`
(sección 1) describe una decisión de plataforma que en parte quedó desactualizada
frente a lo que el equipo terminó desplegando; esta sección es la fuente de verdad
operativa y esa otra tabla se corrige para apuntar aquí.

**Despliegue público de referencia para la entrega:** [LostVault API en Vercel](https://backend-nu-self-91.vercel.app). [Salud](https://backend-nu-self-91.vercel.app/health) y [catálogo](https://backend-nu-self-91.vercel.app/objects) permiten comprobarlo. El cliente Flutter se ejecuta localmente.

## Mapa por pieza

| Pieza | Dónde corre hoy | Evidencia |
|---|---|---|
| **Sitio** (Flutter web / móvil) | No está desplegado públicamente todavía. Corre localmente (`flutter run`) o como build (`flutter build web`) generado en CI únicamente para que el análisis de SonarCloud tenga artefactos que revisar, sin publicarse a ningún hosting. | `.github/workflows/build.yml` (`flutter build web`, sin paso de publicación); no existe workflow de `actions/deploy-pages` ni configuración de GitHub Pages en el repo. |
| **API** (`objects` / `claims`, FastAPI) | **Vercel**, función serverless Python 3.12, detección Zero-Config a partir de `backend/requirements.txt` y `backend/main.py:app`. | `backend/DEPLOY_VERCEL.md`; verificado en vivo: `GET https://backend-nu-self-91.vercel.app/health` → `{"status":"ok"}`, `GET .../objects` → catálogo real. |
| **`api/`** (Claims API, FastAPI) | **No se despliega.** Implementación alternativa solo de la reclamación, con su propio almacén en memoria y su propio `Dockerfile`. Ningún workflow la prueba ni la publica. | `api/README.md`; el proyecto de Vercel es `backend` (`backend/DEPLOY_VERCEL.md`) y `.github/workflows/backend.yml` solo prueba `backend/test_api.py`. |
| **Base de datos** | No existe (decidido PostgreSQL gestionado en [ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md), pendiente). El estado (`_objects`, `_claims`) vive en diccionarios de Python en memoria, dentro de `backend/main.py`. Se reinicia con cada instancia fría de la función. | `backend/main.py` (`_objects: dict[str, dict]`, `_claims: dict[...]`); confirmado empíricamente (ver "Limitación descubierta" abajo). |
| **Caché** | La API emite cabeceras de caché para `GET /objects`. La [medición S14](../medicion/s14-medicion-atributos.md) registró `MISS` en la CDN. Las reclamaciones llevan `no-store`. | `backend/main.py` (`cache_policy`, `OBJECTS_CACHE_CONTROL`); diseño en `docs/datos/cache.md`. |
| **Archivos/objetos** | No aplica. `LostObject` no tiene campo de imagen en este corte. | `lib/features/objects/domain/lost_object.dart`. |
| **Trabajos programados** | Ninguno configurado. | Ningún workflow en `.github/workflows/` usa el disparador `schedule:`. |
| **Pipeline** | GitHub Actions, repo público (sin costo de minutos): `flutter.yml` (analyze + test), `backend.yml` (pytest + cobertura), `build.yml` (build Flutter + análisis SonarCloud + verificación del Quality Gate). | `.github/workflows/*.yml`. |

## Por qué la API sí es función y el sitio (cuando se publique) también

Usando el mismo criterio de la guía de la semana ("¿el tráfico es esporádico o
sostenido?"): la API de LostVault en este corte tiene tráfico de demostración/curso,
no sostenido, y el arranque en frío medido de Vercel para una función Python simple
(cientos de ms) es compatible con el p95 objetivo de 2 s del Escenario 4 — de ahí que
serverless sea una decisión razonable, a diferencia de lo que asumía la tabla de
costos original (que partía de "tráfico sostenido durante horario de clases" sin
haber corrido el sistema real todavía).

## Métricas y estado por instancia

`GET /metrics` agrega las muestras del proceso que responde. S14 observó acumulación cuando se reutilizó una instancia (364 muestras de búsqueda después de la carga). Un reinicio puede borrar esas muestras. Para evaluar AS-04 se usa el p95 del ensayo de extremo a extremo, documentado en [S14](../medicion/s14-medicion-atributos.md).

El catálogo, las reclamaciones y las claves de idempotencia también viven en memoria del proceso. La persistencia entre instancias sigue como propuesta en el [ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md).

## Infraestructura como código

- El despliegue usa la detección automática de Vercel a partir de `backend/`. La configuración operativa está en [DEPLOY_VERCEL.md](../../backend/DEPLOY_VERCEL.md).
- `infra/terraform/` conserva la configuración declarativa opcional.

## Relación con otras secciones

- La decisión de usar Vercel para la API se justifica formalmente en
  [ADR 0003](../adr/0003-plataforma-despliegue-vercel.md).
- El costo mensual estimado, corregido para reflejar esta vista, está en
  `docs/despliegue/estimacion-costo-mensual.md`.
- La evidencia consolidada para el profesor (URL, health, logs, protección de
  secretos, costo) está en `docs/despliegue/evidencias-profesor.md`.
