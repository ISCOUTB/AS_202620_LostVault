# ADR 0002: Integración síncrona para crear una reclamación

- **Estado**: Aceptado
- **Fecha**: 2026-09-20
- **Decisores**: Equipo LostVault
- **Contrato relacionado**: [`../contracts/lostvault-api.yaml`](../contracts/lostvault-api.yaml), versión `1.0.0`

## Contexto

El corte vertical actual permite que un estudiante reclame un objeto mediante
`ClaimObjectUseCase`. La operación comprueba en el mismo flujo que exista una
sesión, que el objeto esté disponible y que la identidad sea válida. La futura
frontera entre el cliente Flutter y el proveedor debe publicar ese acuerdo de
forma ejecutable, sin exponer detalles de los adaptadores in-memory.

El consumidor necesita saber inmediatamente si puede informar una reclamación
autorizada. Una respuesta tardía o una identidad sin verificar no puede
presentarse como éxito, porque el objeto no debe pasar a `claimed` hasta que la
reclamación sea válida.

## Decisión

Se adopta una integración **síncrona HTTP/JSON** para `POST
/v1/objects/{objectId}/claims`, especificada en OpenAPI 3.1.1. El proveedor
responde `201` solo después de verificar la identidad y reservar el objeto. El
cliente recibe un problema explícito para ausencia de sesión (`401`), objeto
inexistente (`404`), objeto ya reclamado (`409`) o identidad no verificada
(`422`).

El contrato se versiona junto al código. La prueba
`test/api_contract_test.dart` representa las necesidades del consumidor y se
ejecuta en cada `push` y `pull request`. Un cambio incompatible, como eliminar
`verified`, cambiarlo de booleano o retirar `409`, rompe esa prueba antes del
merge.

## Alternativa considerada: evento asíncrono

Se consideró publicar `ClaimRequested` en una cola y procesarlo después. Esto
reduciría el acoplamiento temporal: el cliente podría enviar la solicitud aun
si el verificador estuviera momentáneamente indisponible. Sin embargo, exige
un estado pendiente, notificación posterior, reintentos idempotentes y una
forma de resolver solicitudes duplicadas. También cambia la experiencia: el
usuario ya no obtiene una confirmación inmediata de que el objeto quedó
reclamado.

No se adopta ahora porque el flujo actual requiere una decisión inmediata para
evitar que dos estudiantes crean que reclamaron el mismo objeto. Esta decisión
no niega usar eventos más adelante para efectos secundarios no críticos, como
notificaciones o auditoría; en ese caso se creará un contrato AsyncAPI y un
ADR adicional.

## Consecuencias

**Positivas**

- El usuario recibe una respuesta inequívoca durante la misma interacción.
- El proveedor conserva de forma atómica la validación y la reserva del objeto.
- Los modos de fallo son parte explícita del contrato y no mensajes implícitos.
- Cambios incompatibles son detectables por CI antes de integrar código.

**Costos aceptados**

- Cliente, API y verificación deben estar disponibles al mismo tiempo; si el
  proveedor no responde, el usuario no puede completar la reclamación en ese
  instante.
- El cliente debe mostrar y permitir reintentar errores de red o de servidor;
  esos fallos no se confunden con los errores de negocio `401/404/409/422`.
- La implementación actual sigue siendo in-memory: este ADR define la
  frontera que deberá respetar el proveedor HTTP cuando se construya, no
  declara que el servicio remoto ya esté desplegado.

## Trazabilidad

- Flujo existente: [`../arc42/06_vista_runtime.md`](../arc42/06_vista_runtime.md).
- Caso de uso: `lib/features/claims/application/claim_object_use_case.dart`.
- Modelo de respuesta: `lib/features/claims/domain/claim.dart`.
- Evidencia automatizada: `test/api_contract_test.dart` y
  `.github/workflows/flutter.yml`.
