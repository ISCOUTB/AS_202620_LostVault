# Evidencia S12 — Diseño de caché e invalidación

## 1. Qué problema resuelve

El Escenario 4 pide p95 ≤ 2 s en búsquedas con ~200 usuarios concurrentes, y el
Escenario 1 pide consultar fuera de horario sin depender de nadie. La búsqueda
(`GET /objects`) es la operación más frecuente, es pública (no depende del
usuario) y tolera datos un poco viejos (operación C5 en
[consistencia.md](consistencia.md)). Cada petición que no se cachea despierta
la función de Vercel (posible arranque en frío) y, cuando exista, consulta
PostgreSQL ([ADR 0006](../adr/0006-postgresql-fuente-de-verdad.md)).

## 2. Diseño

| Aspecto | Decisión |
|---|---|
| **Dónde** | En la **CDN de Vercel** (Edge Network), delante de la función. No hay caché en memoria del proceso ni Redis (ver §4). |
| **Qué** | Solo las respuestas `200` de `GET /objects` (listado y búsqueda). |
| **Clave** | La URL completa: ruta + query (`status`, `q`). Cada combinación de filtros es una entrada distinta. El cliente debe normalizar `q` (sin espacios sobrantes, en minúsculas) para no fragmentar la caché. |
| **Cuánto tiempo** | `s-maxage=30`: 30 s fresca en la CDN. `stale-while-revalidate=60`: hasta 60 s más se sirve la copia vieja mientras una sola petición la revalida en segundo plano. **Atraso máximo: 90 s.** |
| **Navegador** | `max-age=0`: el navegador no guarda su propia copia. Así hay una sola ventana de datos viejos (la de la CDN) y no dos sumadas. |
| **Patrón** | *Cache-aside* en la CDN: si hay un fallo de caché, la CDN pide a la función y guarda la respuesta según las cabeceras. La aplicación no escribe en la caché. |
| **Lo que nunca se cachea** | Todo lo demás lleva `Cache-Control: no-store` por defecto (middleware `cache_policy`): reclamaciones (`201`, `200`, `4xx`), `/health` (debe reflejar el estado real), `/metrics` y cualquier respuesta que dependa del usuario autenticado. |

Implementación: `OBJECTS_CACHE_CONTROL`, `DEFAULT_CACHE_CONTROL` y el middleware
`cache_policy` en `backend/main.py`. Pruebas en `backend/test_api.py`:
`test_objects_listing_is_cacheable_only_in_the_cdn`,
`test_claim_responses_are_never_cached`,
`test_health_and_metrics_are_not_cached`.

## 3. Política de invalidación

**Política elegida: expiración por tiempo (TTL), sin purga explícita.**

Cuando un objeto cambia (alguien lo reclama o se publica uno nuevo), **no** se
borra la caché: las copias viejas expiran solas en ≤ 90 s. Se elige así porque:

1. **Un dato viejo en el listado no puede causar una entrega indebida.** La
   reclamación (C1) no lee la caché: va a la función con `no-store` y comprueba
   el estado real. Si el objeto ya fue reclamado, responde `409`. Lo peor que
   produce la caché es un `409` a quien vio el objeto como "Disponible" hace
   menos de 90 s.
2. **Purgar al escribir acopla la escritura a la CDN.** La reclamación tendría
   que llamar a la API de Vercel después del commit; si esa llamada falla, hay
   que reintentar (otro fallo parcial más). No vale la pena por 90 s.
3. **Las claves son combinaciones de filtros**: purgar exactamente las URL
   afectadas por un objeto exigiría saber qué búsquedas lo incluían.

**Lectura de lo que yo escribí.** Quien acaba de reclamar o publicar no depende
de la caché: el cliente muestra el cuerpo de la respuesta de su escritura (C4 y
C6) y actualiza ese objeto en su lista local.

**Cuándo cambiar a purga explícita.** Si la prueba de usabilidad del Escenario 2
muestra que los usuarios se confunden porque el objeto que publicaron no aparece
en la búsqueda, se agrega una purga por etiqueta tras el `201` de
`POST /objects`, enviada por el mismo outbox ([eventos.md](eventos.md)) para que
un fallo de la CDN no afecte la publicación.

## 4. Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Caché en memoria del proceso (diccionario en `main.py`) | En Vercel cada instancia tiene su propia memoria y no se reutiliza con el tráfico del proyecto: es la misma causa de R7 (métricas que no acumulan). La tasa de aciertos sería casi cero. |
| Redis (Upstash / Vercel KV) como caché de lectura | Agrega un servicio, credenciales y un modo de fallo más, y aun así la petición despierta la función. La CDN evita también la invocación. Se reconsidera si aparecen lecturas privadas costosas. |
| Cachear también respuestas autenticadas | Riesgo de servir datos de un usuario a otro. No aporta: son pocas y deben ser *read-your-writes*. |

## 5. Fallos de la caché y estampida

- **Estampida al expirar**: `stale-while-revalidate` hace que, al vencer los
  30 s, los usuarios sigan recibiendo la copia vieja mientras **una** petición
  la renueva, en vez de que las 200 peticiones concurrentes despierten la función
  a la vez.
- **Caché vacía o caída de la CDN**: las peticiones llegan a la función; el
  sistema funciona igual, solo más lento. La caché no guarda ningún dato que no
  esté en la fuente de verdad.
- **Función o BD caída**: dentro de la ventana de 90 s se sigue sirviendo el
  listado. Después, la búsqueda falla. No se configura `stale-if-error`; queda
  como mejora para el Escenario 1 si se confirma que la CDN la respeta.

## 6. Cómo verificarlo en producción

Tras desplegar, hacer dos peticiones seguidas a `GET /objects` y revisar la
cabecera `x-vercel-cache` que añade Vercel: la primera debe ser `MISS`, la
segunda `HIT`; pasados 30 s, `STALE`. `POST /v1/objects/{id}/claims` debe
responder siempre con `Cache-Control: no-store`.
