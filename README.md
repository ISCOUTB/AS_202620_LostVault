# LostVault — línea base arquitectónica + corte vertical ejecutable

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

test/
├── architecture_structure_test.dart
├── claim_object_use_case_test.dart
└── widget_test.dart

web/
├── index.html
└── manifest.json

docs/
├── adr/
├── arc42/
└── c4/

.github/workflows/flutter.yml
```

Cada módulo mantiene una frontera pública en `public/`. Entre módulos solo se permiten dependencias hacia esa frontera pública. La prueba `test/architecture_structure_test.dart` verifica esta regla automáticamente.

## Corte vertical ejecutable seleccionado

El corte implementado corresponde a **AS-03 — Seguridad**, específicamente al escenario: **impedir que una reclamación sea autorizada cuando el usuario no está autenticado o su identidad no es válida**.

Este corte se eligió porque atraviesa varias capas y módulos reales de LostVault y coincide con el flujo documentado en `docs/arc42/06_vista_runtime.md`.

### Flujo vertical

```text
Interfaz Flutter (`lib/main.dart`)
        ↓
ClaimObjectUseCase (`claims/application`)
        ↓
AuthenticationService (`authentication/public`)
        ↓
IdentityVerificationService (`identity_verification/public`)
        ↓
ClaimService (`claims/application`)
        ↓
ObjectService (`objects/public`)
        ↓
Adaptadores in-memory (`infrastructure`)
        ↓
Resultado visible en la interfaz
```

### Regla de negocio demostrada

1. Si no existe una sesión autenticada, la reclamación se bloquea.
2. Si el objeto no existe o ya fue reclamado, la reclamación se bloquea.
3. Si la identidad no puede verificarse, la reclamación se bloquea y el objeto permanece disponible.
4. Solo con sesión e identidad válidas se crea una reclamación verificada.
5. Después de una reclamación válida, el objeto cambia de `Disponible` a `Reclamado`.

### Archivos principales del corte

| Capa / responsabilidad | Archivo |
|---|---|
| UI ejecutable | `lib/main.dart` |
| Caso de uso / orquestación | `lib/features/claims/application/claim_object_use_case.dart` |
| Contrato de reclamación | `lib/features/claims/application/claim_service.dart` |
| Entidad de reclamación | `lib/features/claims/domain/claim.dart` |
| Adaptador de reclamación | `lib/features/claims/infrastructure/in_memory_claim_service.dart` |
| Contrato de autenticación | `lib/features/authentication/application/authentication_service.dart` |
| Adaptador de autenticación | `lib/features/authentication/infrastructure/in_memory_authentication_service.dart` |
| Contrato de verificación | `lib/features/identity_verification/application/identity_verification_service.dart` |
| Adaptador de verificación | `lib/features/identity_verification/infrastructure/in_memory_identity_verification_service.dart` |
| Dominio del objeto | `lib/features/objects/domain/lost_object.dart` |
| Contrato de objetos | `lib/features/objects/application/object_service.dart` |
| Adaptador de objetos | `lib/features/objects/infrastructure/in_memory_object_service.dart` |

## Requisitos

- Flutter SDK estable.
- Dart incluido con Flutter.
- Google Chrome para ejecutar directamente el corte incluido en `web/`, o un dispositivo/emulador si se generan otras plataformas.

## Instalar

Desde la carpeta raíz del proyecto:

```bash
flutter pub get
```

La entrega incluye un objetivo web mínimo en `web/`, por lo que el corte puede ejecutarse directamente en Chrome sin generar carpetas adicionales.

## Ejecutar el corte vertical

```bash
flutter run -d chrome
```

Para revisar los dispositivos disponibles:

```bash
flutter devices
```

Si se desea ejecutar además en Android, Windows u otra plataforma que no esté incluida en el archivo fuente, se puede generar su soporte con Flutter, por ejemplo:

```bash
flutter create . --platforms=android,web,windows
```

Al abrir la aplicación aparecerá un objeto de prueba llamado **“Termo negro”** con estado **“Disponible”**.

### Recorrido manual esperado

1. Presionar **“Reclamar objeto”** sin iniciar sesión.
   - Resultado esperado: `Reclamación bloqueada: debes iniciar sesión.`
   - El objeto debe seguir en estado `Disponible`.
2. Presionar **“Iniciar sesión de prueba”**.
   - Resultado esperado: aparece la sesión `estudiante@utb.edu.co`.
3. Presionar nuevamente **“Reclamar objeto”**.
   - La identidad se verifica mediante el adaptador in-memory.
   - Se crea una reclamación verificada.
   - El objeto cambia a estado `Reclamado`.
   - La interfaz muestra la confirmación de reclamación autorizada.

Con este recorrido se demuestra de extremo a extremo el corte UI → aplicación → dominio/contratos → infraestructura → UI.

## Analizar y probar

```bash
flutter analyze
flutter test
```

Las pruebas relevantes para AS-03 son:

- `test/claim_object_use_case_test.dart`
  - bloquea reclamación sin autenticación;
  - bloquea reclamación con identidad inválida;
  - autoriza reclamación con identidad válida y actualiza el objeto.
- `test/widget_test.dart`
  - verifica el comportamiento ejecutable desde la interfaz.
- `test/architecture_structure_test.dart`
  - verifica la existencia de las cuatro fronteras por módulo;
  - impide que un módulo importe `domain/`, `application/` o `infrastructure/` de otro módulo, obligándolo a utilizar `public/`.

El workflow `.github/workflows/flutter.yml` ejecuta automáticamente `flutter analyze` y `flutter test` en cada `push` y `pull_request`.

> Nota de evidencia: el código y las pruebas están preparados para ejecutarse con Flutter. La evidencia de “pruebas en verde” debe registrarse después de ejecutar los comandos anteriores localmente o después de que GitHub Actions finalice correctamente.

## Trazabilidad del aspecto hasta pruebas

La fila **AS-03 Seguridad** se encuentra completada hasta implementación y pruebas en `docs/aspectos.md`.

```text
AS-03 Seguridad
  → Escenario 3 de calidad
  → ADR 0001 / monolito modular + hexagonal selectiva
  → ClaimObjectUseCase
  → AuthenticationService + IdentityVerificationService
  → ClaimService + ObjectService
  → adaptadores in-memory
  → pruebas de caso de uso + widget + arquitectura
