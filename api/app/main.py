"""Aplicación FastAPI de LostVault Claims API."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app import objects, service, session
from app.auth import AuthenticatedUser, current_user
from app.config import cors_origins, jwt_secret
from app.errors import ApiError, api_error_handler, validation_error_handler
from app.models import (
    Claim,
    CreateObjectRequest,
    LoginRequest,
    LostObjectOut,
    Problem,
    TokenResponse,
)
from app.store import ClaimStore


@asynccontextmanager
async def lifespan(_app: FastAPI):
    jwt_secret()  # falla al arrancar si falta JWT_SECRET
    yield


def create_app(store: ClaimStore | None = None) -> FastAPI:
    app = FastAPI(
        title="LostVault Claims API",
        version="1.0.0",
        description=(
            "Frontera HTTP para reclamar un objeto perdido. "
            "Implementa el contrato docs/contracts/lostvault-api.yaml."
        ),
        lifespan=lifespan,
    )
    app.state.store = store if store is not None else ClaimStore()
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    origins = cors_origins()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["POST", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
            expose_headers=["Idempotent-Replayed"],
        )

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/v1/auth/login",
        operation_id="login",
        summary="Inicia sesión con correo institucional y contraseña.",
        response_model=TokenResponse,
        responses={
            401: {"model": Problem, "description": "Credenciales incorrectas."},
            422: {"model": Problem, "description": "Cuerpo inválido."},
            503: {"model": Problem, "description": "Login no configurado en el servidor."},
        },
    )
    def login(body: LoginRequest) -> TokenResponse:
        return session.login(body.email, body.password)

    @app.post(
        "/v1/objects",
        operation_id="createObject",
        summary="Registra un objeto perdido.",
        status_code=201,
        response_model=LostObjectOut,
        responses={
            401: {"model": Problem, "description": "No existe una sesión autenticada."},
            422: {"model": Problem, "description": "Cuerpo inválido."},
        },
    )
    def create_object(
        body: CreateObjectRequest,
        request: Request,
        user: AuthenticatedUser = Depends(current_user),
    ) -> LostObjectOut:
        return objects.create_object(
            request.app.state.store, user, body.name, body.description
        )

    @app.delete(
        "/v1/objects/{objectId}",
        operation_id="deleteObject",
        summary="Borra un objeto perdido que reportó el propio usuario.",
        status_code=204,
        responses={
            401: {"model": Problem, "description": "No existe una sesión autenticada."},
            403: {"model": Problem, "description": "El objeto lo reportó otro usuario."},
            404: {"model": Problem, "description": "El objeto solicitado no existe."},
            409: {"model": Problem, "description": "El objeto ya fue reclamado."},
        },
    )
    def delete_object(
        objectId: str,
        request: Request,
        user: AuthenticatedUser = Depends(current_user),
    ) -> Response:
        objects.delete_object(request.app.state.store, user, objectId)
        return Response(status_code=204)

    @app.post(
        "/v1/objects/{objectId}/claims",
        operation_id="createClaim",
        summary="Solicita la reclamación de un objeto disponible.",
        status_code=201,
        response_model=Claim,
        responses={
            200: {
                "model": Claim,
                "description": "El objeto ya estaba reclamado por este mismo usuario.",
            },
            400: {"model": Problem, "description": "Idempotency-Key inválida."},
            401: {"model": Problem, "description": "No existe una sesión autenticada."},
            404: {"model": Problem, "description": "El objeto solicitado no existe."},
            409: {"model": Problem, "description": "El objeto ya fue reclamado."},
            422: {
                "model": Problem,
                "description": "Identidad no verificada o Idempotency-Key reutilizada.",
            },
        },
    )
    def create_claim(
        objectId: str,
        request: Request,
        response: Response,
        user: AuthenticatedUser = Depends(current_user),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> Claim:
        outcome = service.create_claim(
            request.app.state.store, user, objectId, idempotency_key
        )
        response.status_code = outcome.status_code
        if outcome.replayed:
            response.headers["Idempotent-Replayed"] = "true"
        return outcome.claim

    return app


app = create_app()
