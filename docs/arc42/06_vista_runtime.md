# 6. Vista de Tiempo de Ejecución

Esta sección describe el flujo de ejecución de uno de los escenarios más críticos del sistema: la reclamación de un objeto perdido, que involucra a varios módulos trabajando en conjunto.

## Escenario: Un estudiante reclama un objeto encontrado

1. El estudiante o afiliado a la universidad, ya autenticado en la aplicación, encuentra su objeto usando el módulo `search`.
2. Selecciona "Reclamar objeto" y eso activa el módulo `claims`.
3. `claims` consulta al módulo `authentication` (a través de su `public/`) para confirmar que la sesión del usuario es válida.
4. Si la sesión es válida, `claims` solicita al módulo `identity_verification` que confirme la identidad del reclamante.
5. El estudiante toma una foto sosteniendo su cédula y carné estudiantil; `identity_verification` procesa la verificación.
6. Si la verificación es exitosa, `identity_verification` responde a `claims` con una confirmación.
7. `claims` marca la reclamación como válida y notifica al módulo `objects` para actualizar el estado del objeto (de "disponible" a "reclamado").
8. El estudiante recibe confirmación de que puede acercarse a recoger su objeto.

## Diagrama de secuencia (simplificado)

```text
Estudiante → search: buscar objeto
Estudiante → claims: solicitar reclamación
claims → authentication: ¿sesión válida?
authentication → claims: sí
claims → identity_verification: verificar identidad
identity_verification → claims: verificación exitosa
claims → objects: marcar objeto como reclamado
claims → Estudiante: confirmación de reclamación
```

## Por qué es relevante este flujo

Este escenario ilustra directamente el atributo de calidad de **seguridad** definido en la sección 10: ningún objeto se entrega sin pasar por la verificación de identidad, y el módulo `claims` actúa como orquestador sin acceder directamente al interior de `authentication` ni de `identity_verification` — solo a través de sus interfaces públicas, respetando la regla de dependencia del ADR 0001.
