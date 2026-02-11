"""
Router for Audit Template endpoints.
Handles only request/response — delegates business logic to the service.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.auth import token_required
from database.async_db import get_db
from schemas.audit_template import (
    TemplateCloneRequest,
    TemplateCreate,
    TemplateDetailResponse,
    TemplateResponse,
    TemplateUpdate,
)
from services.audit_template_service import AuditTemplateService

router = APIRouter(prefix="/templates", tags=["Audit Templates"])


def _get_service(db: AsyncSession = Depends(get_db)) -> AuditTemplateService:
    return AuditTemplateService(db)


# ── List all templates ────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[TemplateResponse],
    summary="List all audit templates",
)
async def list_templates(
    include_inactive: bool = Query(False, description="Include soft-deleted templates"),
    service: AuditTemplateService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.get_all_templates(include_inactive=include_inactive)


# ── Seed default template (US 3.1) ───────────────────────────────────────


@router.post(
    "/default",
    response_model=TemplateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Seed or retrieve the default audit template",
)
async def seed_default_template(
    service: AuditTemplateService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.seed_default_template(user_id=current_user.get("user_id"))


# ── Get template detail ──────────────────────────────────────────────────


@router.get(
    "/{template_id}",
    response_model=TemplateDetailResponse,
    summary="Get template with full details (areas → scopes → questions → options)",
)
async def get_template(
    template_id: UUID,
    service: AuditTemplateService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.get_template_detail(template_id)


# ── Create template ──────────────────────────────────────────────────────


@router.post(
    "",
    response_model=TemplateDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new audit template with full tree (areas → scopes → questions → options)",
)
async def create_template(
    payload: TemplateCreate,
    service: AuditTemplateService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.create_template(payload, user_id=current_user.get("user_id"))


# ── Update template ──────────────────────────────────────────────────────


@router.put(
    "/{template_id}",
    response_model=TemplateDetailResponse,
    summary="Update a template (replaces entire tree with provided data)",
)
async def update_template(
    template_id: UUID,
    payload: TemplateUpdate,
    service: AuditTemplateService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.update_template(template_id, payload, user_id=current_user.get("user_id"))


# ── Delete template (soft) ───────────────────────────────────────────────


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete an audit template",
)
async def delete_template(
    template_id: UUID,
    service: AuditTemplateService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    await service.delete_template(template_id, user_id=current_user.get("user_id"))


# ── Clone template (US 3.2) ──────────────────────────────────────────────


@router.post(
    "/{template_id}/clone",
    response_model=TemplateDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone a template with modifications (creates a completely new template from modified data)",
)
async def clone_template(
    template_id: UUID,
    payload: TemplateCloneRequest,
    service: AuditTemplateService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.clone_template(template_id, payload, user_id=current_user.get("user_id"))
