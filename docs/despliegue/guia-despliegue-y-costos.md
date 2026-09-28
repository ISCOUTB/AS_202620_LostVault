# Guía de despliegue y costos — LostVault

## 1. Descripción

LostVault es una plataforma para la gestión de objetos perdidos y encontrados dentro de la Universidad Tecnológica de Bolívar.

Esta guía documenta la infraestructura necesaria para ejecutar el sistema, las variables de configuración, las comprobaciones de salud, las métricas y la estimación del costo mensual.

## 2. Arquitectura de despliegue

El sistema utiliza:

- Cliente: Flutter.
- Backend: FastAPI.
- Contenedorización: Docker.
- Orquestación local: Docker Compose.
- Integración continua: GitHub Actions.
- Análisis de calidad: SonarCloud.

## 3. Ejecución local

Desde la raíz del repositorio se puede ejecutar el backend mediante Docker Compose:

```bash
docker compose up --build
