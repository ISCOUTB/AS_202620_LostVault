# ADR 0001: Estilo arquitectónico base de LostVault

- **Estado**: Aceptado
- **Fecha**: 2026-08-23
- **Decisores**: Equipo LostVault

## Contexto

LostVault necesita un estilo arquitectónico definido antes de empezar a
construir lógica de negocio. El sistema se organiza alrededor de módulos
funcionales identificados por el equipo: `authentication`, `objects`,
`search`, `claims`, `identity_verification` y `users`. El equipo de
desarrollo es pequeño, el despliegue debe mantenerse simple (una sola
aplicación, sin la complejidad operativa de administrar varios servicios
independientes), y se necesita poder trabajar en distintos módulos en
paralelo sin que un cambio en uno rompa a los demás por accidente.

## Decisión

Se adopta **monolito modular** como estilo arquitectónico base del sistema.

LostVault se despliega como una sola aplicación, pero internamente se
organiza en módulos independientes, uno por cada área funcional:
`authentication`, `objects`, `search`, `claims`, `identity_verification` y
`users`. Cada módulo es dueño de su propia lógica interna y solo expone al
resto del sistema lo que decide exponer explícitamente; ningún módulo accede
directamente al detalle interno de otro.

El módulo `authentication` se encarga del registro, inicio y cierre de
sesión, y de validar que un usuario esté autenticado antes de que otros
módulos (como `claims`) permitan acciones que lo requieran.

Estructura de referencia:

```
lib/
├── core/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── public/
└── features/
    ├── authentication/
    ├── objects/
    ├── search/
    ├── claims/
    ├── identity_verification/
    └── users/
```

Dentro de cada módulo (`objects/`, `search/`, etc.) se organiza, como
mínimo, en:

- `domain/` — entidades y reglas de negocio propias del módulo.
- `application/` — casos de uso del módulo.
- `infrastructure/` — persistencia y adaptadores del módulo.
- `public/` — lo único que otros módulos pueden importar de este módulo.

`core/`, a nivel de `lib/`, contiene utilidades compartidas y no contiene lógica de negocio específica de ningún módulo.

Regla de dependencia entre módulos: un módulo solo puede importar el
paquete `public/` de otro módulo, nunca su `domain/`, `application/` o
`infrastructure/` internos. Dentro de cada módulo, el equipo es libre de
organizar esas subcarpetas como mejor le sirva (por capas, o con un
dominio más aislado de la infraestructura); esa es una decisión interna del
módulo, no del sistema completo.

## Alternativas consideradas

### A. Arquitectura en capas

- **A favor**: esfuerzo de configuración inicial bajo, fácil de entender
  para un equipo pequeño.
- **En contra**: organiza el sistema por tipo técnico (presentación, lógica,
  datos) y no por área funcional, por lo que no da ningún mecanismo que
  evite que módulos de negocio distintos terminen acoplados entre sí dentro
  de la misma capa de "lógica".
- **Por qué no se eligió**: no protege los límites entre las áreas
  funcionales del sistema, que es justamente lo que el equipo necesita
  cuidar al tener varios módulos de negocio conviviendo en la misma
  aplicación.

### B. Arquitectura hexagonal (a nivel de todo el sistema)

- **A favor**: alta testeabilidad del dominio; facilita sustituir mecanismos
  de persistencia o servicios externos sin tocar la lógica de negocio.
- **En contra**: resuelve el problema de aislar el dominio de la
  infraestructura, pero no resuelve el problema de evitar que distintas
  áreas funcionales del sistema se acoplen entre sí; aplicada a todo el
  sistema como una sola pieza, añade interfaces y puertos que pueden ser
  innecesarios para los módulos más simples.
- **Por qué no se eligió como estilo único**: sus ventajas siguen siendo
  útiles, pero a nivel de cada módulo, no como decisión de todo el sistema.

### C. Monolito modular (elegido)

- **A favor**: separa con claridad las áreas funcionales del sistema;
  mantiene el despliegue simple al seguir siendo una sola aplicación;
  permite que un equipo pequeño trabaje varios módulos en paralelo sin la
  complejidad operativa de servicios distribuidos.
- **En contra**: todos los módulos comparten el mismo proceso y la misma
  infraestructura de despliegue, así que un fallo grave de infraestructura
  puede afectarlos a todos; la separación entre módulos depende de
  disciplina del equipo, ya que nada impide técnicamente que un módulo
  importe el interior de otro salvo la revisión de código.
- **Por qué se eligió**: es el estilo que mejor equilibra las necesidades
  actuales del proyecto — mantener límites claros entre áreas funcionales —
  con las restricciones del equipo — tamaño pequeño, despliegue simple —
  sin pagar el costo operativo de separar los módulos en servicios
  independientes que hoy no se necesitan.

## Consecuencias

**Positivas**

- Los módulos pueden desarrollarse y probarse en paralelo con menor riesgo
  de pisarse entre sí.
- El despliegue se mantiene simple: una sola aplicación, sin necesidad de
  coordinar servicios independientes.
- Cada módulo puede organizar su propio código internamente sin que eso
  obligue a los demás módulos a hacer lo mismo.
- Si en el futuro algún módulo necesita escalar o desplegarse de forma
  independiente, ya tiene un límite de responsabilidad claro (su carpeta
  `public/`) desde el cual extraerlo.

**Negativas / costos aceptados**

- No hay aislamiento de fallos entre módulos: un problema de infraestructura
  compartida puede afectar a todos los módulos a la vez.
- La separación entre módulos depende de disciplina del equipo y de
  revisión de código; nada la impone automáticamente salvo que se agregue
  tooling de arquitectura (por ejemplo, un linter de imports) más adelante.
- Si algún módulo termina necesitando un ciclo de despliegue, escalamiento o
  stack tecnológico muy distinto al resto, esta decisión no lo resuelve por
  sí sola: haría falta un ADR posterior que evalúe extraer ese módulo a un
  servicio independiente.

## Cómo revisar esta decisión

Si algún módulo crece hasta necesitar un ciclo de vida, escalamiento o
equipo propio claramente distinto al resto, corresponde abrir un ADR 0002
que evalúe extraerlo del monolito, usando el límite ya definido por su
carpeta `public/` como punto de corte natural — no como reemplazo de esta
decisión, sino como su evolución esperada.

## Trazabilidad con aspectos y escenarios

Esta decisión se relaciona directamente con los aspectos y escenarios definidos por el equipo:

- [AS-01 Disponibilidad](../aspectos.md#aspectos-de-calidad-declarados---lostvault) → [Escenario 1](../arc42/10_requisitos_calidad.md#escenario-1--disponibilidad)
- [AS-02 Usabilidad](../aspectos.md#aspectos-de-calidad-declarados---lostvault) → [Escenario 2](../arc42/10_requisitos_calidad.md#escenario-2--usabilidad)
- [AS-03 Seguridad](../aspectos.md#aspectos-de-calidad-declarados---lostvault) → [Escenario 3](../arc42/10_requisitos_calidad.md#escenario-3--seguridad)
- [AS-04 Rendimiento](../aspectos.md#aspectos-de-calidad-declarados---lostvault) → [Escenario 4](../arc42/10_requisitos_calidad.md#escenario-4--rendimiento)

Los escenarios enlazan de regreso a este ADR en `10_requisitos_calidad.md` y la estrategia de la sección 4 enlaza al ADR desde cada fila.
