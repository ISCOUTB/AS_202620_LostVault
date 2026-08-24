# 4. Estrategia y tácticas arquitectónicas — LostVault

## 4.1 Decisión

LostVault adopta un **monolito modular con aplicación selectiva de principios de arquitectura hexagonal**. La unidad desplegable sigue siendo una sola aplicación, pero cada capacidad de negocio tiene una frontera propia y expone únicamente contratos desde `public/`.

La decisión se evalúa contra los cuatro escenarios del árbol de utilidad, no contra criterios genéricos aislados.

## 4.2 Estrategia por escenario

| Escenario | Necesidad arquitectónica | Estrategia | Tácticas | Evidencia |
|---|---|---|---|---|
| Escenario 1 — Disponibilidad | Mantener la consulta accesible fuera del horario de oficina. | Mantener búsqueda y consulta dentro del monolito modular sin depender de la interfaz presencial. | Separar `search` de `claims`; evitar dependencias de UI para consultar objetos; encapsular persistencia detrás de interfaces. | [Escenario 1](10_requisitos_calidad.md#escenario-1--disponibilidad) · [ADR 0001](../adr/0001-estilo-arquitectonico.md) |
| Escenario 2 — Usabilidad | Reducir fricción en publicación. | Mantener módulos simples y contratos estables para que la UI no conozca detalles de infraestructura. | DTOs/servicios de aplicación, validación centralizada y componentes de UI pequeños. | [Escenario 2](10_requisitos_calidad.md#escenario-2--usabilidad) · [ADR 0001](../adr/0001-estilo-arquitectonico.md) |
| Escenario 3 — Seguridad | Impedir reclamaciones sin identidad válida. | Aplicar hexagonal selectivamente en `identity_verification` y `claims`. | Puertos para verificación, adaptadores de infraestructura, reglas de dominio aisladas y bloqueo por defecto ante verificación inválida. | [Escenario 3](10_requisitos_calidad.md#escenario-3--seguridad) · [ADR 0001](../adr/0001-estilo-arquitectonico.md) |
| Escenario 4 — Rendimiento | Mantener búsquedas bajo 2 s p95 con 200 usuarios. | Mantener `search` independiente de verificaciones y operaciones de reclamación. | Consultas específicas, paginación, evitar trabajo de identidad en el camino crítico y medir latencias antes del corte. | [Escenario 4](10_requisitos_calidad.md#escenario-4--rendimiento) · [ADR 0001](../adr/0001-estilo-arquitectonico.md) |

## 4.3 Comparación contra el árbol de utilidad

| Escenario / atributo | Arquitectura en capas | Hexagonal global | Monolito modular + hexagonal selectiva |
|---|---|---|---|
| Disponibilidad — Impacto H / Riesgo H | Alta: simple de desplegar, pero puede propagar dependencias entre áreas. | Media: buen aislamiento, mayor complejidad operativa/documental. | **Muy alta:** un despliegue simple con búsqueda separada de operaciones sensibles. |
| Usabilidad — Impacto H / Riesgo M | Alta: flujo sencillo. | Media: más abstracciones para una UI pequeña. | **Muy alta:** contratos de aplicación simples y límites de módulo claros. |
| Seguridad — Impacto H / Riesgo H | Media-Alta: permite capas, pero puede mezclar dominios si crece. | Muy alta: excelente aislamiento del dominio. | **Muy alta:** hexagonal se aplica donde la verificación y reclamación lo necesitan. |
| Rendimiento — Impacto M / Riesgo M | Alta: pocas capas, aunque pueden atravesarse demasiadas capas. | Media-Alta: aislamiento, con más indirections. | **Muy alta:** búsqueda independiente y sin verificación en el camino crítico. |

## 4.4 Tácticas transversales

1. **Modularidad:** cada módulo expone contratos por `public/` y evita importar detalles internos de otro módulo.
2. **Inversión de dependencias:** dominio y aplicación dependen de abstracciones, no de implementaciones concretas.
3. **Aislamiento selectivo:** `identity_verification` y `claims` pueden usar puertos/adaptadores cuando una regla sensible lo requiera.
4. **Observabilidad futura:** las mediciones de disponibilidad y rendimiento se incorporarán como evidencia del corte.
5. **Prueba:** cada módulo puede probar su dominio y servicios de aplicación sin depender de la UI.

## 4.5 Alternativas

- **Capas:** descartada como estilo único porque no ofrece límites suficientemente explícitos entre capacidades funcionales.
- **Hexagonal global:** descartada como estilo único porque añade complejidad innecesaria al sistema completo para un equipo pequeño.
- **Monolito modular:** elegido por equilibrar separación, despliegue simple y capacidad de evolución.

La decisión formal y sus consecuencias están documentadas en [ADR 0001](../adr/0001-estilo-arquitectonico.md).
