# Amenazas, dependencias y privacidad — LostVault

Fecha: 2026-11-01. Alcance: API FastAPI de `backend/` (desplegada en Vercel) y su relación con el cliente Flutter.

## 1. Tabla de amenazas priorizadas

Prioridad = probabilidad (1–3) × impacto (1–3). Alta ≥ 6, Media 3–5, Baja ≤ 2.

| ID | Amenaza (STRIDE) | Evidencia en el repositorio | P | I | Prior. | Mitigación | Responsable | Estado |
|---|---|---|---|---|---|---|---|---|
| A1 | **Suplantación por verificación de identidad débil.** Cualquier token válido con `sub` no vacío puede reclamar un objeto. | `verify_identity()` en `backend/main.py` devuelve `bool(user_id.strip())` | 3 | 3 | **9 Alta** | Integrar una verificación real de identidad y registrarla en un ADR; hasta entonces, declarar el límite en `docs/aspectos.md` | José Faustino | Pendiente |
| A2 | **Suplantación con token forjado o robado.** El token no exige expiración. | `jwt.decode(..., options={"require": ["sub"]})` no exige `exp` | 2 | 3 | **6 Alta** | Exigir `exp`, usar TTL corto, secreto aleatorio de al menos 32 bytes con rotación, y una prueba de que un token sin `exp` devuelve 401 | Shamara | Pendiente |
| A3 | **Repudio por pérdida de rastro.** Las reclamaciones viven en memoria y se pierden en cada arranque en frío. | `_claims: list` en `backend/main.py` | 3 | 2 | **6 Alta** | PostgreSQL con tabla de reclamaciones y marca de tiempo | Shamara | Pendiente |
| A4 | **Denegación de servicio por agotamiento.** No hay límite de tasa; en pruebas de carga con 200 conexiones falló el 44 % de las peticiones y Vercel bloqueó el tráfico con un 403. | Medición con autocannon contra `/objects` | 3 | 2 | **6 Alta** | Regla de firewall o límite de tasa en Vercel, caché del catálogo y pruebas de carga solo contra un despliegue de pruebas | Shamara | Riesgo registrado |
| A5 | **Doble reclamación entre instancias.** Dos instancias de Vercel pueden aceptar el mismo objeto. | Candado en memoria (`_lock`) que no se comparte entre instancias | 2 | 2 | **4 Media** | `UNIQUE(object_id)` en PostgreSQL; mientras tanto, idempotencia y candado por proceso | José Faustino | Riesgo aceptado |
| A6 | **Dependencia con vulnerabilidades conocidas.** PyJWT 2.7.0 es de 2023. | `backend/requirements.txt`; detalle en la sección 2 | 2 | 2 | **4 Media** | Subir PyJWT a 2.15.0 o superior, correr `pytest` y añadir `pip-audit` a `backend.yml` | Roy | Pendiente |
| A7 | **Secretos en un repositorio público.** | `JWT_SECRET` se lee solo de `os.environ`; el `Dockerfile` no lo define; el CI usa un secreto de prueba | 1 | 3 | **3 Media** | Activar secret scanning y push protection en GitHub; no versionar archivos `.env` | Weller | Verificado; falta activar el escaneo |
| A8 | **CORS demasiado abierto.** Se acepta cualquier origen con `allow_credentials=True`. | `CORSMiddleware` en `backend/main.py`; `test_cors_headers_present` confirma que se refleja el origen | 2 | 1 | **2 Baja** | Limitar a la URL de GitHub Pages y a `localhost`. El riesgo es bajo porque la sesión viaja en la cabecera `Authorization`, no en cookies | Shamara | Pendiente |
| A9 | **Exposición de superficie.** `/docs` y `/metrics` son públicos y la diferencia entre 404 y 409 revela el estado de un objeto. | Rutas de `backend/main.py` | 2 | 1 | **2 Baja** | Aceptar: el catálogo ya es público por diseño; proteger `/metrics` cuando exista base de datos | Roy | Aceptado |

## 2. Resultado del análisis de dependencias

Alcance: las tres dependencias directas de `backend/requirements.txt`. Consulta del 2026-11-01 sobre OSV, GitLab Advisory Database y bases públicas de CVE.

