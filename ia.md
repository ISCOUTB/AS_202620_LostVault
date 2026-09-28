# Uso de IA en este proyecto — LostVault

Este documento registra, de forma transparente, el trabajo hecho con asistencia
de inteligencia artificial (Claude, de Anthropic, usado en modo Cowork) durante
esta sesión de trabajo sobre el proyecto LostVault. El objetivo es que cualquier
persona (equipo, profesor, evaluador) pueda ver exactamente qué se le pidió a la
IA, qué produjo, qué se verificó de verdad y qué quedó como responsabilidad del
equipo.

## 1. Herramienta usada

Claude (Anthropic), en un entorno de trabajo en la nube con acceso a un
filesystem propio, shell, y herramientas de lectura/escritura de archivos y
búsqueda web. **Sin acceso de escritura al repositorio real de GitHub, sin el
SDK de Flutter/Dart instalado, y con acceso de red restringido a un conjunto
de dominios permitidos** (detallado en la sección 5). Todo el trabajo se hizo
sobre copias locales de los archivos del proyecto, subidas como archivos
comprimidos (.zip) por el equipo, y se entregó como paquetes de archivos para
que el equipo los aplicara manualmente con `git`.

## 2. Alcance de esta sesión (cronología)

### Fase 1 — Análisis inicial del proyecto

El equipo subió una primera copia del repositorio (solo la app Flutter
in-memory, sin backend) y pidió corregir una descripción previa del proyecto
que circulaba con datos incorrectos (afirmaba FastAPI + MySQL + Docker, que no
existían en ese momento). Se leyó el código fuente completo (los 6 módulos de
`lib/features/`, `core/`, tests, ADR 0001, documento de mapeo DDD) y se
generó `LostVault_analisis_completo.txt`: un documento con el estado real del
proyecto y lo que le faltaba.

### Fase 2 — Contrato de integración (entrega de otra semana)

El equipo pegó una rúbrica (vía WhatsApp) pidiendo un contrato OpenAPI/AsyncAPI
versionado, una prueba de contrato en el pipeline, y un ADR justificando la
estrategia de integración, para el alcance Objects + Claims. Se generaron:

- `openapi/objects-claims.v1.yaml` + esquemas JSON Schema.
- Métodos `toJson()` en los modelos de dominio (`LostObject`, `Claim`).
- `test/contract/schema_validator.dart` (validador de JSON Schema escrito a
  mano, sin dependencias de pub.dev — ver limitación en la sección 5) y su
  suite de pruebas.
- `.github/workflows/contract.yml` (lint de OpenAPI + pruebas de contrato).
- `docs/adr/0002-estrategia-integracion-objects-claims.md` (Estado: Propuesto).
- Un PDF de una página resumiendo el contrato, y un zip entregable con
  instrucciones exactas de `git` para aplicarlo.

### Fase 3 — Segundo análisis: estado real del proyecto

El equipo subió una segunda copia del repositorio, ya con un backend real en
FastAPI (`backend/main.py`) desplegado en Vercel, su propio contrato OpenAPI
(`docs/contracts/lostvault-api.yaml`, distinto del generado en la Fase 2) y su
propio ADR 0002 (aceptado, mejor alineado con el backend real que el de la
Fase 2). Se leyó todo el código nuevo, la configuración de CI, SonarCloud, y
los documentos de despliegue existentes.

### Fase 4 — Corrección de los criterios en rojo (Semana 8: Despliegue y
operación)

El equipo compartió el texto completo de la rúbrica de la semana y una tabla
propia con 18 criterios marcados en verde/amarillo/rojo, y pidió resolver los
que estaban en rojo. Antes de tocar nada, se verificó en vivo (peticiones HTTP
reales contra `https://backend-nu-self-91.vercel.app`) cuáles de esos
criterios ya funcionaban y cuáles no, para no arreglar algo que no estaba
roto. Ver el detalle completo de cada cambio en la sección 3 y en
`docs/despliegue/evidencias-profesor.md`.

### Fase 5 — Diagnóstico de un fallo real de CI (PR #10)

El equipo (Fausto) compartió capturas del historial de builds de GitHub
Actions y el log de error de un build fallido (`sonar-scanner.bat failed with
exit code 1`). Se diagnosticó la causa (GitHub no expone secrets del
repositorio a workflows disparados por `pull_request` desde un fork) y se
corrigió `.github/workflows/build.yml` para que el job de SonarQube se salte
en PRs desde forks y solo corra en `push` a `main` o en PRs desde ramas
internas del repositorio.

## 3. Qué se le pidió a la IA y qué produjo (Fase 4, esta entrega)

