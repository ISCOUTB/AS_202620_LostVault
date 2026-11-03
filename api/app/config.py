"""Configuración leída de variables de entorno."""

import os


def jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET no está configurado. Define una cadena larga y aleatoria."
        )
    return secret


def jwt_algorithm() -> str:
    return os.environ.get("JWT_ALGORITHM", "HS256")


def verified_email_domains() -> set[str]:
    """Dominios de correo cuya identidad se considera verificada."""
    raw = os.environ.get("VERIFIED_EMAIL_DOMAINS", "utb.edu.co")
    return {d.strip().lower() for d in raw.split(",") if d.strip()}


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


def port() -> int:
    """Puerto en el que escucha el servidor (lo usa el Dockerfile)."""
    return int(os.environ.get("PORT", "8000"))


def database_url() -> str | None:
    """URL de la base de datos. Todavía no se usa: el almacenamiento es en memoria.

    Cuando exista la base de datos, define DATABASE_URL y reemplaza app/store.py.
    """
    return os.environ.get("DATABASE_URL") or None


def jwt_expires_minutes() -> int:
    return int(os.environ.get("JWT_EXPIRES_MINUTES", "60"))


def single_user() -> tuple[str, str, str] | None:
    """Usuario único temporal: (id, correo, contraseña), o None si no está configurado."""
    email = os.environ.get("AUTH_USER_EMAIL", "").strip()
    password = os.environ.get("AUTH_USER_PASSWORD", "")
    if not email or not password:
        return None
    user_id = os.environ.get("AUTH_USER_ID", "").strip() or "user-1"
    return user_id, email, password
