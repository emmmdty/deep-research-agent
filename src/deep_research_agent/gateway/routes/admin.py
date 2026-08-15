"""Administrator-only model, tool, and runtime configuration routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import Field

from deep_research_agent.gateway.routes.auth import (
    AdminCsrfIdentityDependency,
    AdminIdentityDependency,
    ProductServiceDependency,
    StrictRequest,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"])


class ModelRequest(StrictRequest):
    endpoint_id: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    enabled: bool = True


class ToolRequest(StrictRequest):
    tool_id: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class RuntimeConfigRequest(StrictRequest):
    version_id: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)


@router.post("/models", status_code=status.HTTP_201_CREATED)
def create_model(
    payload: ModelRequest,
    identity: AdminCsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    del identity
    try:
        return service.create_model(payload.model_dump())
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/models")
def list_models(identity: AdminIdentityDependency, service: ProductServiceDependency) -> dict:
    del identity
    return {"models": [service.model_dict(model) for model in service.repository.list_models()]}


@router.post("/tools", status_code=status.HTTP_201_CREATED)
def create_tool(
    payload: ToolRequest,
    identity: AdminCsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    del identity
    return service.create_tool(
        tool_id=payload.tool_id, config=payload.config, enabled=payload.enabled
    )


@router.get("/tools")
def list_tools(identity: AdminIdentityDependency, service: ProductServiceDependency) -> dict:
    del identity
    return {"tools": [service.tool_dict(tool) for tool in service.repository.list_tools()]}


@router.post("/configs", status_code=status.HTTP_201_CREATED)
def create_config(
    payload: RuntimeConfigRequest,
    identity: AdminCsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    del identity
    try:
        return service.create_runtime_config(version_id=payload.version_id, config=payload.config)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/configs")
def list_configs(identity: AdminIdentityDependency, service: ProductServiceDependency) -> dict:
    del identity
    return {
        "configs": [
            service.runtime_config_dict(config)
            for config in service.repository.list_runtime_configs()
        ]
    }


@router.post("/configs/{version_id}:activate")
def activate_config(
    version_id: str,
    identity: AdminCsrfIdentityDependency,
    service: ProductServiceDependency,
) -> dict:
    del identity
    try:
        config = service.repository.activate_runtime_config(version_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="runtime config not found") from exc
    return service.runtime_config_dict(config)


__all__ = ["router"]
