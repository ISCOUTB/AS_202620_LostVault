# Evidencia S14 — Medición de un atributo de calidad

**Atributo medido:** rendimiento de la búsqueda, [Escenario 4](../arc42/10_requisitos_calidad.md#escenario-4--rendimiento).
**Umbral del escenario:** p95 de `GET /objects?q=…` ≤ **2 000 ms** con ~200 usuarios concurrentes.
**Sistema medido:** la API desplegada, `https://backend-nu-self-91.vercel.app` (Vercel, función Python, región `iad1`). No es una medición local ni simulada.
**Fecha:** 2026-11-09 03:52–03:54 UTC (8 nov., 22:52 hora de Bogotá).

## 1. Veredicto

| Medición | p95 medido | Umbral | ¿Cumple? |
|---|---|---|---|
| **B. 200 concurrentes, URL únicas, instancias ya escaladas** (corrida principal) | **1 867 ms** | 2 000 ms | **Sí, con un margen de solo 7 %** |
| A. Primera ráfaga de 200 sobre una sola instancia caliente (Vercel tiene que escalar) | 2 279 ms | 2 000 ms | **No** (+14 %) |
| C. Tiempo de servidor (TTFB) bajo 200 concurrentes | 148 ms | — | Referencia |
| Base secuencial, sin concurrencia (30 búsquedas) | 162 ms | — | Referencia |

**Conclusión:** el Escenario 4 **se cumple en estado estable, pero no con holgura, y no se cumple durante la
primera ráfaga**, mientras Vercel arranca instancias nuevas. 0 errores en 3 000 búsquedas. El umbral queda
**parcialmente demostrado**: la medición es real, pero el generador de carga (un solo navegador) también
mete latencia (§4), así que 1 867 ms es una **cota superior** del p95 que vería un usuario real.

## 2. Método

Se usó `scripts/medicion/carga_navegador.js`, ejecutado en un navegador Chromium 152 (HTTP/2) abierto
en el mismo origen de la API. Cada corrida lanza **5 rondas de 200 búsquedas simultáneas** (1 000
peticiones), con 5 términos que rotan. Se toma el tiempo de extremo a extremo de cada `fetch`
(petición → cuerpo completo) y se calculan percentiles por rango. Los resultados crudos están en
[`s14-resultados-crudos.json`](s14-resultados-crudos.json).

- **A:** misma URL por término, `cache: "no-store"`, justo después de una sola petición de calentamiento.
- **B:** cada URL es única (`&nocache=…`), así que todas llegan al origen y el navegador no las agrupa.
- **C:** mismas URL con la caché por defecto del navegador. Con *Resource Timing* se separa la espera
  en la cola del navegador (`requestStart − startTime`) del tiempo del servidor (`responseStart − requestStart`).

Para repetir la medición con usuarios sostenidos en lugar de ráfagas, y desde una máquina distinta,
está `scripts/medicion/carga_busqueda.py` (solo biblioteca estándar; sale con código 1 si no cumple).

## 3. Resultados

| Corrida | n | p50 | p95 | p99 | máx | Errores | Duración de cada ronda (ms) |
|---|---|---|---|---|---|---|---|
| A | 1 000 | 1 343 | **2 279** | 2 298 | 2 508 | 0 | **2 530**, 1 731, 1 539, 1 594, 1 564 |
| B | 1 000 | 1 428 | **1 868** | 1 897 | 1 919 | 0 | 1 677, 1 674, 1 817, 2 028, 2 139 |
| C total | 1 000 | 3 056 | 5 292 | 5 534 | 5 728 | 0 | — |
| C cola en el navegador | 1 000 | 2 919 | 5 144 | 5 415 | 5 607 | — | — |
| C servidor (TTFB) | 1 000 | 119 | **148** | 252 | 319 | — | — |

Después de la carga, `GET /metrics` reportó `{"/objects": {"p95_ms": 1.07, "samples": 364}}`: dentro
del proceso, la búsqueda tarda alrededor de 1 ms.

## 4. Interpretación (sensibilidades y compromisos)

1. **El servidor no es el cuello de botella.** Bajo 200 concurrentes, el servidor responde en un p95
   de 148 ms, y la búsqueda en sí tarda alrededor de 1 ms. El resto del tiempo es espera en cola.
2. **Punto de sensibilidad: escalado en frío.** La corrida A solo falla en su primera ronda (2,5 s, frente
   a ~1,6 s en las siguientes), cuando Vercel tiene que levantar instancias nuevas. El p95 del Escenario 4
   es sensible al número de instancias calientes en el momento del pico. Ver **R11** en
   [§11](../arc42/11_riesgos.md).
3. **La táctica de caché del Escenario 4 no está activa en producción.** El diseño
   ([cache.md](../datos/cache.md)) espera que la CDN atienda las búsquedas repetidas, pero las
   3 000 peticiones de carga y una sonda de 5 peticiones idénticas separadas 1 s devolvieron
   `x-vercel-cache: MISS` y `age: 0`. Todas las búsquedas llegan a la función. La causa aún no está
   determinada. Ver **R12**.
4. **Límite del instrumento.** En la corrida C, Chrome serializa las URL idénticas en vuelo (bloqueo de
   caché), lo que infla el total a 5,3 s sin que el servidor sea más lento. Por eso el veredicto se
   basa en B. Un solo cliente no equivale a 200 usuarios en 200 redes distintas. Ver **R13**.
5. **Hallazgo lateral sobre R7.** Bajo carga, `/metrics` sí acumuló 364 muestras: las métricas en
   memoria acumulan cuando la instancia se reutiliza. Siguen sin ser globales (cada instancia tiene las
   suyas), así que R7 sigue abierto, pero su descripción se precisa.

## 5. Qué haría que el escenario se cumpla con margen

- Que la caché de la CDN funcione (R12). Las búsquedas repetidas ya no despertarían a la función, y
  eso también reduce los arranques en frío.
- Repetir con `carga_busqueda.py` desde fuera del navegador, para quitar el sesgo del instrumento.
- Si el pico de A se confirma, evaluar el escalado de Vercel (concurrencia de la función) frente a su costo
  ([estimación de costo](../despliegue/estimacion-costo-mensual.md)).
