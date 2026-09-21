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
