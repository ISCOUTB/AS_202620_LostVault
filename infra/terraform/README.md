# IaC opcional — Terraform para el proyecto Vercel

Este directorio es **opcional**, tal como lo indica la guía de la semana
("Terraform: opcional"). El requisito real de esta entrega es tener alguna
infraestructura versionada como código; eso ya lo cumple
[`backend/vercel.json`](../../backend/vercel.json), que fija explícitamente
el runtime de la función (`python3.12`) en vez de depender solo de la
detección automática de Vercel.

Este Terraform es un espejo declarativo de esa misma configuración para el
equipo que quiera adoptar Terraform formalmente más adelante. **No se aplicó
desde este entorno** — no hay acceso a un token de API de Vercel del equipo
aquí, y nunca debe pedirse ni compartirse ese token en texto plano.

## Si el equipo decide usarlo

1. Instalar Terraform (ver <https://developer.hashicorp.com/terraform>,
   recurso dado esta semana).
2. Exportar el token propio del equipo, nunca committearlo:
   ```bash
   export TF_VAR_vercel_api_token="..."
   ```
3. Importar el proyecto ya existente (no recrearlo — ya está desplegado y
   funcionando):
   ```bash
   terraform init
   terraform import vercel_project.backend <project-id-de-vercel>
   ```
4. Revisar el plan con cuidado antes de aplicar nada:
   ```bash
   terraform plan
   ```
   Si el plan propone recrear el proyecto o cambiar `root_directory`,
   **no aplicar** — significa que algún valor en `main.tf` no coincide con
   la configuración real y hay que ajustarlo primero.
5. El valor real de `JWT_SECRET` **nunca** va en este archivo ni en el
   estado de Terraform en texto plano sin cifrar; gestionarlo con un backend
   remoto cifrado o seguir configurándolo manualmente en el dashboard de
   Vercel, y dejar aquí solo la declaración de que la variable existe.

## Por qué no se aplicó como parte de esta entrega

Aplicar Terraform contra un proyecto real requiere credenciales que solo el
equipo tiene, y un `terraform import` mal hecho puede desincronizar el
estado con la configuración real en producción. El riesgo de romper el
despliegue que ya funciona no se justifica para cumplir un requisito que la
guía marca como opcional. La configuración real y verificada sigue siendo
`backend/vercel.json` + el dashboard de Vercel.
