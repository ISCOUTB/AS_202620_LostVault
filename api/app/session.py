"""Inicio de sesión con un único usuario (temporal, hasta tener base de datos).

El usuario sale de las variables de entorno AUTH_USER_EMAIL, AUTH_USER_PASSWORD
y, opcionalmente, AUTH_USER_ID. Es el punto de extensión para buscar usuarios
reales en la base de datos.
"""

import secrets
import time

import jwt

from app.config import (
    jwt_algorithm,
    jwt_expires_minutes,
    jwt_secret,
    single_user,
    verified_email_domains,
)
from app.errors import ApiError
from app.models import TokenResponse


def _invalid() -> ApiError:
    return ApiError(401, "INVALID_CREDENTIALS", "Correo o contraseña incorrectos.")


def login(email: str, password: str) -> TokenResponse:
    configured = single_user()
    if configured is None:
        raise ApiError(
            503,
            "AUTH_NOT_CONFIGURED",
            "El inicio de sesión no está configurado en el servidor.",
        )
    user_id, user_email, user_password = configured

    email_n = email.strip().lower()
    domain = email_n.rsplit("@", 1)[1] if "@" in email_n else ""
    if domain not in verified_email_domains():
        raise _invalid()

    # Se comparan ambos campos siempre, en tiempo constante, para no filtrar cuál falló.
    email_ok = secrets.compare_digest(email_n.encode(), user_email.strip().lower().encode())
    password_ok = secrets.compare_digest(password.encode(), user_password.encode())
    if not (email_ok and password_ok):
        raise _invalid()

    expires_in = jwt_expires_minutes() * 60
    token = jwt.encode(
        {
            "sub": user_id,
            "email": user_email.strip().lower(),
            "exp": int(time.time()) + expires_in,
        },
        jwt_secret(),
        algorithm=jwt_algorithm(),
    )
    return TokenResponse(accessToken=token, expiresIn=expires_in)
