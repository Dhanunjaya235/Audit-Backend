"""
Repository layer for AuditArea database operations.
"""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.audit_models import AuditArea, AuditQuestion, AuditQuestionOption, AuditScope


class AuditAreaRepository:
    """Data-access layer for audit areas."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── List by template ─────────────────────────────────────────────────

    async def get_by_template_id(self, template_id: UUID) -> list[AuditArea]:
        stmt = (
            select(AuditArea)
            .options(
                selectinload(AuditArea.scopes.and_(AuditScope.isactive.is_(True)))
                .selectinload(AuditScope.questions.and_(AuditQuestion.isactive.is_(True)))
                .selectinload(AuditQuestion.options.and_(AuditQuestionOption.isactive.is_(True))),
            )
            .where(and_(AuditArea.template_id == template_id, AuditArea.isactive.is_(True)))
            .order_by(AuditArea.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    # ── Single ────────────────────────────────────────────────────────────

    async def get_by_id(self, area_id: UUID) -> AuditArea | None:
        stmt = (
            select(AuditArea)
            .options(
                selectinload(AuditArea.scopes.and_(AuditScope.isactive.is_(True)))
                .selectinload(AuditScope.questions.and_(AuditQuestion.isactive.is_(True)))
                .selectinload(AuditQuestion.options.and_(AuditQuestionOption.isactive.is_(True))),
            )
            .where(and_(AuditArea.id == area_id, AuditArea.isactive.is_(True)))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create ────────────────────────────────────────────────────────────

    async def create(
        self,
        *,
        template_id: UUID,
        name: str,
        weightage: int,
        created_by: int | None = None,
    ) -> AuditArea:
        area = AuditArea(
            template_id=template_id,
            name=name,
            weightage=weightage,
            isactive=True,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(area)
        await self.db.flush()
        return area

    # ── Update ────────────────────────────────────────────────────────────

    async def update(
        self,
        area: AuditArea,
        *,
        name: str | None = None,
        weightage: int | None = None,
        updated_by: int | None = None,
    ) -> AuditArea:
        if name is not None:
            area.name = name
        if weightage is not None:
            area.weightage = weightage
        if updated_by is not None:
            area.updated_by = updated_by
        await self.db.flush()
        return area

    # ── Soft Delete ────────────────────────────────────────────────────────

    async def soft_delete(self, area: AuditArea, *, updated_by: int | None = None) -> None:
        area.isactive = False
        if updated_by is not None:
            area.updated_by = updated_by
        await self.db.flush()