```

## Documentación arquitectónica

- `docs/ficha_problema.md`: problema, población, alcance y tensiones de calidad.
- `docs/aspectos.md`: tabla de aspectos con trazabilidad hasta implementación y pruebas para AS-03.
- `docs/arc42/01_objetivos.md`: objetivos y prioridades.
- `docs/arc42/02_restricciones.md`: restricciones.
- `docs/arc42/03_contexto.md`: contexto y actores.
- `docs/arc42/04_estilo_arquitectonico.md`: estrategia y comparación contra escenarios.
- `docs/arc42/05_vista_bloques.md`: módulos y regla de dependencia.
- `docs/arc42/06_vista_runtime.md`: flujo ejecutable de reclamación.
- `docs/arc42/10_requisitos_calidad.md`: árbol de utilidad y escenarios medibles.
- `docs/c4/contexto.mmd`: C4 de contexto como código.
- `docs/c4/c4_contexto.png`: representación visual.
- `docs/adr/0001-estilo-arquitectonico.md`: decisión arquitectónica y trazabilidad.
- `docs/ia.md`: uso de IA, aceptaciones y rechazos.

## Alcance de esta línea base

Este corte utiliza persistencia y servicios **in-memory** para demostrar la arquitectura y la regla de seguridad de manera ejecutable y testeable. No representa todavía una integración real con base de datos, autenticación institucional ni reconocimiento documental. Tampoco afirma que las métricas de producción de disponibilidad o rendimiento estén demostradas; esas requieren ejecución y medición real.
