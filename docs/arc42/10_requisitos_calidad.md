# 10. Requisitos de Calidad

## Árbol de utilidad

La priorización usa **impacto** y **riesgo** de forma explícita. H = alto, M = medio, L = bajo.

| Prioridad | Aspecto | Impacto | Riesgo | Razón |
|---|---|---|---|---|
| 1 | Disponibilidad | H | H | Resuelve directamente la dependencia del horario de la oficina. |
| 2 | Usabilidad | H | M | Una experiencia compleja impediría que estudiantes adopten la plataforma. |
| 3 | Seguridad | H | H | Una reclamación incorrecta puede producir pérdida o entrega indebida de un objeto. |
| 4 | Rendimiento | M | M | La búsqueda rápida reduce fricción, pero el alcance inicial es académico. |

```text
Utilidad
├── Disponibilidad [Impacto H / Riesgo H]
│   └── Consulta 24/7 → Escenario 1
├── Usabilidad [Impacto H / Riesgo M]
│   └── Publicación sin fricción → Escenario 2
├── Seguridad [Impacto H / Riesgo H]
│   └── Verificación antes de entregar → Escenario 3
└── Rendimiento [Impacto M / Riesgo M]
    └── Búsqueda rápida bajo carga → Escenario 4
```

## Escenarios de calidad

## Escenario 1 — Disponibilidad
- **Fuente:** Estudiante
- **Estímulo:** Intenta consultar el estado de un objeto perdido fuera del horario de atención.
- **Artefacto:** Módulo de consulta/búsqueda de LostVault.
- **Entorno:** Operación normal, fuera de horario de oficina.
- **Respuesta:** El sistema responde sin intervención humana.
- **Medida:** Disponibilidad del 99 % mensual, con inactividad no programada menor a 7 horas/mes.
- **Cómo se medirá:** monitoreo HTTP periódico en producción; se calculará disponibilidad mensual y se comparará con el umbral de 99 %.
- **Relación arquitectónica:** [ADR 0001](../adr/0001-estilo-arquitectonico.md).

## Escenario 2 — Usabilidad
- **Fuente:** Estudiante que usa la plataforma por primera vez.
- **Estímulo:** Intenta publicar un objeto encontrado.
- **Artefacto:** Formulario de publicación.
- **Entorno:** Uso normal, sin capacitación previa.
- **Respuesta:** Completa la publicación sin ayuda externa.
- **Medida:** Al menos 90 % de usuarios nuevos completan la publicación en menos de 3 minutos.
- **Cómo se medirá:** prueba de usabilidad con usuarios nuevos; cronómetro desde apertura del formulario hasta confirmación de publicación.
- **Relación arquitectónica:** [ADR 0001](../adr/0001-estilo-arquitectonico.md).

## Escenario 3 — Seguridad
- **Fuente:** Usuario no autorizado.
- **Estímulo:** Intenta reclamar un objeto que no le pertenece.
- **Artefacto:** Módulo de verificación de identidad.
- **Entorno:** Operación normal.
- **Respuesta:** El sistema rechaza la entrega y marca el intento para revisión.
- **Medida:** 100 % de los intentos sin verificación válida son bloqueados automáticamente.
- **Cómo se medirá:** pruebas automatizadas de casos válidos e inválidos; ningún caso inválido debe producir estado de reclamación autorizada.
- **Relación arquitectónica:** [ADR 0001](../adr/0001-estilo-arquitectonico.md).

## Escenario 4 — Rendimiento
- **Fuente:** Estudiante.
- **Estímulo:** Realiza una búsqueda por palabra clave en hora pico.
- **Artefacto:** Módulo de búsqueda.
- **Entorno:** Carga pico, ~200 usuarios concurrentes.
- **Respuesta:** El sistema retorna resultados de búsqueda.
- **Medida:** 95 % de las búsquedas responden en ≤2 segundos (p95) con 200 usuarios concurrentes.
- **Cómo se medirá:** prueba de carga con herramienta de rendimiento; registrar latencias y comprobar que el percentil 95 sea ≤2 s.
- **Relación arquitectónica:** [ADR 0001](../adr/0001-estilo-arquitectonico.md).
