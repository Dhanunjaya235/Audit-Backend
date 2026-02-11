"""
Pydantic schemas for Audit Areas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.audit_question import ScopeCreateNested, ScopeDetailResponse, ScopeUpdateNested

# ─── Area Schemas ────────────────────────────────────────────────────────────


class AreaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Audit area name")
    weightage: int = Field(..., ge=1, le=100, description="Area weightage (1–100)")


class AreaCreateNested(BaseModel):
    """Area with nested scopes → questions → options for bulk template creation."""

    name: str = Field(..., min_length=1, max_length=255, description="Audit area name")
    weightage: int = Field(..., ge=1, le=100, description="Area weightage (1–100)")
    scopes: list[ScopeCreateNested] = Field(default=[], description="Scopes within this area")


class AreaUpdateNested(BaseModel):
    """Area in update payload. id=None means create new, id=UUID means update existing."""

    id: UUID | None = Field(default=None, description="Existing area ID (omit for new)")
    name: str = Field(..., min_length=1, max_length=255, description="Audit area name")
    weightage: int = Field(..., ge=1, le=100, description="Area weightage (1–100)")
    scopes: list[ScopeUpdateNested] = Field(default=[], description="Scopes within this area")


class AreaUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    weightage: int | None = Field(None, ge=1, le=100)


class AreaResponse(BaseModel):
    id: UUID
    template_id: UUID
    name: str
    weightage: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AreaDetailResponse(BaseModel):
    id: UUID
    template_id: UUID
    name: str
    weightage: int
    scopes: list[ScopeDetailResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
