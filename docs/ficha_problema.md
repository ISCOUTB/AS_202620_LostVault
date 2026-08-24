# Ficha del Problema — LostVault

## Contexto

En la universidad, los objetos perdidos se gestionan hoy de forma manual, quien encuentra un objeto lo entrega en la oficina de objetos perdidos y quien lo perdió debe escribirle a 
los encargados de cerrar los salones o acercarse presencialmente a preguntar si ha llegado algo suyo.

## Problema

Este proceso manual genera varias fricciones:

- El estudiante debe contactar directamente a la persona encargada (por mensaje o en persona) para saber si su objeto fue entregado.
- Si decide ir presencialmente, corre el riesgo de que la oficina esté cerrada o de que no haya nadie disponible en el momento, perdiendo tiempo de forma innecesaria.
- No existe un registro visible ni centralizado de qué objetos han sido encontrados, por lo que la búsqueda depende completamente de la memoria y disponibilidad del encargado.
- Tampoco hay manera fácil de que un estudiante que encuentra un objeto lo reporte sin pasar físicamente por la oficina.

## Población afectada

Estudiantes de la universidad, tanto quienes pierden objetos como quienes los encuentran, y la oficina de objetos perdidos, que concentra toda la carga de gestión y atención de consultas.


## Tensiones de calidad

LostVault debe equilibrar **disponibilidad y seguridad**. La consulta del inventario debe mantenerse disponible sin depender de la oficina, pero la reclamación requiere controles de identidad. La solución mantiene la consulta general disponible y concentra los controles fuertes en la reclamación.

## Propuesta

Una plataforma tipo "Marketplace" (similar a Facebook Marketplace), desarrollada como aplicación independiente con identidad visual de la universidad, donde:

- Tanto la oficina de objetos perdidos como cualquier estudiante puedan publicar un objeto encontrado, con foto y descripción.
- Los estudiantes puedan buscar y filtrar objetos publicados sin necesidad de escribirle a nadie ni desplazarse físicamente.
- La entrega del objeto se verifique solicitando al reclamante una foto sosteniendo su cédula y carné estudiantil, como mecanismo básico de identificación antes de la entrega presencial.
## Valor esperado

- Reduce el tiempo perdido en desplazamientos innecesarios cuando la oficina está cerrada o sin atención.
- Evita la dependencia de mensajes directos al encargado para consultas simples.
- Centraliza y hace visible el inventario de objetos perdidos en tiempo real.
- Da a los estudiantes que encuentran objetos una forma simple de reportarlos.
