"""Authentication routes and shared product API dependencies."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from deep_research_agent.product.auth import SESSION_COOKIE_NAME, SESSION_TTL, SessionIdentity
from deep_research_agent.product.service import ProductService


router = APIRouter(tags=["authentication"])


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(StrictRequest):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)


class AcceptInvitationRequest(StrictRequest):
    password: str = Field(min_length=12)


class InvitationRequest(StrictRequest):
    email: str = Field(min_length=3, max_length=320)
    tenant_id: str = Field(min_length=1, max_length=128)
    role: Literal["user", "admin"] = "user"


def get_product_service(request: Request) -> ProductService:
    service = getattr(request.app.state, "product_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="the product database is not configured")
    return service


ProductServiceDependency = Annotated[ProductService, Depends(get_product_service)]


def current_identity(
    request: Request,
    service: ProductServiceDependency,
) -> SessionIdentity:
    identity = service.auth.authenticate(request.cookies.get(SESSION_COOKIE_NAME))
    if identity is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return identity


IdentityDependency = Annotated[SessionIdentity, Depends(current_identity)]


def csrf_identity(
    identity: IdentityDependency,
    service: ProductServiceDependency,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> SessionIdentity:
    if not service.auth.verify_csrf(identity, csrf_token):
        raise HTTPException(status_code=403, detail="invalid CSRF token")
    return identity


CsrfIdentityDependency = Annotated[SessionIdentity, Depends(csrf_identity)]


def admin_identity(identity: IdentityDependency) -> SessionIdentity:
    if identity.role != "admin":
        raise HTTPException(status_code=403, detail="administrator role required")
    return identity


AdminIdentityDependency = Annotated[SessionIdentity, Depends(admin_identity)]


def admin_csrf_identity(identity: CsrfIdentityDependency) -> SessionIdentity:
    if identity.role != "admin":
        raise HTTPException(status_code=403, detail="administrator role required")
    return identity


AdminCsrfIdentityDependency = Annotated[SessionIdentity, Depends(admin_csrf_identity)]


@router.post("/v1/auth/login")
def login(payload: LoginRequest, response: Response, service: ProductServiceDependency) -> dict:
    try:
        login_session = service.auth.login(email=payload.email, password=payload.password)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="invalid email or password") from exc
    response.set_cookie(
        SESSION_COOKIE_NAME,
        login_session.session_token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=not service.database.offline_mode,
        samesite="strict",
        path="/",
    )
    return {
        "user": {
            "user_id": login_session.identity.user_id,
            "tenant_id": login_session.identity.tenant_id,
            "email": login_session.identity.email,
            "role": login_session.identity.role,
        },
        "csrf_token": login_session.csrf_token,
    }


@router.get("/v1/auth/session")
def session(identity: IdentityDependency) -> dict:
    return {
        "user": {
            "user_id": identity.user_id,
            "tenant_id": identity.tenant_id,
            "email": identity.email,
            "role": identity.role,
        }
    }


@router.post("/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    identity: CsrfIdentityDependency,
    service: ProductServiceDependency,
) -> Response:
    del identity
    service.auth.logout(request.cookies.get(SESSION_COOKIE_NAME))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", httponly=True, samesite="strict")
    return response


@router.post("/v1/auth/invitations/{invite_token}/accept", status_code=status.HTTP_201_CREATED)
def accept_invitation(
    invite_token: str,
    payload: AcceptInvitationRequest,
    service: ProductServiceDependency,
) -> dict:
    try:
        user = service.auth.accept_invitation(invite_token, password=payload.password)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="invitation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"user": service.user_dict(user)}


@router.post("/v1/admin/invitations", status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationRequest,
    identity: AdminCsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    try:
        invitation, token = service.auth.create_invitation(
            email=payload.email,
            tenant_id=payload.tenant_id,
            role=payload.role,
            invited_by=identity.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "invitation_id": invitation.invitation_id,
        "email": invitation.email,
        "tenant_id": invitation.tenant_id,
        "role": invitation.role,
        "expires_at": invitation.expires_at.isoformat(),
        "invite_token": token,
    }


__all__ = [
    "AdminCsrfIdentityDependency",
    "AdminIdentityDependency",
    "CsrfIdentityDependency",
    "IdentityDependency",
    "ProductServiceDependency",
    "get_product_service",
    "router",
]

