# Amenazas, dependencias y privacidad — LostVault

Fecha: 2026-11-01. Alcance: API FastAPI de `backend/` (desplegada en el servidor que exige la universidad, https://panel.iscoutb.dev/) y su relación con el cliente Flutter.

> Nota de despliegue: el equipo probó Vercel en una etapa intermedia, pero el despliegue final es el servidor de la universidad. Las amenazas de este documento se evalúan contra ese servidor. Lo que se midió en Vercel se cita solo como antecedente y se indica cuando es así.

## 1. Tabla de amenazas priorizadas

Prioridad = probabilidad (1–3) × impacto (1–3). Alta ≥ 6, Media 3–5, Baja ≤ 2.

| ID | Amenaza (STRIDE) | Evidencia en el repositorio | P | I | Prior. | Mitigación | Responsable | Estado |
|---|---|---|---|---|---|---|---|---|
| A1 | **Suplantación por verificación de identidad débil.** Cualquier token válido con `sub` no vacío puede reclamar un objeto. | `verify_identity()` en `backend/main.py` devuelve `bool(user_id.strip())` | 3 | 3 | **9 Alta** | Integrar una verificación real de identidad y registrarla en un ADR; hasta entonces, declarar el límite en `docs/aspectos.md` | José Faustino | Pendiente |
| A2 | **Suplantación con token forjado o robado.** Quien obtenga `JWT_SECRET` puede emitir sesiones válidas, y no hay revocación de tokens. | `exp` ya es obligatorio en el JWT de `backend/main.py` (registro S12 de `docs/ia.md`, con dos pruebas). El riesgo restante es el secreto | 1 | 3 | **3 Media** | Secreto aleatorio de al menos 32 bytes guardado solo en variables de entorno del servidor (nunca en el repositorio), TTL corto y rotación del secreto; comprobar en el código que `exp` sigue exigido | Shamara | Parcial: `exp` obligatorio; **por confirmar** dónde se configura `JWT_SECRET` en el panel |
| A3 | **Repudio por pérdida de rastro.** Las reclamaciones viven en memoria y se pierden en cada reinicio del proceso o del servidor. | `_claims: list` en `backend/main.py` | 3 | 2 | **6 Alta** | Base de datos con tabla de reclamaciones y marca de tiempo (PostgreSQL si el servidor de la universidad la ofrece) | Shamara | Pendiente; **por confirmar** si hay base de datos disponible en el panel |
| A4 | **Denegación de servicio por agotamiento.** No hay límite de tasa en la aplicación. Antecedente: en una prueba de carga con 200 conexiones contra `/objects` (medida con autocannon sobre el despliegue en Vercel) falló el 44 % de las peticiones y Vercel bloqueó el tráfico con un 403. | Medición con autocannon contra `/objects` (Vercel, antes del cambio de servidor) | 3 | 2 | **6 Alta** | Límite de tasa en la aplicación o en el proxy inverso del servidor, caché del catálogo (cabeceras ya implementadas en S12) y pruebas de carga solo contra un entorno de pruebas y con el permiso de quien administra el servidor de la universidad | Shamara | Parcial: cabeceras de caché implementadas; falta límite de tasa. La prueba de carga **no se ha repetido** contra panel.iscoutb.dev |
| A5 | **Doble reclamación entre procesos.** Si el servidor ejecuta más de un proceso (workers) de la API, cada uno tiene su propio candado y pueden aceptar el mismo objeto. | Candado en memoria (`_lock`) que no se comparte entre procesos | 2 | 2 | **4 Media** | `UNIQUE(object_id)` en la base de datos; mientras tanto, ejecutar un solo proceso, idempotencia y candado por proceso | José Faustino | Riesgo aceptado; **por confirmar** cuántos workers corren |
| A6 | **Dependencia con vulnerabilidades conocidas.** PyJWT 2.7.0 es de 2023. | `backend/requirements.txt`; detalle en la sección 2 | 2 | 2 | **4 Media** | Subir PyJWT a 2.15.0 o superior, correr `pytest` y añadir `pip-audit` a `backend.yml` | Roy | Pendiente |
| A7 | **Secretos en un repositorio público.** | `JWT_SECRET` se lee solo de `os.environ`; el `Dockerfile` no lo define; el CI usa un secreto de prueba | 1 | 3 | **3 Media** | Activar secret scanning y push protection en GitHub; no versionar archivos `.env` | Weller | Verificado; falta activar el escaneo |
| A8 | **CORS demasiado abierto.** Se acepta cualquier origen con `allow_credentials=True`. | `CORSMiddleware` en `backend/main.py`; `test_cors_headers_present` confirma que se refleja el origen | 2 | 1 | **2 Baja** | Limitar a la URL de GitHub Pages y a `localhost`. El riesgo es bajo porque la sesión viaja en la cabecera `Authorization`, no en cookies | Shamara | Pendiente |
| A9 | **Exposición de superficie.** `/docs` y `/metrics` son públicos y la diferencia entre 404 y 409 revela el estado de un objeto. | Rutas de `backend/main.py` | 2 | 1 | **2 Baja** | Aceptar: el catálogo ya es público por diseño; proteger `/metrics` cuando exista base de datos | Roy | Aceptado |
| A10 | **Elevación de privilegios por acceso al panel o al servidor.** Quien tenga las credenciales del panel puede redesplegar, leer variables de entorno (incluido `JWT_SECRET`) y alterar la API. | Despliegue en https://panel.iscoutb.dev/ (valoración provisional, sin evidencia en el código) | 2 | 3 | **6 Alta** | Credenciales del panel individuales y no compartidas por chat, lista corta de quienes pueden redesplegar, verificar que el servidor sirva solo por HTTPS y rotar `JWT_SECRET` si alguien sale del equipo | Weller | **Por confirmar:** quién tiene acceso al panel, si hay HTTPS forzado y si el panel ofrece segundo factor |

## 2. Resultado del análisis de dependencias

Alcance: las tres dependencias directas de `backend/requirements.txt`. Consulta del 2026-11-01 sobre OSV, GitLab Advisory Database y bases públicas de CVE. Este análisis no depende de la plataforma de despliegue.

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
- No se analizaron `mensajeria/` (simulador local de eventos), `api/` (implementación alternativa no desplegada, riesgo R10 en `docs/arc42/11_riesgos.md`) ni `requirements-dev.txt`.

## 3. Privacidad

Marco de referencia: Ley 1581 de 2012 (protección de datos personales en Colombia). Es un análisis técnico del equipo, no asesoría jurídica.

### Datos personales que trata LostVault

| Dato | Dónde aparece | Estado actual |
|---|---|---|
| Identificador de usuario (`sub`) | Token JWT y registro de reclamación | En uso, en memoria |
| Correo institucional | Sesión de prueba del cliente (`estudiante@utb.edu.co`) | Solo datos de prueba |
| Perfil (nombre, carné, tipo) | Módulo `users` | Diseñado, sin conectar a otros módulos |
| Evidencia de verificación de identidad | Módulo `identity_verification` | Diseñado, sin tratamiento real; sería el dato más sensible |
| Foto del objeto | Módulo de objetos | No existe en `LostObject` hoy |

### Decisiones de privacidad

- **Minimización.** La API solo conoce el `sub` del token. No guarda correo ni nombre, y así se mantiene hasta que un escenario justifique más.
- **Logs.** El formateador JSON escribe una lista cerrada de campos (`request_id`, `endpoint`, `method`, `status_code`, `duration_ms`, `event`) y registra la ruta con `{object_id}`, no la real. La prueba `test_logs_never_contain_the_token` garantiza que el token no aparece.
- **Repositorio público.** Solo se versionan datos de prueba: nunca datos reales de estudiantes ni capturas con correos reales. Lo mismo aplica a lo que se pegue en herramientas de IA y a `docs/ia.md`.
- **Retención.** Hoy los datos viven en memoria y se pierden al reiniciar, lo que limita la retención pero elimina el rastro (A3). Al pasar a una base de datos se fija por escrito el plazo de conservación de las reclamaciones.
- **Ubicación del tratamiento.** La API corre en el servidor de la universidad, que queda como infraestructura institucional y no en un proveedor externo de nube. Dónde está físicamente el servidor y quién lo administra **está por confirmar**; si resulta estar en Colombia y bajo la universidad, se reduce la preocupación por transferencia internacional que existía con Vercel. Los registros del servidor (accesos, IP) los controla quien administra el panel, y conviene saber por cuánto tiempo los conserva.

### Brechas conocidas

1. No existe aviso de privacidad ni texto de autorización del titular en el cliente.
2. No hay procedimiento para que un usuario consulte, corrija o elimine sus datos.
3. No hay plazo de retención definido para las reclamaciones.
4. Cuando `identity_verification` trate evidencia real, habrá que revisar de nuevo si se separa como servicio por ser el dato más sensible.
5. No se conoce la política de registros y copias de seguridad del servidor de la universidad.

## Por confirmar antes de entregar

Estos puntos dependen del servidor de la universidad y no se pueden deducir del repositorio:

1. Dónde y cómo se configura `JWT_SECRET` en el panel (A2).
2. Si hay base de datos disponible y de qué tipo (A3).
3. Cuántos procesos o workers ejecutan la API (A5).
4. Si el servidor fuerza HTTPS y si el panel tiene segundo factor; quién tiene acceso (A10).
5. Ubicación física del servidor y política de registros (sección 3).
6. Si se repetirá la prueba de carga contra panel.iscoutb.dev y con qué permiso (A4).

## Fuentes

- [OSV — PYSEC-2026-120 (PyJWT, CVE-2026-32597)](https://osv.dev/PYSEC-2026-120)
- [Historial de CVE de PyJWT (releasealert)](https://releasealert.dev/pypi/PyJWT/cves)
- [CVE-2026-48710 (Starlette y FastAPI)](https://tuxcare.com/cve-tracker/cve/details/cve-2026-48710/)
- [CVE-2026-48817 (Starlette)](https://www.sentinelone.com/vulnerability-database/cve-2026-48817/)
- [Uvicorn — CVE-2020-7694 (GitLab Advisory Database)](https://advisories.gitlab.com/pkg/pypi/uvicorn/CVE-2020-7694/)
