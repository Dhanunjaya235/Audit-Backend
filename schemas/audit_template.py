"""
Pydantic schemas for Audit Templates.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.audit_area import (
    AreaCreateNested,
    AreaDetailResponse,
    AreaResponse,
    AreaUpdateNested,
)

# ─── Template Schemas ────────────────────────────────────────────────────────


class TemplateCreate(BaseModel):
    """Create a template with the full tree: areas → scopes → questions → options."""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    areas: list[AreaCreateNested] = Field(
        default=[], description="Audit areas with nested scopes, questions, and options"
    )


class TemplateUpdate(BaseModel):
    """
    Update a template with ID-based merging:
    - Items WITH id → update existing record in place
    - Items WITHOUT id → create new record
    - Existing items NOT in payload → soft-deleted
    """

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    areas: list[AreaUpdateNested] = Field(
        default=[], description="Areas with optional IDs for merging"
    )


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    isactive: bool
    areas: list[AreaResponse] = []
    total_weightage: int = Field(
        default=0,
        description="Sum of area weightages (auto-calculated)",
    )
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateDetailResponse(BaseModel):
    """Full template with nested areas → scopes → questions → options."""

    id: UUID
    name: str
    isactive: bool
    areas: list[AreaDetailResponse] = []
    total_weightage: int = Field(
        default=0,
        description="Sum of area weightages (auto-calculated)",
    )
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateCloneRequest(BaseModel):
    """Clone a template with full modifications: areas → scopes → questions → options."""

    name: str = Field(..., min_length=1, max_length=255, description="Name for the new template")
    areas: list[AreaCreateNested] = Field(
        default=[], description="Modified audit areas with nested scopes, questions, and options"
    )
