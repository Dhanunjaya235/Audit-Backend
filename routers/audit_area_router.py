"""
Router for Audit Area endpoints.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.auth import token_required
from database.async_db import get_db
from schemas.audit_area import AreaCreate, AreaDetailResponse, AreaResponse, AreaUpdate
from services.audit_area_service import AuditAreaService

router = APIRouter(tags=["Audit Areas"])


def _get_service(db: AsyncSession = Depends(get_db)) -> AuditAreaService:
    return AuditAreaService(db)


# ── List areas by template ───────────────────────────────────────────────


@router.get(
    "/templates/{template_id}/areas",
    response_model=list[AreaDetailResponse],
    summary="List all areas for a template",
)
async def list_areas(
    template_id: UUID,
    service: AuditAreaService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.get_areas_by_template(template_id)


# ── Get single area ─────────────────────────────────────────────────────


@router.get(
    "/areas/{area_id}",
    response_model=AreaDetailResponse,
    summary="Get a single audit area with scopes and questions",
)
async def get_area(
    area_id: UUID,
    service: AuditAreaService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.get_area(area_id)


# ── Create area ──────────────────────────────────────────────────────────


@router.post(
    "/templates/{template_id}/areas",
    response_model=AreaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new audit area to a template",
)
async def create_area(
    template_id: UUID,
    payload: AreaCreate,
    service: AuditAreaService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.create_area(template_id, payload, user_id=current_user.get("user_id"))


# ── Update area ──────────────────────────────────────────────────────────


@router.put(
    "/areas/{area_id}",
    response_model=AreaResponse,
    summary="Update an audit area (name and/or weightage)",
)
async def update_area(
    area_id: UUID,
    payload: AreaUpdate,
    service: AuditAreaService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.update_area(area_id, payload, user_id=current_user.get("user_id"))


# ── Delete area ──────────────────────────────────────────────────────────


@router.delete(
    "/areas/{area_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an audit area",
)
async def delete_area(
    area_id: UUID,
    service: AuditAreaService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    await service.delete_area(area_id, user_id=current_user.get("user_id"))
