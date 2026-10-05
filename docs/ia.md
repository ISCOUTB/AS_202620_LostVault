# Uso de IA en el Proyecto

Este documento registra el uso de herramientas de inteligencia artificial durante el desarrollo del proyecto, con fines de transparencia académica.

## Herramienta utilizada

Claude (Anthropic) y ChatGPT (OpenAI).

## Registro S1 — 2026-08-08

Se utilizó IA para apoyar la redacción y estructuración de la ficha del problema y del aspecto de calidad inicial. El equipo revisó el resultado y mantuvo las decisiones de alcance y prioridad.

**Aceptado:** apoyo de redacción y organización del contenido.

**Rechazado:** propuestas de ampliar el alcance a integraciones externas con sistemas universitarios, porque el alcance del equipo define LostVault como un sistema independiente.

## Registro S2 — 2026-08-16

Se utilizó IA para revisar la redacción de escenarios de calidad, organizar restricciones y detectar inconsistencias entre la estructura arc42 y los criterios de revisión.

**Aceptado:** mejora de claridad, estructura de escenarios y formulación de medidas numéricas.

**Rechazado:** sugerencias que introducían servicios externos no definidos en el contexto del proyecto, porque no correspondían al alcance actual.

## Registro S3 — 2026-08-23/24

Se utilizó IA para revisar la sección 4 de arc42, comparar estilos arquitectónicos contra los escenarios del equipo, proponer la estructura modular y revisar la trazabilidad entre aspectos, escenarios y ADR.

**Aceptado:** vincular la estrategia a los cuatro escenarios, documentar tácticas por escenario, explicitar impacto/riesgo y mejorar la estructura de módulos.

**Rechazado:** convertir LostVault en microservicios, porque aumentaría la complejidad operativa para un equipo pequeño y no es necesaria para los requisitos actuales.

## Criterio del equipo sobre el uso de IA

La IA se utiliza como apoyo para redacción, exploración de alternativas, revisión y estructuración. Las decisiones de arquitectura, alcance y diseño son discutidas y validadas por el equipo antes de incorporarse al repositorio.

## Registro S6 — 2026-09-13

Se utilizó IA para revisar la tabla módulo → datos con dueño único
(`docs/ddd/tabla_modulo.md`) y contrastarla con el código del corte vertical.
La IA no tiene acceso directo al repositorio, por lo que trabajó solo con los
archivos y capturas que el equipo le compartió.

**Trabajo realizado y motivo:**

1. Se revisó la tabla original y se detectó una imprecisión: la fila de
   `claims` presentaba a `objects` como lector de datos de reclamaciones,
   cuando el estado del objeto es dato propio de `objects` y lo que ocurre es
   que `claims` le ordena cambiarlo. Se reformuló como comando y no como
   lectura, para preservar la regla de dueño único.
2. Se verificó esa relación contra `claim_object_use_case.dart`: todos los
   imports pasan por `public/` y el cambio de estado se hace con
   `_objects.markAsClaimed(object.id)`.
3. Se propuso una ubicación para la tabla. El equipo adoptó
   `docs/ddd/tabla_modulo.md`, con un archivo por parte de la evidencia.
4. Se redactó la justificación de cada fila para poder defender la tabla en la
   sustentación, y se resumió el mapa de contextos y la lista de no
   conformidades ya elaborados por el equipo para preparar la exposición.

**Aceptado:** la reformulación de `claims` → `objects` como comando y la
carpeta `docs/ddd/`.

**Rechazado:** ubicar la tabla dentro de la sección 8 de arc42 o en un único
archivo `evidencia_s6.md`; el equipo prefirió un archivo por parte.

**Limitación:** la IA dio la tabla por verificada tras revisar un único
archivo. La auditoría posterior del equipo (`mapa_contextos.md`) mostró que
varias relaciones de la tabla no existían aún en el código (`users` aislado,
`objects` sin leer `authentication`, `AuthUser` sin token) y las registró como
no conformidades NC1 a NC4. La verificación de la IA solo cubría la relación
`claims` → `objects`.

## Registro S7 — 2026-09-20

Se utilizó IA para inspeccionar el corte vertical existente, relacionar su
caso de uso de reclamación con una frontera HTTP futura y preparar la evidencia
solicitada para interfaces y contratos. Se revisaron los materiales de la
semana y se distinguió entre sus instrucciones académicas y las decisiones que
corresponden al equipo.

**Trabajo realizado y motivo:**

