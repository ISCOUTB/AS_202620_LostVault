"""Panel del encargado y operaciones exclusivas de administración."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse

from app import objects, session
from app.auth import AuthenticatedUser, current_admin
from app.models import CreateObjectRequest, InventoryItem, LoginRequest, TokenResponse

router = APIRouter()
_page = Path(__file__).with_name("admin.html")
_NO_STORE = {"Cache-Control": "no-store"}


@router.get("/admin", include_in_schema=False)
def panel() -> FileResponse:
    return FileResponse(_page, headers=_NO_STORE)


@router.post("/v1/admin/login", tags=["Administración"])
def login(body: LoginRequest, response: Response) -> TokenResponse:
    response.headers.update(_NO_STORE)
    return session.login_admin(body.email, body.password)


@router.get("/v1/admin/objects", tags=["Administración"])
def inventory(
    request: Request,
    response: Response,
    _admin: AuthenticatedUser = Depends(current_admin),
) -> list[InventoryItem]:
    response.headers.update(_NO_STORE)
    return objects.list_inventory(request.app.state.store)


@router.post("/v1/admin/objects", status_code=201, tags=["Administración"])
def register_object(
    body: CreateObjectRequest,
    request: Request,
    response: Response,
    admin: AuthenticatedUser = Depends(current_admin),
) -> InventoryItem:
    response.headers.update(_NO_STORE)
    obj = objects.create_object(request.app.state.store, admin, body.name, body.description)
    return InventoryItem(id=obj.id, name=obj.name, description=obj.description, status="available")


@router.post("/v1/admin/objects/{object_id}/deliver", tags=["Administración"])
def deliver(
    object_id: str,
    request: Request,
    response: Response,
    _admin: AuthenticatedUser = Depends(current_admin),
) -> InventoryItem:
    response.headers.update(_NO_STORE)
    return objects.mark_delivered(request.app.state.store, object_id)