| Criterio en rojo | Qué se pidió | Qué se hizo | Archivo(s) |
|---|---|---|---|
| SonarCloud (Quality Gate fallando) | Arreglar el análisis y que el pipeline bloquee si el gate queda rojo | Se activaron `sonar.sources`/tests/cobertura (estaban comentados); se agregó `pytest-cov`; se cambió el runner de `build.yml` de Windows a Ubuntu y se le agregaron pruebas de Flutter y del backend con cobertura antes del escaneo; se agregó un paso que hace fallar el pipeline si el gate queda rojo | `sonar-project.properties`, `backend/requirements-dev.txt`, `.github/workflows/backend.yml`, `.github/workflows/build.yml` |
| Sistema desplegado / Health check en producción | Conseguir evidencia | Verificado en vivo por HTTP — ya funcionaban; se documentó como evidencia en vez de "arreglarlos" | `docs/despliegue/evidencias-profesor.md` |
| Logs en producción | Conseguir evidencia | Documentado el formato de logs estructurados y la prueba que verifica que el token JWT nunca aparece en ellos | `docs/despliegue/evidencias-profesor.md` |
| p95 en producción | Conseguir evidencia | Se intentó generar tráfico real; se descubrió que Vercel no comparte estado en memoria entre invocaciones bajo tráfico ligero, así que el p95 nunca puede acumular muestras con el diseño actual — documentado como hallazgo arquitectónico, con la solución recomendada (almacén externo) marcada como trabajo futuro | `docs/arc42/07_vista_despliegue.md`, `docs/despliegue/evidencias-profesor.md` |
| Guía de despliegue | Actualizarla | Ya existía y estaba bien (`backend/DEPLOY_VERCEL.md`); se conectó con una vista arc42 nueva que mapea dónde corre cada pieza del sistema | `docs/arc42/07_vista_despliegue.md` |
| Estimación de costo mensual | Corregirla | La fila de la API asumía "servidor del laboratorio" (nunca confirmado); se corrigió para reflejar Vercel, ya verificado | `docs/despliegue/estimacion-costo-mensual.md` |
| Evidencias para el profesor | Organizarlas | Documento único que junta todo lo anterior | `docs/despliegue/evidencias-profesor.md` |
| (No pedido explícitamente, pero requerido por la rúbrica) ADR de plataforma real | — | No existía un ADR para la decisión de Vercel (el único ADR de despliegue que había era de un ejercicio de laboratorio aparte); se creó uno nuevo | `docs/adr/0003-plataforma-despliegue-vercel.md` |
| (No pedido explícitamente) IaC versionada | — | No existía ninguna; se agregó `vercel.json` (aplicado) y un Terraform opcional (no aplicado, requiere credenciales del equipo) | `backend/vercel.json`, `infra/terraform/` |

## 4. Decisiones que la IA tomó vs. las que quedan en manos del equipo

La IA **sí** decidió: cómo estructurar la configuración de SonarCloud, cómo
redactar los ADR y la vista arc42 siguiendo el formato ya usado por el equipo,
y cómo diagnosticar la causa raíz de cada falla a partir del código y de
pruebas en vivo.

La IA **no** decidió ni puede decidir: si el equipo aprueba el ADR 0003 como
"Aceptado" definitivo, si se prioriza resolver la limitación de p95 en una
entrega futura, si se adopta el Terraform opcional, ni si se le da acceso de
colaborador a Fausto en vez de seguir usando su fork. Tampoco pudo confirmar
que el pipeline corra en verde después de aplicar los cambios — eso solo se
sabe haciendo push real al repositorio, algo que la IA no tiene permiso de
hacer.

## 5. Limitaciones honestas del entorno de trabajo

- Sin acceso de escritura al repositorio real de GitHub: todo se entregó como
  archivos + instrucciones de `git` para que el equipo los aplicara.
- Sin el SDK de Flutter/Dart instalado (bloqueado por política de red del
  entorno hacia `storage.googleapis.com`/`pub.dev`): no se pudo correr
  `flutter analyze`/`flutter test` directamente; se usaron validaciones
  cruzadas con Python (`jsonschema`, PyYAML) donde fue posible.
- Sin acceso a `sonarcloud.io` (bloqueado por política de red del entorno): no
  se pudo confirmar el resultado real del próximo análisis de SonarCloud, solo
  corregir la configuración que causaba que analizara sobre prácticamente
  nada.
- Sí se pudo verificar en vivo, por HTTP, el estado real de la API en
  producción (`https://backend-nu-self-91.vercel.app`) — esa evidencia es
  real, no simulada.

## 6. Archivos de esta sesión

Ver la lista completa y actualizada en `docs/despliegue/evidencias-profesor.md`
(sección 10) y en `LostVault_analisis_completo.txt` (documento acumulado de
todo el proyecto, con el detalle de las 5 fases de esta sección 2).