1. Se agregó `docs/contracts/lostvault-api.yaml`, una especificación OpenAPI
   3.1.1 con versión `1.0.0`, para que el acuerdo de `POST
   /v1/objects/{objectId}/claims` sea una fuente de verdad versionable antes de
   que exista un proveedor HTTP. La operación se eligió porque corresponde al
   flujo ya ejecutable de `ClaimObjectUseCase`, no a una integración externa
   inventada.
2. Se agregó `test/api_contract_test.dart`. La prueba expresa los requisitos
   del consumidor: ruta protegida, parámetro `objectId`, respuesta `201` con
   `objectId`, `userId` y `verified`, y los fallos `401`, `404`, `409` y `422`.
   Se hizo para que una modificación incompatible del contrato falle de forma
   visible. No se presentó como prueba de integración porque el repositorio no
   tiene un proveedor HTTP desplegado.
3. Se actualizó `.github/workflows/flutter.yml` para ejecutar explícitamente
   esa prueba en `push` y `pull request`, de modo que el cambio incompatible
   bloquee el merge.
4. Se agregó el ADR 0002. Se aceptó HTTP síncrono porque el usuario necesita
   saber en la misma interacción si la identidad fue verificada y el objeto
   quedó reservado. También se documentó el costo: si el proveedor no está
   disponible, la reclamación no puede completarse entonces. Se rechazó usar
   eventos asíncronos ahora porque exigiría estado pendiente, notificaciones,
   idempotencia y manejo de duplicados que el caso de uso actual no implementa.
5. Se actualizó el README para conectar contrato, prueba, pipeline y ADR, y
   facilitar la revisión contra el repositorio.

**Aceptado:** usar OpenAPI para una frontera HTTP futura, manteniendo la
trazabilidad con el caso de uso real y declarando la limitación del proveedor
in-memory.

**Rechazado:** afirmar que ya existe una API remota o una integración
asíncrona. El código actual no las implementa; documentarlas como existentes
haría que la evidencia no correspondiera con el repositorio.

**Complemento (sesión de apoyo con Claude):**

- Se esbozó un contrato alternativo para el módulo `objects` (`GET /objects`,
  `GET /objects/{id}`, `POST /objects`) a partir de `lost_object.dart`. No se
  adoptó: el equipo eligió el flujo de reclamación por tener más modos de fallo
  bien definidos.
- Se advirtió que `LostObject` no tiene campo de foto, aunque la tabla
  módulo → datos lo lista como dato de `objects`. Es una inconsistencia entre
  documentación y código que queda pendiente de registrar.
- Se discutió que FastAPI, por defecto, genera OpenAPI desde el código
  (code-first), lo cual difiere de API-first. Se recomendó mantener el YAML
  escrito a mano como fuente de verdad y comparar contra él el OpenAPI que
  genere FastAPI. Es una recomendación; no consta como implementada.

## Registro S8 — 2026-09-27

Se utilizó IA para preparar la estimación de costo y la métrica de la evidencia
de despliegue y operación, y para contrastar las decisiones de plataforma con
la Guía de despliegue y costos.

**Trabajo realizado y motivo:**

1. Se redactó `docs/despliegue/estimacion-costo-mensual.md` siguiendo el
   apartado «Cómo estimar el costo mensual»: decisión pieza por pieza, los
   cuatro números con sus supuestos (≈6.000 operaciones al mes, datos de pocos
   MB, tráfico de decenas de MB), resultado de $0 y punto de cruce. Se pidió la
   guía del curso antes de calcular, en lugar de estimar con precios genéricos
   de proveedores.
2. Se definió la métrica: latencia p95 de `GET /objects`, ligada al escenario
   de rendimiento (95 % de las búsquedas en ≤ 2 s).
3. Se propuso un esqueleto de backend FastAPI con `/health`, `/metrics`, logs
   JSON y siete pruebas (100 % de cobertura local). Antes de subirlo se
   corrigió un error de la propia IA: los campos de los logs no se imprimían.
   El PR #11 falló el Quality Gate de SonarCloud (0 % de cobertura sobre las
   líneas nuevas) y se cerró sin fusionar, porque una compañera ya había
   subido a `main` el backend definitivo. Ese esqueleto no forma parte del
   repositorio.
4. Se verificó la capa gratuita de Render (suspensión tras 15 minutos, cerca
   de un minuto de arranque, disco efímero, 750 horas al mes; las fuentes
   discrepan sobre si exige tarjeta) y se analizó críticamente la
   recomendación de otro asistente de desplegar allí. El equipo desplegó en
   Vercel.
