# Aspectos de Calidad Declarados — LostVault

## Tensiones de calidad

LostVault enfrenta una tensión explícita entre **disponibilidad** y **seguridad**. La disponibilidad exige que la consulta del inventario esté accesible sin depender del horario de la oficina, mientras que la seguridad exige controles de identidad antes de permitir una reclamación. Un control de seguridad demasiado pesado puede aumentar fricción o impedir el acceso a funciones que deberían permanecer disponibles. La decisión arquitectónica busca mantener la consulta pública disponible y concentrar la verificación fuerte en la operación sensible de reclamación.

La entrega actual implementa **una fila completa hasta pruebas: AS-03 Seguridad**. Los demás aspectos conservan su definición arquitectónica y quedan pendientes de un corte ejecutable propio.

| ID | Aspecto | Prioridad | Justificación | Tensión | Escenario relacionado | Medida | Decisión/compromiso | Implementación del corte | Pruebas / evidencia |
|---|---|---|---|---|---|---|---|---|---|
| AS-01 | Disponibilidad | Alta | La consulta debe funcionar fuera del horario de la oficina. | Con Seguridad: controles adicionales no deben bloquear la consulta general. | [Escenario 1](arc42/10_requisitos_calidad.md#escenario-1--disponibilidad) | 99 % mensual; <7 h/mes de inactividad no programada. | Mantener consulta pública disponible y reservar la verificación fuerte para reclamaciones. [ADR 0001](adr/0001-estilo-arquitectonico.md) | Pendiente de un corte específico de disponibilidad. | Pendiente de medición HTTP en un entorno desplegado. |
| AS-02 | Usabilidad | Alta | Estudiantes nuevos deben publicar sin capacitación. | Con Seguridad: la verificación no debe trasladarse a cada acción de consulta/publicación. | [Escenario 2](arc42/10_requisitos_calidad.md#escenario-2--usabilidad) | ≥90 % de usuarios nuevos publican en <3 min. | Formularios simples y controles de identidad solo donde aportan seguridad real. [ADR 0001](adr/0001-estilo-arquitectonico.md) | Pendiente de un corte específico de publicación. | Pendiente de prueba de usabilidad con usuarios nuevos. |
| **AS-03** | **Seguridad** | **Alta** | Una reclamación no verificada no debe permitir la entrega. | Con Disponibilidad: el control de identidad puede añadir pasos y dependencias. | [Escenario 3](arc42/10_requisitos_calidad.md#escenario-3--seguridad) | **100 % de intentos sin verificación válida bloqueados.** | Aplicar verificación en reclamaciones y conservar el inventario consultable sin ella. [ADR 0001](adr/0001-estilo-arquitectonico.md) | **Corte vertical ejecutable:** `lib/main.dart` → `ClaimObjectUseCase` → contratos públicos de `authentication`, `identity_verification` y `objects` → `ClaimService` → adaptadores `infrastructure/`. El caso de uso bloquea ausencia de sesión, identidad inválida, objeto inexistente o ya reclamado; solo una identidad válida permite crear la reclamación y marcar el objeto como reclamado. | **`test/claim_object_use_case_test.dart`** prueba sesión ausente, identidad inválida y flujo válido. **`test/widget_test.dart`** prueba el recorrido desde UI. **`test/architecture_structure_test.dart`** protege la regla de dependencias entre módulos. Ejecutar `flutter test`. |
| AS-04 | Rendimiento | Media | La búsqueda debe seguir siendo rápida con carga elevada. | Con Seguridad: validaciones innecesarias no deben incorporarse al camino crítico de búsqueda. | [Escenario 4](arc42/10_requisitos_calidad.md#escenario-4--rendimiento) | p95 ≤2 s con ~200 usuarios concurrentes. | Mantener búsqueda independiente de la verificación de identidad. [ADR 0001](adr/0001-estilo-arquitectonico.md) | Pendiente de un corte específico de búsqueda bajo carga. | Pendiente de prueba de carga con ~200 usuarios concurrentes. |

## Trazabilidad detallada de AS-03 — Seguridad

```text
Aspecto
AS-03 Seguridad
   ↓
Escenario de calidad
Escenario 3 — bloquear 100 % de intentos sin verificación válida
   ↓
Decisión arquitectónica
ADR 0001 — monolito modular + hexagonal selectiva
   ↓
Táctica
Orquestación en claims mediante contratos públicos y bloqueo por defecto
   ↓
Código
ClaimObjectUseCase
   ├── AuthenticationService
   ├── IdentityVerificationService
   ├── ClaimService
   └── ObjectService
   ↓
Adaptadores
InMemoryAuthenticationService
InMemoryIdentityVerificationService
InMemoryClaimService
InMemoryObjectService
   ↓
Pruebas
claim_object_use_case_test.dart
widget_test.dart
architecture_structure_test.dart
```

### Criterio de aceptación del corte AS-03

Se considera satisfecho el corte cuando:

1. una reclamación sin sesión es rechazada;
2. una reclamación con identidad inválida es rechazada;
3. en ambos casos el objeto permanece disponible y no se crea una reclamación válida;
4. una reclamación con sesión e identidad válidas crea una reclamación verificada y cambia el objeto a estado reclamado;
5. la UI permite demostrar el recorrido de manera ejecutable;
6. los módulos involucrados solo consumen la frontera `public/` de otros módulos;
7. `flutter test` finaliza sin fallos.

## Detalle — Disponibilidad

La disponibilidad continúa siendo el aspecto prioritario del árbol de utilidad porque el problema original depende del horario de la oficina. LostVault debe permitir consultar el inventario sin intervención humana. Sin embargo, el corte vertical seleccionado para esta entrega es AS-03 Seguridad porque ya existe un escenario de runtime transversal y permite demostrar la arquitectura completa hasta pruebas automatizadas.
