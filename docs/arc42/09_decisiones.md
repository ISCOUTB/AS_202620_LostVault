# 9. Decisiones de Arquitectura

Las decisiones arquitectónicas relevantes del proyecto se documentan como ADRs (Architecture Decision Records) independientes, en la carpeta `docs/adr/`.

## Decisiones registradas

| ADR | Título | Estado |
|---|---|---|
| [0001](../adr/0001-estilo-arquitectonico.md) | Estilo arquitectónico base de LostVault (monolito modular) | Aceptado |
| [0002](../adr/0002-integracion-reclamacion-api.md) | Integración síncrona para crear una reclamación | Aceptado |
| [0003](../adr/0003-plataforma-despliegue-vercel.md) | Plataforma de despliegue de la API — Vercel (funciones serverless) | Aceptado |
| [000.3](../adr/000.3-despliegue-busqueda-lostvault.md) | Análisis comparativo de despliegue para búsqueda (Railway vs. GCP Cloud Functions) — ejercicio de laboratorio, no describe el sistema real desplegado | Aceptado (laboratorio) |

Cada nueva decisión arquitectónica significativa (por ejemplo, extraer un módulo a un servicio independiente, o cambiar el mecanismo de verificación de identidad) se documentará como un nuevo ADR numerado consecutivamente (`0002-*.md`, `0003-*.md`, etc.), siguiendo el mismo formato: contexto, decisión, alternativas consideradas y consecuencias.
