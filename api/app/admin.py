"""Panel del encargado y operaciones exclusivas de administración."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse

from app import objects, session
from app.auth import AuthenticatedUser, current_admin
from app.config import single_user
from app.errors import ApiError
from app.models import IntakeRequest, InventoryItem, LoginRequest, ReviewRequest, SuspensionRequest, TokenResponse

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
    body: IntakeRequest,
    request: Request,
    response: Response,
    admin: AuthenticatedUser = Depends(current_admin),
) -> InventoryItem:
    response.headers.update(_NO_STORE)
    store = request.app.state.store
    return objects.create_object(store, admin, body.name, body.description, intake=body)


@router.post("/v1/admin/objects/{object_id}/deliver", tags=["Administración"])
def deliver(
    object_id: str,
    request: Request,
    response: Response,
    _admin: AuthenticatedUser = Depends(current_admin),
) -> InventoryItem:
    response.headers.update(_NO_STORE)
    return objects.mark_delivered(request.app.state.store, object_id, _admin.id)


@router.post("/v1/admin/objects/{object_id}/review", tags=["Administración"])
def review(
    object_id: str, body: ReviewRequest, request: Request, response: Response,
    admin: AuthenticatedUser = Depends(current_admin),
) -> InventoryItem:
    response.headers.update(_NO_STORE)
    return objects.review_claim(
        request.app.state.store, object_id, admin.id, body.decision == "approve", body.reason
    )


@router.get("/v1/admin/users", tags=["Administración"])
def users(request: Request, response: Response, _admin=Depends(current_admin)):
    response.headers.update(_NO_STORE)
    account = single_user()
    if account is None:
        return []
    user_id, email, _ = account
    suspended, _ = request.app.state.store.user_session(user_id)
    return [{"id": user_id, "email": email, "suspended": suspended}]


@router.post("/v1/admin/users/{user_id}/suspension", tags=["Administración"])
def suspension(
    user_id: str, body: SuspensionRequest, request: Request, response: Response,
    _admin=Depends(current_admin),
):
    response.headers.update(_NO_STORE)
    account = single_user()
    if account is None or account[0] != user_id:
        raise ApiError(404, "FORBIDDEN", "La cuenta estudiantil no existe.")
    suspended = request.app.state.store.set_suspended(user_id, body.suspended)
    return {"id": user_id, "email": account[1], "suspended": suspended}
