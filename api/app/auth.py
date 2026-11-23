"""Autenticación Bearer JWT: el proveedor identifica al usuario por el token."""

from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import jwt_algorithm, jwt_secret
from app.errors import ApiError

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str | None
    is_admin: bool = False


def _unauthenticated(message: str) -> ApiError:
    return ApiError(
        401,
        "UNAUTHENTICATED",
        message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthenticated("Debes iniciar sesión.")

    try:
        payload = jwt.decode(
            credentials.credentials,
            jwt_secret(),
            algorithms=[jwt_algorithm()],
            options={"require": ["sub", "exp"]},
        )
    except jwt.PyJWTError:
        raise _unauthenticated("Token inválido o expirado.") from None

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise _unauthenticated("Token inválido.")

    email = payload.get("email")
    return AuthenticatedUser(
        id=sub,
        email=email if isinstance(email, str) else None,
        is_admin=payload.get("role") == "admin",
    )


def current_admin(user: AuthenticatedUser = Depends(current_user)) -> AuthenticatedUser:
    if not user.is_admin:
        raise ApiError(403, "FORBIDDEN", "Se requiere una cuenta de administrador.")
    return user
