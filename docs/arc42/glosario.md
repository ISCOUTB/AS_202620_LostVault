# Glosario — LostVault

Este glosario reúne los términos clave utilizados a lo largo de la documentación del proyecto, para asegurar un lenguaje común entre el equipo y los lectores del repositorio.

| Término | Definición |
|---|---|
| **LostVault** | Nombre del proyecto: una plataforma independiente, con identidad visual UTB, para la gestión de objetos perdidos y encontrados dentro de la universidad. |
| **Monolito modular** | Estilo arquitectónico adoptado por el proyecto: la aplicación se despliega como una sola unidad, pero internamente está organizada en módulos independientes con responsabilidades separadas. |
| **Módulo** | Unidad funcional independiente del sistema (ej: `objects`, `search`, `claims`), dueña de su propia lógica interna, que solo expone al resto del sistema lo que decide hacer público. |
| **Authentication** | Módulo encargado del registro, inicio y cierre de sesión, y de validar que un usuario esté autenticado en el sistema. |
| **Identity Verification** | Módulo encargado de verificar que la persona que reclama un objeto es realmente su dueño, mediante una foto con cédula y carné estudiantil. |
| **Claims** | Módulo que gestiona el proceso de reclamación de un objeto perdido, desde que el usuario lo solicita hasta que se confirma la entrega. |
| **Objects** | Módulo encargado de la publicación y gestión de los objetos perdidos o encontrados dentro de la plataforma. |
| **Search** | Módulo que permite buscar y filtrar los objetos publicados en el sistema. |
| **Users** | Módulo que almacena la información de perfil de los usuarios (nombre, carné, tipo de usuario: estudiante u oficina). |
| **ADR (Architecture Decision Record)** | Documento que registra una decisión arquitectónica importante, junto con su contexto, alternativas consideradas y consecuencias. |
| **Escenario de calidad** | Descripción concreta y medible de cómo debe responder el sistema ante un estímulo específico, compuesta de seis partes: fuente, estímulo, artefacto, entorno, respuesta y medida. |
| **Atributo de calidad** | Característica no funcional que el sistema debe cumplir (ej: disponibilidad, usabilidad, seguridad, rendimiento). |
| **Árbol de utilidad** | Herramienta que organiza los atributos de calidad de un sistema en una jerarquía, priorizándolos según su impacto en el negocio y su riesgo técnico. |
| **arc42** | Plantilla estándar utilizada para documentar la arquitectura de software de un sistema, organizada en 12 secciones temáticas. |
| **C4 (Nivel 1 / Nivel 2)** | Modelo de diagramas de arquitectura por niveles de zoom: Nivel 1 (Contexto) muestra el sistema y sus actores externos; Nivel 2 (Contenedores) muestra las piezas internas principales del sistema. |
| **Corte vertical** | Porción reducida pero completa de una funcionalidad, implementada de punta a punta (desde la interfaz hasta la persistencia), usada para validar que la arquitectura elegida funciona en la práctica. |
| **Restricción** | Condición impuesta al proyecto que no es negociable por el equipo (ej: plazo del semestre, infraestructura gratuita, alojamiento en ISCOUTB). |
