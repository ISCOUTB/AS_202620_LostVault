# Estimación de costo mensual y métrica operativa — LostVault

Evidencia S8 — Despliegue y operación

## 1. Dónde vive cada pieza (decisión previa al costo)

Siguiendo la advertencia de la guía ("elegir la plataforma antes que el escenario" es
el primer error frecuente), esta decisión se toma primero, pieza por pieza, y el
costo es consecuencia de ella, no al revés.

| Pieza | Dónde se ejecuta | Criterio que lo decide |
|---|---|---|
| Sitio (Flutter web) | GitHub Pages | Estático, repo público → gratis, sin tarjeta |
| API (FastAPI, `objects`/`claims`) | Vercel (función serverless, Python 3.12) | Plan Hobby gratuito y sin tarjeta; URL pública accesible desde fuera de la universidad; despliegue con `npx vercel --prod` o desde Git. El tráfico esperado es bajo y esporádico, lo que encaja con un modelo por invocación |
| Datos (`objects`, `claims`) | En memoria del proceso de la API | En este corte no hay base de datos externa. Los datos no persisten entre instancias ni reinicios (ver limitaciones, sección 2) |
| Ficheros/objetos | No aplica en este corte | El modelo `LostObject` actual no tiene campo de foto; si se agrega, iría a almacenamiento de objetos (nunca al disco de la función, que es de solo lectura salvo `/tmp`) |
| Trabajos programados | GitHub Actions `schedule` (si aplica) | Los cron de Vercel Hobby se limitan a una ejecución por día; Actions no tiene ese tope en repos públicos |
| Pipeline | GitHub Actions | Repo público → no consume cuota de minutos |

**Alternativa considerada: Render (plan gratuito).** Corre la API como proceso continuo,
pero se suspende tras 15 minutos sin tráfico y tarda cerca de un minuto en despertar, y
su disco es efímero. Las fuentes discrepan sobre si exige tarjeta al registrarse. Se
eligió Vercel porque no pide tarjeta y ya estaba operativo; el detalle de la decisión
va en el ADR de plataforma.

## 2. Métrica ligada al escenario de calidad

**Métrica elegida:** latencia p95 de `GET /objects` (búsqueda).

**Por qué esta métrica:** el escenario de calidad de la semana 2 exige que el 95 %
de las búsquedas respondan en ≤ 2 s con 200 usuarios concurrentes. El criterio 2 de la
guía usa exactamente ese número para decidir si una pieza puede ser función ("si el p95
que declaraste es menor que el arranque en frío medido, la pieza no es candidata"). En
Vercel la API sí corre como función, así que esta métrica es la que dice si esa decisión
se sostiene: el arranque en frío de una función dormida compite con el presupuesto de 2 s.

**Cómo se consulta:** `GET /metrics` en la URL desplegada devuelve el p95 por endpoint,
calculado sobre una ventana deslizante de las últimas peticiones. Cada petición deja
además un log JSON con `endpoint`, `status_code` y `duration_ms`, y un encabezado
`X-Request-Id` para trazabilidad.

**Limitaciones que hay que declarar:**

- Las mediciones viven en la memoria de cada instancia de la función. Con más de una
  instancia, o tras un reinicio o archivado, el p95 de `/metrics` cambia o se reinicia,
  así que es un indicador por instancia y no una medición global.
- Por la misma razón, los objetos y reclamaciones en memoria no se comparten entre
  instancias ni sobreviven a un redespliegue.
- Las funciones sin invocar se archivan (en producción, pasadas unas dos semanas) y la
  primera petición posterior tarda al menos un segundo más de lo normal. Esa primera
  petición puede superar el objetivo de 2 s aunque el p95 general lo cumpla.
- Los logs de Vercel Hobby se conservan solo durante una hora, por lo que la captura de
  evidencia debe tomarse justo después de generar tráfico.

## 3. Estimación de costo mensual

Los cuatro números que pide la guía, con supuestos explícitos:

| # | Número | Supuesto usado | Fuente del supuesto |
|---|---|---|---|
| 1 | Operaciones al mes | ~500 usuarios activos × ~10 búsquedas + ~1 publicación cada uno ≈ **6.000 invocaciones/mes** | Estimado; ajustar con el tamaño real esperado de usuarios de la UTB |
| 2 | Tamaño de datos almacenados | `LostObject` sin foto (id, title, description, status) < 1 KB/registro → **pocos MB acumulados, en memoria** | Modelo real en `lost_object.dart` |
| 3 | Tráfico de salida | Respuestas JSON pequeñas, sin imágenes → **decenas de MB/mes** | Derivado de (2) |
| 4 | Tiempo de ejecución | Modelo por invocación: CPU activa ≈ 50 ms por petición × 6.000 ≈ **5 minutos de CPU al mes** (0,08 h) | Supuesto de 50 ms por petición; la espera de E/S no cuenta como CPU activa |

**Capa gratuita de Vercel Hobby (verificada el 27/09/2026 en la documentación de
Vercel):** 1 millón de invocaciones, 4 horas de CPU activa y 360 GB-hora de memoria
aprovisionada al mes, sin tarjeta ni vencimiento. Es de uso personal y no comercial,
condición que un proyecto académico cumple. Estas cuotas cambian sin aviso, por lo que
la verificación se repite y se registra en el ADR de plataforma.

**Resultado (como indica la guía, el resultado esperado es cero):** con ~6.000
invocaciones al mes se usa cerca del 0,6 % de la cuota de invocaciones y ~2 % de la de
CPU activa. El costo mensual es **$0** para la API (Vercel Hobby) y para el sitio
(GitHub Pages).

**Punto de cruce (dónde deja de ser gratis):**

- La cuota que se agota primero es la de invocaciones: **1.000.000 al mes**, unas 166
  veces el volumen estimado. Al superarla, el plan Hobby no cobra: las funciones dejan de
  ejecutarse hasta el siguiente ciclo.
- Para seguir sin interrupción habría que pasar a Vercel Pro, desde **$20 al mes por
  integrante** (incluye $20 de crédito de uso), y después pagar por CPU activa y memoria
  aprovisionada.
- Para el tamaño actual de LostVault ese punto queda fuera de escala.

**Costos indirectos (no monetarios):**

- **Minutos de integración continua:** sin costo, repo público en GitHub Actions.
- **Tiempo de despliegue:** un comando (`npx vercel --prod`) desde la carpeta `backend`,
  o despliegue automático al hacer push a `main` si se conecta el repositorio en
  Vercel.
- **Redundancia de conocimiento:** el proyecto de Vercel está en la cuenta personal de
  una integrante. Si ella no está disponible, el resto del equipo no puede redesplegar
  salvo que se comparta el acceso (riesgo de la sección 11 de arc42).
- **Arranque en frío:** la primera petición tras un periodo sin tráfico es más lenta,
  y ese costo lo asume el usuario, no el presupuesto.
