########################################################################
# LostVault — IaC opcional para el proyecto Vercel del backend
#
# Este archivo NO se aplicó (no hay `terraform apply` ejecutado desde este
# entorno: requeriría un token de API de Vercel del equipo, que nadie más
# que ustedes debe compartir). Se entrega como IaC versionada opcional,
# usando el proveedor oficial de Vercel, tal como lo pide la guía de la
# semana para quien quiera declarar la infraestructura como código en vez
# de configurarla solo por el dashboard.
#
# La fuente de verdad operativa sigue siendo `backend/vercel.json` (Zero-
# Config + runtime fijado) y `backend/DEPLOY_VERCEL.md`. Este Terraform es
# un espejo declarativo de esa misma configuración, para el equipo que
# quiera adoptarlo formalmente.
########################################################################

terraform {
  required_providers {
    vercel = {
      source  = "vercel/vercel"
      version = "~> 1.0"
    }
  }
}

variable "vercel_api_token" {
  description = "Token de API de Vercel del equipo. Nunca se versiona; se pasa por variable de entorno TF_VAR_vercel_api_token o -var en la CLI."
  type        = string
  sensitive   = true
}

variable "vercel_team_id" {
  description = "ID del equipo/organización en Vercel (shamara-llorente-s-projects), si el proyecto vive bajo un team en vez de una cuenta personal."
  type        = string
  default     = null
}

provider "vercel" {
  api_token = var.vercel_api_token
  team      = var.vercel_team_id
}

# Importar el proyecto existente con:
#   terraform import vercel_project.backend <project-id>
# (el project-id se obtiene en Vercel: Settings del proyecto "backend").
resource "vercel_project" "backend" {
  name      = "backend"
  framework = null # Zero-Config Python, sin framework de build de Vercel

  git_repository = {
    type = "github"
    repo = "ISCOUTB/AS_202620_LostVault"
  }

  root_directory = "backend"
}

resource "vercel_project_environment_variable" "jwt_secret" {
  project_id = vercel_project.backend.id
  key        = "JWT_SECRET"
  value      = "REEMPLAZAR-fuera-de-este-archivo" # nunca committear el valor real
  target     = ["production", "preview"]
  sensitive  = true
}

resource "vercel_project_environment_variable" "log_level" {
  project_id = vercel_project.backend.id
  key        = "LOG_LEVEL"
  value      = "INFO"
  target     = ["production", "preview", "development"]
}
