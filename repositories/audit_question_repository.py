"""
Repository layer for AuditScope, AuditQuestion, and AuditQuestionOption.
"""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.audit_models import AuditQuestion, AuditQuestionOption, AuditScope


class AuditScopeRepository:
    """Data-access layer for audit scopes."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_area_id(self, area_id: UUID) -> list[AuditScope]:
        stmt = (
            select(AuditScope)
            .options(
                selectinload(
                    AuditScope.questions.and_(AuditQuestion.isactive.is_(True))
                ).selectinload(AuditQuestion.options.and_(AuditQuestionOption.isactive.is_(True))),
            )
            .where(and_(AuditScope.area_id == area_id, AuditScope.isactive.is_(True)))
            .order_by(AuditScope.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_id(self, scope_id: UUID) -> AuditScope | None:
        stmt = (
            select(AuditScope)
            .options(
                selectinload(
                    AuditScope.questions.and_(AuditQuestion.isactive.is_(True))
                ).selectinload(AuditQuestion.options.and_(AuditQuestionOption.isactive.is_(True))),
            )
            .where(and_(AuditScope.id == scope_id, AuditScope.isactive.is_(True)))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        area_id: UUID,
        name: str,
        created_by: int | None = None,
    ) -> AuditScope:
        scope = AuditScope(
            area_id=area_id,
            name=name,
            isactive=True,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(scope)
        await self.db.flush()
        return scope

    async def update(
        self,
        scope: AuditScope,
        *,
        name: str | None = None,
        updated_by: int | None = None,
    ) -> AuditScope:
        if name is not None:
            scope.name = name
        if updated_by is not None:
            scope.updated_by = updated_by
        await self.db.flush()
        return scope

    async def soft_delete(self, scope: AuditScope, *, updated_by: int | None = None) -> None:
        scope.isactive = False
        if updated_by is not None:
            scope.updated_by = updated_by
        await self.db.flush()


class AuditQuestionRepository:
    """Data-access layer for audit questions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_scope_id(self, scope_id: UUID) -> list[AuditQuestion]:
        stmt = (
            select(AuditQuestion)
            .options(
                selectinload(AuditQuestion.options.and_(AuditQuestionOption.isactive.is_(True)))
            )
            .where(and_(AuditQuestion.scope_id == scope_id, AuditQuestion.isactive.is_(True)))
            .order_by(AuditQuestion.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_id(self, question_id: UUID) -> AuditQuestion | None:
        stmt = (
            select(AuditQuestion)
            .options(
                selectinload(AuditQuestion.options.and_(AuditQuestionOption.isactive.is_(True)))
            )
            .where(and_(AuditQuestion.id == question_id, AuditQuestion.isactive.is_(True)))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        scope_id: UUID,
        text: str,
        percentage: int,
        is_mandatory: bool = True,
        created_by: int | None = None,
    ) -> AuditQuestion:
        question = AuditQuestion(
            scope_id=scope_id,
            text=text,
            percentage=percentage,
            is_mandatory=is_mandatory,
            isactive=True,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(question)
        await self.db.flush()
        return question

    async def update(
        self,
        question: AuditQuestion,
        *,
        text: str | None = None,
        percentage: int | None = None,
        is_mandatory: bool | None = None,
        updated_by: int | None = None,
    ) -> AuditQuestion:
        if text is not None:
            question.text = text
        if percentage is not None:
            question.percentage = percentage
        if is_mandatory is not None:
            question.is_mandatory = is_mandatory
        if updated_by is not None:
            question.updated_by = updated_by
        await self.db.flush()
        return question

    async def soft_delete(self, question: AuditQuestion, *, updated_by: int | None = None) -> None:
        question.isactive = False
        if updated_by is not None:
            question.updated_by = updated_by
        await self.db.flush()


class AuditQuestionOptionRepository:
    """Data-access layer for audit question options (scoring criteria)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_question_id(self, question_id: UUID) -> list[AuditQuestionOption]:
        stmt = (
            select(AuditQuestionOption)
            .where(
                and_(
                    AuditQuestionOption.question_id == question_id,
                    AuditQuestionOption.isactive.is_(True),
                )
            )
            .order_by(AuditQuestionOption.value.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, option_id: UUID) -> AuditQuestionOption | None:
        stmt = select(AuditQuestionOption).where(
            and_(AuditQuestionOption.id == option_id, AuditQuestionOption.isactive.is_(True))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        question_id: UUID,
        label: str,
        value: int,
        created_by: int | None = None,
    ) -> AuditQuestionOption:
        option = AuditQuestionOption(
            question_id=question_id,
            label=label,
            value=value,
            isactive=True,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(option)
        await self.db.flush()
        return option

    async def bulk_create(
        self,
        *,
        question_id: UUID,
        options: list[dict],
        created_by: int | None = None,
    ) -> list[AuditQuestionOption]:
        """Create multiple options in a single flush (no commits inside loops)."""
        entities = []
        for opt in options:
            entity = AuditQuestionOption(
                question_id=question_id,
                label=opt["label"],
                value=opt["value"],
                isactive=True,
                created_by=created_by,
                updated_by=created_by,
            )
            self.db.add(entity)
            entities.append(entity)
        await self.db.flush()
        return entities

    async def update(
        self,
        option: AuditQuestionOption,
        *,
        label: str | None = None,
        value: int | None = None,
        updated_by: int | None = None,
    ) -> AuditQuestionOption:
        if label is not None:
            option.label = label
        if value is not None:
            option.value = value
        if updated_by is not None:
            option.updated_by = updated_by
        await self.db.flush()
        return option

    async def soft_delete(
        self, option: AuditQuestionOption, *, updated_by: int | None = None
    ) -> None:
        option.isactive = False
        if updated_by is not None:
            option.updated_by = updated_by
        await self.db.flush()
