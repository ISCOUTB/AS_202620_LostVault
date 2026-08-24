# LostVault — línea base arquitectónica corregida

LostVault es una plataforma tipo Marketplace para objetos perdidos y encontrados dentro de la universidad.

## Decisión arquitectónica

**Monolito modular con aplicación selectiva de principios de arquitectura hexagonal.**

La decisión está documentada en `docs/adr/0001-estilo-arquitectonico.md` y se traza desde los aspectos y escenarios de calidad.

## Estructura

```text
lib/
├── core/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── public/
└── features/
    ├── authentication/
    │   ├── domain/ application/ infrastructure/ public/
    ├── objects/
    ├── search/
    ├── claims/
    ├── identity_verification/
    └── users/

docs/
├── adr/
├── arc42/
└── c4/

.github/workflows/flutter.yml
```

Cada módulo mantiene una frontera pública en `public/`. El dominio y la aplicación no dependen de implementaciones concretas de infraestructura.

## Requisitos

- Flutter SDK estable.
- Dart incluido con Flutter.
- Dispositivo físico o emulador para ejecutar la aplicación.

## Instalar

```bash
flutter pub get
```

## Ejecutar

```bash
flutter run
```

## Analizar y probar

```bash
flutter analyze
flutter test
```

El workflow `.github/workflows/flutter.yml` ejecuta automáticamente análisis y pruebas en cada push y pull request. La revisión final del criterio «prueba en verde» debe hacerse después de que GitHub Actions ejecute el workflow.

## Documentación arquitectónica

- `docs/ficha_problema.md`: problema, población, alcance y tensiones de calidad.
- `docs/aspectos.md`: tabla de aspectos con trazabilidad y trade-offs.
- `docs/arc42/01_objetivos.md`: objetivos y prioridades.
- `docs/arc42/02_restricciones.md`: restricciones.
- `docs/arc42/03_contexto.md`: contexto y actores.
- `docs/arc42/04_estilo_arquitectonico.md`: estrategia y comparación contra escenarios.
- `docs/arc42/10_requisitos_calidad.md`: árbol de utilidad y escenarios medibles.
- `docs/c4/contexto.mmd`: C4 de contexto como código.
- `docs/c4/c4_contexto.png`: representación visual.
- `docs/adr/0001-estilo-arquitectonico.md`: decisión arquitectónica y trazabilidad.
- `docs/ia.md`: uso de IA, aceptaciones y rechazos.

## Alcance de esta línea base

Esta versión corrige los hallazgos documentales y estructurales de S1–S3 y deja una implementación Flutter mínima para demostrar que los módulos pueden evolucionar sin romper la frontera arquitectónica. No pretende afirmar que las métricas de producción de disponibilidad o rendimiento ya están demostradas; esas requieren ejecución y medición real.
