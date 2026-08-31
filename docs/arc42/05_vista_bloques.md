# 5. Vista de Bloques de Construcción

## Nivel 1 — Descomposición en módulos

Siguiendo la decisión registrada en [ADR 0001](../adr/0001-estilo-arquitectonico.md), LostVault se organiza como un monolito modular compuesto por los siguientes módulos:

| Módulo | Responsabilidad |
|---|---|
| `authentication` | Registro, inicio y cierre de sesión; validación de que un usuario esté autenticado. |
| `users` | Datos de perfil del usuario (nombre, carné, tipo: estudiante u oficina). |
| `objects` | Publicación y gestión de objetos perdidos o encontrados. |
| `search` | Búsqueda y filtrado de objetos publicados. |
| `claims` | Proceso de reclamación de un objeto. |
| `identity_verification` | Verificación de identidad (foto con cédula y carné) antes de entregar un objeto reclamado. |

## Nivel 2 — Estructura interna de cada módulo

Cada módulo se organiza internamente en las mismas cuatro subcarpetas:

```text
lib/<modulo>/
├── domain/          → entidades y reglas de negocio propias del módulo
├── application/     → casos de uso del módulo
├── infrastructure/  → persistencia y adaptadores del módulo
└── public/          → lo único que otros módulos pueden importar de este módulo
```

## Regla de dependencia

Un módulo solo puede importar el paquete `public/` de otro módulo. Nunca puede acceder directamente a su `domain/`, `application/` o `infrastructure/` interno. Esta regla es la que mantiene los módulos desacoplados entre sí, evitando que el sistema degenere en un monolito fuertemente acoplado.

## Kernel compartido

`lib/shared/` contiene utilidades comunes (por ejemplo, manejo de errores, utilidades de red) y no contiene lógica de negocio de ningún módulo específico.
