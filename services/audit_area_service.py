"""
Service layer for Audit Area business logic.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.audit_area_repository import AuditAreaRepository
from repositories.audit_template_repository import AuditTemplateRepository
from schemas.audit_area import AreaCreate, AreaDetailResponse, AreaResponse, AreaUpdate


def _scope_detail(scope) -> dict:
    questions = getattr(scope, "questions", []) or []
    total_pct = sum(q.percentage for q in questions)
    return {
        "id": scope.id,
        "area_id": scope.area_id,
        "name": scope.name,
        "questions": [
            {
                "id": q.id,
                "scope_id": q.scope_id,
                "text": q.text,
                "percentage": q.percentage,
                "is_mandatory": q.is_mandatory,
                "options": [
                    {
                        "id": o.id,
                        "question_id": o.question_id,
                        "label": o.label,
                        "value": o.value,
                        "created_at": o.created_at,
                        "updated_at": o.updated_at,
                    }
                    for o in (getattr(q, "options", []) or [])
                ],
                "created_at": q.created_at,
                "updated_at": q.updated_at,
            }
            for q in questions
        ],
        "total_percentage": total_pct,
        "created_at": scope.created_at,
        "updated_at": scope.updated_at,
    }


def _area_to_detail(area) -> AreaDetailResponse:
    scopes = getattr(area, "scopes", []) or []
    return AreaDetailResponse(
        id=area.id,
        template_id=area.template_id,
        name=area.name,
        weightage=area.weightage,
        scopes=[_scope_detail(s) for s in scopes],
        created_at=area.created_at,
        updated_at=area.updated_at,
    )


class AuditAreaService:
    """Business logic for audit areas within a template."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditAreaRepository(db)
        self.template_repo = AuditTemplateRepository(db)

    # ── List by template ─────────────────────────────────────────────────

    async def get_areas_by_template(self, template_id: UUID) -> list[AreaDetailResponse]:
        # Verify template exists
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        areas = await self.repo.get_by_template_id(template_id)
        return [_area_to_detail(a) for a in areas]

    # ── Get single area ──────────────────────────────────────────────────

    async def get_area(self, area_id: UUID) -> AreaDetailResponse:
        area = await self.repo.get_by_id(area_id)
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
        return _area_to_detail(area)

    # ── Create ────────────────────────────────────────────────────────────

    async def create_area(
        self, template_id: UUID, payload: AreaCreate, *, user_id: int | None = None
    ) -> AreaResponse:
        # Verify template exists
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

        area = await self.repo.create(
            template_id=template_id,
            name=payload.name,
            weightage=payload.weightage,
            created_by=user_id,
        )
        await self.db.commit()
        await self.db.refresh(area)
        return AreaResponse.model_validate(area)

    # ── Update ────────────────────────────────────────────────────────────

    async def update_area(
        self, area_id: UUID, payload: AreaUpdate, *, user_id: int | None = None
    ) -> AreaResponse:
        area = await self.repo.get_by_id(area_id)
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
        area = await self.repo.update(
            area,
            name=payload.name,
            weightage=payload.weightage,
            updated_by=user_id,
        )
        await self.db.commit()
        await self.db.refresh(area)
        return AreaResponse.model_validate(area)

    # ── Delete (soft) ─────────────────────────────────────────────────────

    async def delete_area(self, area_id: UUID, *, user_id: int | None = None) -> None:
        area = await self.repo.get_by_id(area_id)
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
        await self.repo.soft_delete(area, updated_by=user_id)
        await self.db.commit()
