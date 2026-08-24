# Aspectos de Calidad Declarados — LostVault

## Tensiones de calidad

LostVault enfrenta una tensión explícita entre **disponibilidad** y **seguridad**. La disponibilidad exige que la consulta del inventario esté accesible sin depender del horario de la oficina, mientras que la seguridad exige controles de identidad antes de permitir una reclamación. Un control de seguridad demasiado pesado puede aumentar fricción o impedir el acceso a funciones que deberían permanecer disponibles. La decisión arquitectónica busca mantener la consulta pública disponible y concentrar la verificación fuerte en la operación sensible de reclamación.

| ID | Aspecto | Prioridad | Justificación | Tensión | Escenario relacionado | Medida | Decisión/compromiso |
|---|---|---|---|---|---|---|---|
| AS-01 | Disponibilidad | Alta | La consulta debe funcionar fuera del horario de la oficina. | Con Seguridad: controles adicionales no deben bloquear la consulta general. | [Escenario 1](arc42/10_requisitos_calidad.md#escenario-1--disponibilidad) | 99 % mensual; <7 h/mes de inactividad no programada. | Mantener consulta pública disponible y reservar la verificación fuerte para reclamaciones. [ADR 0001](adr/0001-estilo-arquitectonico.md) |
| AS-02 | Usabilidad | Alta | Estudiantes nuevos deben publicar sin capacitación. | Con Seguridad: la verificación no debe trasladarse a cada acción de consulta/publicación. | [Escenario 2](arc42/10_requisitos_calidad.md#escenario-2--usabilidad) | ≥90 % de usuarios nuevos publican en <3 min. | Formularios simples y controles de identidad solo donde aportan seguridad real. [ADR 0001](adr/0001-estilo-arquitectonico.md) |
| AS-03 | Seguridad | Alta | Una reclamación no verificada no debe permitir la entrega. | Con Disponibilidad: el control de identidad puede añadir pasos y dependencias. | [Escenario 3](arc42/10_requisitos_calidad.md#escenario-3--seguridad) | 100 % de intentos sin verificación válida bloqueados. | Aplicar verificación en reclamaciones y conservar el inventario consultable sin ella. [ADR 0001](adr/0001-estilo-arquitectonico.md) |
| AS-04 | Rendimiento | Media | La búsqueda debe seguir siendo rápida con carga elevada. | Con Seguridad: validaciones innecesarias no deben incorporarse al camino crítico de búsqueda. | [Escenario 4](arc42/10_requisitos_calidad.md#escenario-4--rendimiento) | p95 ≤2 s con ~200 usuarios concurrentes. | Mantener búsqueda independiente de la verificación de identidad. [ADR 0001](adr/0001-estilo-arquitectonico.md) |

## Detalle — Disponibilidad

La disponibilidad es el aspecto prioritario porque el problema original depende del horario de la oficina. LostVault debe permitir consultar el inventario sin intervención humana.
