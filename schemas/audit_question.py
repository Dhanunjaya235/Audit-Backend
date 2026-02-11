"""
Pydantic schemas for Audit Scopes, Questions, and Question Options.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ─── Question Option Schemas ─────────────────────────────────────────────────


class OptionCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=255, description="Option label text")
    value: int = Field(..., ge=0, le=5, description="Numeric value for the option (0–5)")


class OptionUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=255)
    value: int | None = Field(None, ge=0, le=5)


class OptionResponse(BaseModel):
    id: UUID
    question_id: UUID
    label: str
    value: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Question Schemas ────────────────────────────────────────────────────────


class QuestionCreate(BaseModel):
    text: str = Field(..., min_length=1, description="Audit question text")
    percentage: int = Field(..., ge=0, le=100, description="Question weightage percentage")
    is_mandatory: bool = Field(default=True, description="Whether question is mandatory")
    options: list[OptionCreate] | None = Field(
        default=None,
        description="Optional list of scoring options to create with the question",
    )


class QuestionUpdate(BaseModel):
    text: str | None = Field(None, min_length=1)
    percentage: int | None = Field(None, ge=0, le=100)
    is_mandatory: bool | None = None


class QuestionResponse(BaseModel):
    id: UUID
    scope_id: UUID
    text: str
    percentage: int
    is_mandatory: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionDetailResponse(BaseModel):
    id: UUID
    scope_id: UUID
    text: str
    percentage: int
    is_mandatory: bool
    options: list[OptionResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Scope Schemas ───────────────────────────────────────────────────────────


class ScopeCreate(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=255, description="Scope name (e.g. Schedule, Quality)"
    )


class ScopeCreateNested(BaseModel):
    """Scope with nested questions + options for bulk template creation."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Scope name (e.g. Schedule, Quality)"
    )
    questions: list[QuestionCreate] = Field(default=[], description="Questions within this scope")


class ScopeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)


# ─── Nested Update Schemas (for template update with ID-based merging) ────────


class OptionUpdateNested(BaseModel):
    """Option in update payload. id=None means create new, id=UUID means update existing."""

    id: UUID | None = Field(default=None, description="Existing option ID (omit for new)")
    label: str = Field(..., min_length=1, max_length=255, description="Option label text")
    value: int = Field(..., ge=0, le=5, description="Numeric value for the option (0–5)")


class QuestionUpdateNested(BaseModel):
    """Question in update payload. id=None means create new, id=UUID means update existing."""

    id: UUID | None = Field(default=None, description="Existing question ID (omit for new)")
    text: str = Field(..., min_length=1, description="Audit question text")
    percentage: int = Field(..., ge=0, le=100, description="Question weightage percentage")
    is_mandatory: bool = Field(default=True, description="Whether question is mandatory")
    options: list[OptionUpdateNested] = Field(
        default=[], description="Scoring options for this question"
    )


class ScopeUpdateNested(BaseModel):
    """Scope in update payload. id=None means create new, id=UUID means update existing."""

    id: UUID | None = Field(default=None, description="Existing scope ID (omit for new)")
    name: str = Field(
        ..., min_length=1, max_length=255, description="Scope name (e.g. Schedule, Quality)"
    )
    questions: list[QuestionUpdateNested] = Field(
        default=[], description="Questions within this scope"
    )


# ─── Response Schemas ────────────────────────────────────────────────────────


class ScopeResponse(BaseModel):
    id: UUID
    area_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScopeDetailResponse(BaseModel):
    id: UUID
    area_id: UUID
    name: str
    questions: list[QuestionDetailResponse] = []
    total_percentage: int = Field(
        default=0,
        description="Sum of question percentages in this scope (auto-calculated)",
    )
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
