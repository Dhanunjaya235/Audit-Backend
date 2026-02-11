"""
Repository layer for AuditTemplate database operations.
All queries use SQLAlchemy 2.0 select() style with async sessions.
"""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.audit_models import (
    AuditArea,
    AuditQuestion,
    AuditQuestionOption,
    AuditScope,
    AuditTemplate,
)


class AuditTemplateRepository:
    """Data-access layer for audit templates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── List ──────────────────────────────────────────────────────────────

    async def get_all(self, *, include_inactive: bool = False) -> list[AuditTemplate]:
        """Return all templates with their areas eagerly loaded."""
        stmt = (
            select(AuditTemplate)
            .options(selectinload(AuditTemplate.areas.and_(AuditArea.isactive.is_(True))))
            .order_by(AuditTemplate.created_at.desc())
        )
        if not include_inactive:
            stmt = stmt.where(AuditTemplate.isactive.is_(True))
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    # ── Single (shallow) ─────────────────────────────────────────────────

    async def get_by_id(self, template_id: UUID) -> AuditTemplate | None:
        """Return a single template by ID (no nested eager load)."""
        stmt = (
            select(AuditTemplate)
            .options(selectinload(AuditTemplate.areas.and_(AuditArea.isactive.is_(True))))
            .where(and_(AuditTemplate.id == template_id, AuditTemplate.isactive.is_(True)))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Single (deep – areas → scopes → questions → options) ─────────────

    async def get_by_id_with_details(self, template_id: UUID) -> AuditTemplate | None:
        """
        Return a template with the full tree eagerly loaded:
        areas → scopes → questions → options.
        """
        stmt = (
            select(AuditTemplate)
            .options(
                selectinload(AuditTemplate.areas.and_(AuditArea.isactive.is_(True)))
                .selectinload(AuditArea.scopes.and_(AuditScope.isactive.is_(True)))
                .selectinload(AuditScope.questions.and_(AuditQuestion.isactive.is_(True)))
                .selectinload(AuditQuestion.options.and_(AuditQuestionOption.isactive.is_(True))),
            )
            .where(AuditTemplate.id == template_id)
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Lookup by name ───────────────────────────────────────────────────

    async def get_by_name(self, name: str) -> AuditTemplate | None:
        stmt = select(AuditTemplate).where(
            and_(AuditTemplate.name == name, AuditTemplate.isactive.is_(True))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create ────────────────────────────────────────────────────────────

    async def create(self, *, name: str, created_by: int | None = None) -> AuditTemplate:
        template = AuditTemplate(
            name=name, isactive=True, created_by=created_by, updated_by=created_by
        )
        self.db.add(template)
        await self.db.flush()
        return template

    # ── Update ────────────────────────────────────────────────────────────

    async def update(
        self,
        template: AuditTemplate,
        *,
        name: str | None = None,
        isactive: bool | None = None,
        updated_by: int | None = None,
    ) -> AuditTemplate:
        if name is not None:
            template.name = name
        if isactive is not None:
            template.isactive = isactive
        if updated_by is not None:
            template.updated_by = updated_by
        await self.db.flush()
        return template

    # ── Soft delete ───────────────────────────────────────────────────────

    async def soft_delete(self, template: AuditTemplate, *, updated_by: int | None = None) -> None:
        template.isactive = False
        if updated_by is not None:
            template.updated_by = updated_by
        await self.db.flush()

    # ── Create full tree from payload ──────────────────────────────────────

    async def create_with_tree(
        self,
        *,
        name: str,
        areas: list[dict],
        created_by: int | None = None,
    ) -> AuditTemplate:
        """
        Create a template with full tree: areas → scopes → questions → options.
        `areas` is a list of dicts from the validated Pydantic schema.
        All inserts are batched; commit is left to the caller.
        """
        # 1 ── Template
        new_template = AuditTemplate(
            name=name,
            isactive=True,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(new_template)
        await self.db.flush()

        # 2 ── Areas
        area_objects: list[tuple[dict, AuditArea]] = []
        for area_data in areas:
            area_obj = AuditArea(
                template_id=new_template.id,
                name=area_data["name"],
                weightage=area_data["weightage"],
                isactive=True,
                created_by=created_by,
                updated_by=created_by,
            )
            self.db.add(area_obj)
            area_objects.append((area_data, area_obj))

        await self.db.flush()

        # 3 ── Scopes
        scope_objects: list[tuple[dict, AuditScope]] = []
        for area_data, area_obj in area_objects:
            for scope_data in area_data.get("scopes", []):
                scope_obj = AuditScope(
                    area_id=area_obj.id,
                    name=scope_data["name"],
                    isactive=True,
                    created_by=created_by,
                    updated_by=created_by,
                )
                self.db.add(scope_obj)
                scope_objects.append((scope_data, scope_obj))

        await self.db.flush()

        # 4 ── Questions
        question_objects: list[tuple[dict, AuditQuestion]] = []
        for scope_data, scope_obj in scope_objects:
            for q_data in scope_data.get("questions", []):
                q_obj = AuditQuestion(
                    scope_id=scope_obj.id,
                    text=q_data["text"],
                    percentage=q_data["percentage"],
                    is_mandatory=q_data.get("is_mandatory", True),
                    isactive=True,
                    created_by=created_by,
                    updated_by=created_by,
                )
                self.db.add(q_obj)
                question_objects.append((q_data, q_obj))

        await self.db.flush()

        # 5 ── Options
        for q_data, q_obj in question_objects:
            for opt in q_data.get("options", []) or []:
                opt_obj = AuditQuestionOption(
                    question_id=q_obj.id,
                    label=opt["label"],
                    value=opt["value"],
                    isactive=True,
                    created_by=created_by,
                    updated_by=created_by,
                )
                self.db.add(opt_obj)

        await self.db.flush()
        return new_template
