# ADR 0004 — No incorporación de un componente generativo en runtime

## Estado

Aceptado — 2026-10-04

## Contexto

La evidencia S9 pide que, si el sistema incorpora o va a incorporar un componente
generativo (un modelo de lenguaje en tiempo de ejecución, por ejemplo vía RAG o un
agente con herramientas), se documente su conjunto de evaluación, su costo por
operación y su latencia. Si se decide no incorporarlo, pide el ADR que lo justifique.

LostVault es una plataforma de objetos perdidos y encontrados: publicar un objeto,
buscarlo y reclamarlo con identidad verificada. Ninguno de los escenarios de calidad
definidos en la semana 2, ni el corte vertical implementado (AS-03, seguridad en la
reclamación), requiere generación de lenguaje, resumen de texto, clasificación
semántica ni ningún otro uso de un modelo generativo en producción.

## Decisión

El equipo decide **no incorporar ningún componente generativo en tiempo de ejecución**
en esta entrega. El uso de IA en el proyecto se mantiene donde ya está: como apoyo de
desarrollo (redacción, revisión de código, auditoría), registrado en `docs/ia.md`, y
nunca como parte del sistema que corre en producción.

## Alternativas consideradas

- **Descripciones de objetos generadas automáticamente** a partir de una foto o de
  palabras clave. Se descartó: el modelo actual de `LostObject` no tiene campo de foto,
  y el escenario de calidad de rendimiento (p95 ≤ 2s) ya está en tensión con el
  arranque en frío de la función serverless; agregar una llamada a un proveedor externo
  de IA en el camino crítico de publicación empeoraría esa tensión sin que ningún
  escenario lo exija.
- **Búsqueda semántica** (en vez de la búsqueda por texto exacto que ya existe en
  `GET /objects`). Se descartó por ahora: el volumen de objetos publicados es bajo
  (estimado en cientos al mes, según `docs/despliegue/estimacion-costo-mensual.md`), y
  la búsqueda por texto simple ya cumple el escenario de calidad definido. Introducir
  un proveedor de embeddings añadiría costo por operación y una dependencia externa sin
  un escenario que lo justifique.

## Consecuencias

- No hay conjunto de evaluación, costo por operación ni latencia que reportar para esta
  evidencia, porque no hay componente generativo que evaluar.
- Las amenazas específicas de un componente generativo (inyección de prompt, fuga de
  datos, envenenamiento del contexto), que la semana 13 trabaja con OWASP, no aplican a
  LostVault en su estado actual.
- Si en una iteración futura el equipo decide incorporar uno (por ejemplo, para
  clasificar automáticamente la categoría de un objeto perdido), esta decisión debe
  revisarse con un nuevo ADR que documente el proveedor, el costo por operación, la
  latencia esperada y su evaluación de seguridad, no como una extensión silenciosa de
  este documento.