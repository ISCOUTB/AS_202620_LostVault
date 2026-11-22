# LostVault — criterios corregidos

Esta versión aplica las correcciones identificadas en las evidencias S1, S2 y S3 y en la retroalimentación disponible.

| Hallazgo | Corrección aplicada |
|---|---|
| Falta de dos tensiones de calidad | Se documenta la tensión Disponibilidad ↔ Seguridad y su trade-off. |
| `docs/aspectos.md` narrativo | Se reemplaza por una tabla de 8 columnas con ID, prioridad, tensión, escenario, medida y decisión. |
| Árbol sin impacto/riesgo | Se agregan valores H/M/L y justificación de prioridad. |
| Sección 4 genérica | Se reescribe con estrategia y tácticas vinculadas a los escenarios 1–4. |
| Matriz comparativa genérica | Se compara cada estilo contra los cuatro escenarios y su impacto/riesgo. |
| ADR no alcanzable desde aspectos/escenarios | Se agregan enlaces desde aspectos, escenarios y sección 4. |
| C4 fuera de `docs/c4/` | Se mueve a `docs/c4/` y se añade fuente `contexto.mmd` para revisión. |
| `docs/ia.md` desactualizado | Se agregan registros S2/S3 y aceptaciones/rechazos con motivos. |
| Paquetes arquitectónicos ausentes/incompletos | Se crean `domain`, `application`, `infrastructure` y `public` para los seis módulos y `core`. |
| Archivos placeholder | Se eliminan y se reemplazan por clases/interfaces mínimas reales. |
| Residuos `front_end` y `ejecutable` | Se eliminan. |
| Pruebas sin evidencia automatizada | Se agregan pruebas de UI y estructura y un workflow de GitHub Actions para `flutter analyze` y `flutter test`. El criterio queda pendiente de confirmación hasta que GitHub ejecute el workflow en el repositorio. |

## Límite de la corrección

Esta versión corrige los hallazgos documentales y estructurales disponibles. No afirma que las métricas de producción de disponibilidad, usabilidad o rendimiento ya estén demostradas: esas requieren mediciones reales y evidencia posterior.
