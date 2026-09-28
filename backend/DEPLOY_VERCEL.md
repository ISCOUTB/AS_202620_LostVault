# Despliegue del Backend en Vercel — LostVault API

El backend FastAPI de LostVault se encuentra desplegado y operativo en **Vercel** como una aplicación Serverless con soporte nativo Zero-Config.

---

## 1. URL de Producción y Endpoints Operativos

* **URL Base de Producción:** [`https://backend-nu-self-91.vercel.app`](https://backend-nu-self-91.vercel.app)
* **Proyecto en Vercel:** `shamara-llorente-s-projects/backend`

### Endpoints Disponibles

| Endpoint | Método | URL de acceso | Descripción |
|---|---|---|---|
| **Root** | `GET` | [`https://backend-nu-self-91.vercel.app/`](https://backend-nu-self-91.vercel.app/) | Estado y enlaces principales de la API |
| **Health Check** | `GET` | [`https://backend-nu-self-91.vercel.app/health`](https://backend-nu-self-91.vercel.app/health) | Verificación de disponibilidad del servicio (`{"status":"ok"}`) |
| **Documentación Swagger** | `GET` | [`https://backend-nu-self-91.vercel.app/docs`](https://backend-nu-self-91.vercel.app/docs) | Interfaz interactiva de OpenAPI / Swagger UI |
| **Listado y Búsqueda** | `GET` | [`https://backend-nu-self-91.vercel.app/objects`](https://backend-nu-self-91.vercel.app/objects) | Consulta de catálogo y filtros (`?q=termo`, `?status=available`) |
| **Métricas p95** | `GET` | [`https://backend-nu-self-91.vercel.app/metrics`](https://backend-nu-self-91.vercel.app/metrics) | Medición de percentiles de latencia para el Escenario 4 |
| **Reclamar Objeto** | `POST` | `https://backend-nu-self-91.vercel.app/v1/objects/{objectId}/claims` | Flujo de reclamación protegido con JWT (`Bearer`) |

---

## 2. Arquitectura de Despliegue

* **Runtime:** Python 3.12 Serverless Function administrada por Vercel.
* **Detección Zero-Config:** Vercel detecta automáticamente el framework FastAPI a través de `backend/requirements.txt` y `backend/main.py:app` sin requerir reescrituras complejas ni adaptadores intermedios.
* **CORS:** Habilitado mediante `CORSMiddleware` en `backend/main.py` para admitir solicitudes cross-origin desde Flutter Web (GitHub Pages / localhost) y clientes móviles.
* **Observabilidad:** Cada solicitud genera encabezados de trazabilidad `X-Request-Id` y registra latencias en ventana deslizante para computar el percentil $p95$ en `/metrics`.

---

## 3. Variables de Entorno en Vercel

| Variable | Estado en Producción | Descripción |
|---|---|---|
| `JWT_SECRET` | Configurada | Secreto criptográfico para firma y validación de tokens JWT (HS256). Es obligatoria durante el arranque (`lifespan`). |
| `LOG_LEVEL` | `INFO` (por defecto) | Nivel de logging estructurado en JSON. |




