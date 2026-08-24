# LostVault — Esqueleto ejecutable

Este repositorio contiene únicamente el **esqueleto ejecutable** correspondiente a la responsabilidad de esta etapa.

La estructura está preparada para el estilo arquitectónico seleccionado por el equipo:

> **Monolito modular con aplicación selectiva de principios de arquitectura hexagonal.**

## Estructura

```text
lib/
├── core/
└── features/
    ├── authentication/
    ├── objects/
    ├── search/
    ├── claims/
    ├── identity_verification/
    └── users/

test/
└── widget_test.dart
```

Los paquetes están preparados, pero **no contienen lógica de negocio**. La implementación de las funcionalidades corresponde a las siguientes etapas del proyecto.

## Requisitos

- Flutter SDK instalado.
- Dart incluido con Flutter.
- Un dispositivo físico o emulador disponible para ejecutar la aplicación.

## Instalar dependencias

Desde la raíz del proyecto:

```bash
flutter pub get
```

## Ejecutar

```bash
flutter run
```

El comando `flutter run` inicia la aplicación y muestra la pantalla mínima del esqueleto de LostVault.

## Ejecutar pruebas

```bash
flutter test
```

La prueba automatizada verifica que `LostVaultApp` se inicia y renderiza correctamente el esqueleto.

## Estado de esta entrega

- [x] Proyecto Flutter ejecutable.
- [x] Estructura de monolito modular.
- [x] Paquete `core`.
- [x] Paquete `authentication`.
- [x] Paquete `objects`.
- [x] Paquete `search`.
- [x] Paquete `claims`.
- [x] Paquete `identity_verification`.
- [x] Paquete `users`.
- [x] Prueba automatizada inicial.
- [x] Instrucciones de ejecución.
- [ ] Lógica de negocio.

## Objetivo

El propósito de este esqueleto es que la semana 4 pueda comenzar directamente sobre la estructura arquitectónica acordada, sin dedicar tiempo a montar nuevamente el proyecto.

No se implementa lógica de negocio en esta etapa.
