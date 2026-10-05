# Auditoría de erosión y verificación de dependencias — backend

Evidencia S9 — Generación con IA: verificación y erosión

Este documento complementa `docs/ddd/mapa_contextos.md` (semana 6) y cubre dos de los
puntos que pide la evidencia: la verificación de lo que el modelo generativo trajo
consigo (dependencias y credenciales) y la auditoría de erosión arquitectónica sobre
`backend/`, código construido con apoyo de IA que el mapa de contextos original no
alcanzó a cubrir porque no existía todavía.

## 1. Verificación de dependencias

Las tres dependencias declaradas en `backend/requirements.txt` se verificaron contra
PyPI el 04/10/2026:

| Paquete | Versión declarada | ¿Existe en PyPI? | Observación |
|---|---|---|---|
| `fastapi` | 0.141.1 | Sí, publicada el 2026-07-29 | Versión real y vigente |
| `uvicorn` | 0.54.0 | Sí, existe | Versión real |
| `PyJWT` | 2.7.0 | Sí, existe | Es real, pero data de junio de 2023 — tres años más vieja que las otras dos dependencias. Como maneja la autenticación del sistema, conviene revisar si hay una versión más reciente con parches de seguridad |

**Resultado:** ninguna dependencia es inventada. Se descarta el riesgo de que el modelo
haya propuesto un paquete que no existe y que alguien pudiera registrar después con ese
mismo nombre para inyectar código malicioso (*slopsquatting*).

**Pendiente:** actualizar `PyJWT` a una versión más reciente, o justificar por qué se
mantiene fija en 2.7.0.

## 2. Verificación de credenciales

Se revisaron `backend/main.py` y `backend/Dockerfile` en busca de secretos en texto
plano:

- `backend/main.py`: el secreto JWT se obtiene únicamente de `os.environ.get("JWT_SECRET")`
  en la función `jwt_secret()`. Si la variable no está definida, la aplicación falla al
  arrancar (`lifespan`) en vez de usar un valor por defecto. No hay ningún secreto
  hardcodeado en el archivo.
- `backend/Dockerfile`: no fija `JWT_SECRET`. Solo deja un comentario (`# JWT_SECRET debe
  sobreescribirse en ejecución`) indicando que debe inyectarse en tiempo de ejecución.

**Resultado:** no se encontraron credenciales en el código ni en los archivos de
configuración versionados. Como el repositorio es público, esto es importante: cualquier
secreto hardcodeado quedaría expuesto permanentemente en el historial de commits, incluso
si se corrige después.

## 3. Auditoría de erosión arquitectónica

### 3.1 Qué se auditó

El mapa de contextos de la semana 6 (`docs/ddd/mapa_contextos.md`) establece, para el
código Dart, la regla de dueño único: cada dato tiene un solo módulo con permiso de
escritura, y los demás acceden solo a través de su carpeta `public/`. El backend en
Python (`backend/main.py`), construido después con apoyo de IA, es código nuevo que esa
auditoría no alcanzó a cubrir.

### 3.2 Hallazgo

`backend/main.py` no reproduce la estructura modular (`domain/`, `application/`,
`infrastructure/`, `public/`) que el equipo adoptó en el ADR 0001. Todo el backend —
rutas, datos en memoria y lógica de negocio — vive en un único archivo, sin ninguna
frontera declarada entre los conceptos de `objects` y `claims`.

La consecuencia concreta aparece en el endpoint de reclamación:

```python
@app.post("/v1/objects/{object_id}/claims", status_code=201)
async def create_claim(object_id: str, request: Request):
    ...
    obj["status"] = "claimed"
```

Esta línea modifica directamente el diccionario `_objects` desde la misma función que
procesa la reclamación. En el Dart, la misma operación pasa por la frontera pública de
`objects` (`_objects.markAsClaimed(...)` en `claim_object_use_case.dart`), respetando
que `objects` es el único módulo con permiso de escritura sobre el estado del objeto. En
el backend Python esa frontera no existe: no hay ninguna regla que impida que el código
de `claims` escriba directamente sobre el dato de `objects`, porque no hay módulos
separados en absoluto.

Esto es el mismo tipo de problema que la NC3 del mapa de contextos (acoplamiento entre
contextos), pero más severo: en Dart el acoplamiento ocurre pese a que existen los
módulos y sus fronteras (`search` importa el modelo de `objects` en vez de tener el
propio); en el backend Python no llegó a construirse ninguna frontera que pudiera
respetarse o violarse.

### 3.3 No conformidad

Se registra como continuación de la numeración de `docs/ddd/mapa_contextos.md`:

| # | No conformidad | Plan de corrección |
|---|---|---|
| NC6 | `backend/main.py` no reproduce la separación modular del ADR 0001; el endpoint de reclamación escribe directamente sobre el dato de `objects` sin pasar por ninguna frontera equivalente a `public/`. | Separar `main.py` en al menos dos módulos (por ejemplo `objects_store.py` y `claims_routes.py`), donde solo el primero pueda modificar el estado de un objeto, y el segundo lo invoque a través de una función expuesta, replicando en Python la misma regla de dueño único que ya rige en Dart. |

### 3.4 Por qué ocurrió

El backend se generó como un esqueleto nuevo y rápido para cumplir la Evidencia S8
(URL desplegada, health check, métrica, costo), priorizando tener algo funcionando
sobre aplicarle la misma disciplina modular que el equipo ya había decidido para el
cliente Flutter. Es un ejemplo directo de lo que advierte la guía de esta semana: el
volumen de código generado creció más rápido que la revisión, y un límite de propiedad
de datos se cruzó sin que nadie lo notara hasta esta auditoría.

## 4. Resumen para la evidencia S9

- **Dependencias:** verificadas, ninguna inventada; pendiente actualizar `PyJWT`.
- **Credenciales:** no se encontraron en el código versionado.
- **Erosión:** un hallazgo nuevo (NC6) — el backend no respeta la separación de dueño
  único que el resto del proyecto sí aplica, con un ejemplo concreto y su corrección
  propuesta.