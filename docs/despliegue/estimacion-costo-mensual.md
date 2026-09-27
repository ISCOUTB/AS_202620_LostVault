# Estimación de costo mensual y métrica operativa — LostVault

Evidencia S8 — Despliegue y operación

## 1. Dónde vive cada pieza (decisión previa al costo)

Siguiendo la advertencia de la guía ("elegir la plataforma antes que el escenario" es
el primer error frecuente), esta decisión se toma primero, pieza por pieza, y el
costo es consecuencia de ella, no al revés.

| Pieza | Dónde se ejecuta | Criterio que lo decide |
|---|---|---|
| Sitio (Flutter web) | GitHub Pages | Estático, repo público → gratis, sin tarjeta |
| API (FastAPI, `objects`/`claims`) | Servidor del laboratorio* | Tráfico sostenido durante horario de clases, no esporádico; no candidata a función (criterio 1 de la guía) |
| Base de datos | PostgreSQL en el servidor del laboratorio* | Nunca como función: proceso de larga duración por definición |
| Ficheros/objetos | No aplica en este corte | El modelo `LostObject` actual no tiene campo de foto; si se agrega, iría a almacenamiento de objetos (nunca al disco del contenedor) |
| Trabajos programados | GitHub Actions `schedule` (si aplica) | Corre minutos al día; proceso 24h sería desperdicio |
| Pipeline | GitHub Actions | Repo público → no consume cuota de minutos |

\* **Pendiente crítico:** la guía marca como `POR_CONFIRMAR` si el servidor del
laboratorio es accesible desde fuera de la universidad. Este es el requisito no
negociable de la Evidencia S8 ("el evaluador la abre desde su casa"). Mientras no
se confirme, este documento asume que sí lo es; si no lo fuera, la alternativa
sería Render o Fly.io (Google Cloud Run u otro servicio gestionado), sujeta a
verificar su capa gratuita vigente en el momento del despliegue.

## 2. Métrica ligada al escenario de calidad

**Métrica elegida:** latencia p95 de `GET /objects` (búsqueda).

**Por qué esta métrica:** el escenario de calidad de la semana 2 exige que el 95%
de las búsquedas respondan en ≤2s con 200 usuarios concurrentes. El criterio 2 de
esta misma guía usa exactamente ese número para decidir si una pieza puede ser
función ("si el p95 que declaraste es menor que el arranque en frío medido, la
pieza no es candidata"). Por eso esta métrica no es solo observabilidad: es la
evidencia que sostiene la decisión de la sección 1 (API como proceso continuo, no
función).

**Cómo se consulta:** endpoint `/metrics` en el backend FastAPI, o logs
estructurados por request con `endpoint`, `status`, `duration_ms`, agregables a p95
después.

## 3. Estimación de costo mensual

Los cuatro números que pide la guía, con supuestos explícitos y por confirmar con
el equipo:

| # | Número | Supuesto usado | Fuente del supuesto |
|---|---|---|---|
| 1 | Operaciones al mes | ~500 usuarios activos × ~10 búsquedas + ~1 publicación cada uno ≈ **6,000 operaciones/mes** | Estimado, ajustar con tamaño real esperado de usuarios de la UTB |
| 2 | Tamaño de datos almacenados | `LostObject` sin foto (id, title, description, status) ≈ <1KB/registro → **pocos MB/mes acumulados** | Modelo real confirmado en `lost_object.dart` |
| 3 | Tráfico de salida | Respuestas JSON pequeñas, sin imágenes en este corte → **decenas de MB/mes** | Derivado de (2) |
| 4 | Horas de ejecución | Servidor del laboratorio: proceso continuo, no por invocación → no aplica el modelo "por invocación"; si se usara un servicio gestionado tipo Render, sería equivalente a uso continuo de una instancia pequeña | Depende de la decisión de la sección 1 |

**Resultado esperado (como indica la guía, el resultado esperado es cero):**

Con el volumen estimado (~6,000 operaciones/mes), el proyecto se mantiene en **$0**
tanto en el servidor del laboratorio como en la capa gratuita de alternativas como
Render o GitHub Pages para el sitio estático.

**Punto de cruce (dónde deja de ser gratis):**

- Con hasta ~50,000 peticiones/mes, cualquier capa gratuita evaluada cubre el
  proyecto sin costo.
- A partir de volúmenes cercanos a ~2,000,000 de peticiones/mes (fuera de escala
  para el tamaño actual de LostVault), un servicio gestionado por invocación
  empezaría a generar costo, mientras que el servidor del laboratorio seguiría en
  $0 pero sin garantía de disponibilidad fuera del periodo lectivo (dato también
  pendiente de confirmar).

**Costo que no es dinero:**

- Minutos de integración continua: sin costo, repo público en GitHub Actions.
- Tiempo de despliegue manual: por confirmar según el flujo de despliegue al
  servidor del laboratorio.
- Redundancia de conocimiento: por confirmar cuántas personas del equipo saben
  redesplegar el sistema (riesgo de sección 11 de arc42 si es solo una).

## 4. Pendientes a resolver con el equipo antes de cerrar esta evidencia

1. Confirmar con el laboratorio si el servidor es accesible desde fuera de la red
   de la universidad — condición no negociable para la Evidencia S8.
2. Validar los supuestos de volumen (500 usuarios, 10 búsquedas/mes) contra un
   número más realista para la población de la UTB.
3. Si finalmente se usa una alternativa gestionada en vez del servidor del
   laboratorio, verificar su capa gratuita vigente en el momento del despliegue y
   registrar esa verificación en el ADR correspondiente.

