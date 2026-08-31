# 6. Vista de Tiempo de Ejecución

Esta sección describe el flujo de ejecución implementado para el corte vertical **AS-03 Seguridad: reclamación de un objeto**. El corte atraviesa UI, aplicación, contratos públicos de módulos e infraestructura in-memory.

## Escenario: un estudiante reclama un objeto encontrado

1. La interfaz muestra un objeto disponible y permite solicitar su reclamación.
2. La UI invoca `ClaimObjectUseCase`, ubicado en `claims/application`.
3. `ClaimObjectUseCase` consulta `AuthenticationService.currentUser` a través de la frontera pública de `authentication`.
4. Si no existe sesión autenticada, el caso de uso devuelve un resultado fallido y el flujo termina sin modificar el objeto.
5. Si existe sesión, el caso de uso consulta el objeto mediante `ObjectService` a través de `objects/public`.
6. Si el objeto no existe o ya fue reclamado, el flujo se bloquea.
7. `ClaimObjectUseCase` solicita la verificación a `IdentityVerificationService` mediante `identity_verification/public`.
8. Si la verificación es inválida, el caso de uso devuelve un resultado fallido. No se crea una reclamación y el objeto permanece disponible.
9. Si la identidad es válida, `ClaimService` crea una reclamación con `verified = true`.
10. `ObjectService.markAsClaimed` cambia el estado del objeto de `available` a `claimed`.
11. El resultado exitoso regresa a la UI y se muestra la confirmación al usuario.

## Diagrama de secuencia simplificado

```text
Estudiante → UI: Reclamar objeto
UI → ClaimObjectUseCase: execute(objectId)
ClaimObjectUseCase → authentication/public: currentUser

alt sin sesión
  ClaimObjectUseCase → UI: Result.failure
else sesión válida
  ClaimObjectUseCase → objects/public: findById(objectId)
  ClaimObjectUseCase → identity_verification/public: verify(userId)

  alt identidad inválida
    identity_verification → ClaimObjectUseCase: valid = false
    ClaimObjectUseCase → UI: Result.failure
  else identidad válida
    identity_verification → ClaimObjectUseCase: valid = true
    ClaimObjectUseCase → ClaimService: requestClaim(...)
    ClaimService → ClaimObjectUseCase: Claim(verified = true)
    ClaimObjectUseCase → objects/public: markAsClaimed(objectId)
    ClaimObjectUseCase → UI: Result.success
  end
end
```

## Evidencia en código

- Orquestación: `lib/features/claims/application/claim_object_use_case.dart`.
- UI: `lib/main.dart`.
- Autenticación: `lib/features/authentication/`.
- Verificación: `lib/features/identity_verification/`.
- Reclamaciones: `lib/features/claims/`.
- Actualización del objeto: `lib/features/objects/`.

## Evidencia en pruebas

- `test/claim_object_use_case_test.dart`: prueba reglas de seguridad sin UI.
- `test/widget_test.dart`: prueba el corte desde la interfaz.
- `test/architecture_structure_test.dart`: prueba la frontera arquitectónica entre módulos.

## Relación con el atributo de calidad

Este flujo implementa directamente [AS-03 Seguridad](../aspectos.md) y el [Escenario 3](10_requisitos_calidad.md#escenario-3--seguridad): una reclamación no se autoriza si falta autenticación o si la verificación de identidad es inválida. Además, la orquestación consume otros módulos únicamente mediante sus contratos `public/`, siguiendo [ADR 0001](../adr/0001-estilo-arquitectonico.md).

## Limitación del adaptador actual

La verificación y la persistencia son in-memory para que el corte sea ejecutable y testeable sin servicios externos. El adaptador de identidad no reemplaza una verificación documental real; funciona como sustituto controlable para demostrar la arquitectura y probar tanto aceptación como rechazo.