5. Se revisó el backend existente y se advirtió que, en Vercel, el estado en
   memoria (métricas, objetos y reclamaciones) no es confiable porque las
   funciones no comparten memoria entre instancias. Se propusieron dos ajustes
   en `main.py` (agrupar rutas inexistentes y mostrar el objetivo de 2000 ms en
   `/metrics`), probados en un entorno aislado y aún no aplicados al
   repositorio.
6. Se apoyó la revisión del estado del repositorio contra la rúbrica de S8:
   probar la URL desde datos móviles, infraestructura como código, secretos
   por defecto en `docker-compose.yml`, documento de costos y ADR de
   plataforma.

**Aceptado:** la decisión pieza por pieza antes de elegir plataforma, la
métrica ligada al escenario de calidad y la estimación con supuestos
explícitos.

**Rechazado:** estimar costos con cifras genéricas sin la guía del curso, y
usar Render como plataforma, porque el equipo optó por Vercel.

**Limitaciones:** el documento de costos describe el servidor del laboratorio
con PostgreSQL y quedó desactualizado frente al despliegue en Vercel. Los
supuestos de volumen (≈500 usuarios) son estimados no validados con el equipo.
La IA no pudo abrir la URL desplegada ni ver el estado de los checks en GitHub
Actions.

## Registro S9 — 2026-10-04

Se utilizó IA para completar la cadena de la métrica de rendimiento (ligarla
explícitamente al escenario de calidad), para auditar el backend generado en S8 contra
las reglas de propiedad de datos de la semana 6, y para verificar lo que el modelo trajo
consigo (dependencias y credenciales).

Trabajo realizado y motivo:

- Se agregó `OBJECTIVES_MS` y se modificó `GET /metrics` en `backend/main.py` para que la
  respuesta de `/objects` muestre explícitamente el objetivo del escenario de calidad
  (2000 ms) y si se cumple (`met: true/false`), en vez de mostrar solo el p95 suelto. Se
  hizo porque la evidencia pide una medición ligada al escenario, no solo un número.
- Se agregó `test_p95_calculation_with_known_values` en `backend/test_api.py`. El test
  existente (`test_metrics_groups_by_route_template_not_raw_path`) solo comprobaba que
  hubiera datos y que el p95 no fuera `None`; no verificaba el cálculo en sí, así que si
  alguien rompía la fórmula del percentil, ningún test lo habría detectado. El test nuevo
  alimenta el cálculo con valores fijos y verifica el resultado exacto.
- Se auditó `backend/main.py` contra `docs/ddd/mapa_contextos.md`. Se detectó que el
  backend no reproduce la separación modular del ADR 0001: el endpoint de reclamación
  escribe directamente sobre el diccionario `_objects` sin pasar por ninguna frontera
  equivalente a `public/`. Se registró como no conformidad NC6 en
  `docs/ddd/auditoria_backend.md`, con el fragmento de código exacto y la corrección
  propuesta (separar el archivo en al menos dos módulos).
- Se verificaron las tres dependencias de `backend/requirements.txt` contra PyPI:
  `fastapi==0.141.1`, `uvicorn==0.54.0` y `PyJWT==2.7.0` existen y corresponden a
  versiones reales publicadas por los proyectos legítimos. Ninguna es una dependencia
  inventada por el modelo.
- Se revisaron `backend/main.py` y `backend/Dockerfile` en busca de credenciales en texto
  plano. El secreto JWT se obtiene solo de una variable de entorno y la aplicación falla
  al arrancar si no está definida; no se encontró ningún valor hardcodeado.

Aceptado: la corrección de `/metrics` con `objective_ms` y `met`, el test del cálculo del
p95, y el hallazgo NC6 con su plan de corrección.

Rechazado: aplicar de inmediato la corrección de NC6 (separar `main.py` en módulos), por
no ser código propio del integrante que hizo la auditoría; queda documentada para que el
equipo decida si se corrige antes de la entrega o se deja como hallazgo.

Limitaciones: `PyJWT==2.7.0` es una versión real pero de 2023, bastante más vieja que
`fastapi` y `uvicorn`; no se verificó si tiene vulnerabilidades conocidas pendientes de
parche. La auditoría de erosión cubrió solo el flujo de reclamación (`create_claim`); no
se revisó el resto de `main.py` en busca de otros cruces de frontera.