| Paquete | Versión fijada | ¿Existe en PyPI? | Vulnerabilidades conocidas | Decisión |
|---|---|---|---|---|
| `fastapi` | 0.141.1 | Sí (publicada el 29-jul-2026) | Sin CVE propio hallado; hereda los de Starlette | Mantener |
| `uvicorn` | 0.54.0 | Sí | Solo CVE de 2020 (CVE-2020-7694 y CVE-2020-7695), anteriores a esta versión | Mantener |
| `PyJWT` | 2.7.0 | Sí | Varios, por estar por debajo de 2.12, 2.13, 2.14 y 2.15 | **Actualizar a 2.15.0 o superior** |

**PyJWT 2.7.0.** Los CVE relevantes y su aplicabilidad a LostVault:

| CVE | Qué es | ¿Aplica? |
|---|---|---|
| CVE-2026-32597 (7.5, corregido en 2.12.0) | No se valida la cabecera `crit`; se aceptan tokens con extensiones críticas desconocidas | Parcial: la firma HS256 sigue siendo obligatoria, así que quien no tiene el secreto no puede aprovecharlo |
| Familia CVE-2026-1022xx (corregidos en 2.14.0) | Confusión de claves: una clave pública (PEM, DER o JWK) se usa como secreto HMAC | No: el secreto es una cadena propia y `algorithms` está fijado a `["HS256"]`. Queda registrado por si se pasa a claves asimétricas |
| CVE-2026-102270 (4.4, 2.14.0) | Expresión regular con retroceso al comprobar PEM (consumo de CPU) | Bajo: la clave evaluada es nuestro propio secreto, no entrada del atacante |
| CVE-2026-102269 (4.8, 2.14.0) | La firma acepta caracteres no Base64URL | No: no hay lista de revocación por token |
| CVE-2026-48522, 48523, 48524 y 102267 | Fallos del cliente de JWKS (`PyJWKClient`) | No: no se usa `PyJWKClient` |
| CVE-2022-29217 y CVE-2024-53861 | Elección de algoritmo y comparación de `iss` | No: 2.7.0 ya incluye la primera corrección y la app no valida `iss` |

La explotabilidad real es baja por la forma de uso (HS256, algoritmo fijo, secreto en el entorno). Aun así se actualiza, porque la versión acumula muchas correcciones y el cambio es pequeño. Antes de fijar la nueva versión se confirma en PyPI la última estable y se corre `pytest`, ya que `jwt.encode` y `jwt.decode` se usan en la reclamación y en las pruebas de 401.

**Starlette (transitiva de FastAPI).** Dos CVE recientes, ninguno con impacto relevante:
- CVE-2026-48710 (6.5): el encabezado `Host` no se valida antes de reconstruir `request.url`. LostVault no controla acceso por ruta en un middleware, porque la autenticación está en la función de cada ruta.
- CVE-2026-48817 (5.3): `HTTPEndpoint` expone métodos auxiliares si la ruta no declara `methods`. LostVault no usa `HTTPEndpoint`.

**Límites del análisis.**
- La consulta fue manual, porque no se pudo ejecutar `pip-audit` en el entorno de trabajo. Para dejarla reproducible: `pip install pip-audit` y `pip-audit -r requirements.txt` dentro de `backend/`, y pegar la salida como anexo.
- La versión exacta de Starlette instalada no se comprobó (`pip list` en un entorno con las dependencias instaladas).
- Las dependencias de Dart (`pubspec.lock`) no se analizaron todavía (`flutter pub outdated`).

## 3. Privacidad

Marco de referencia: Ley 1581 de 2012 (protección de datos personales en Colombia). Es un análisis técnico del equipo, no asesoría jurídica.

### Datos personales que trata LostVault

| Dato | Dónde aparece | Estado actual |
|---|---|---|
| Identificador de usuario (`sub`) | Token JWT y registro de reclamación | En uso, en memoria |
| Correo institucional | Sesión de prueba del cliente (`estudiante@utb.edu.co`) | Solo datos de prueba |
| Perfil (nombre, carné, tipo) | Módulo `users` | Diseñado, sin