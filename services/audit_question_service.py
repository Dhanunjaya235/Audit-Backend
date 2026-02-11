"""
Service layer for Audit Scope, Question, and Question Option business logic (US 3.3).
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.audit_area_repository import AuditAreaRepository
from repositories.audit_question_repository import (
    AuditQuestionOptionRepository,
    AuditQuestionRepository,
    AuditScopeRepository,
)
from schemas.audit_question import (
    OptionCreate,
    OptionResponse,
    OptionUpdate,
    QuestionCreate,
    QuestionDetailResponse,
    QuestionUpdate,
    ScopeCreate,
    ScopeDetailResponse,
    ScopeResponse,
    ScopeUpdate,
)


def _question_to_detail(question) -> QuestionDetailResponse:
    options = getattr(question, "options", []) or []
    return QuestionDetailResponse(
        id=question.id,
        scope_id=question.scope_id,
        text=question.text,
        percentage=question.percentage,
        is_mandatory=question.is_mandatory,
        options=[
            {
                "id": o.id,
                "question_id": o.question_id,
                "label": o.label,
                "value": o.value,
                "created_at": o.created_at,
                "updated_at": o.updated_at,
            }
            for o in options
        ],
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


def _scope_to_detail(scope) -> ScopeDetailResponse:
    questions = getattr(scope, "questions", []) or []
    total_pct = sum(q.percentage for q in questions)
    return ScopeDetailResponse(
        id=scope.id,
        area_id=scope.area_id,
        name=scope.name,
        questions=[_question_to_detail(q) for q in questions],
        total_percentage=total_pct,
        created_at=scope.created_at,
        updated_at=scope.updated_at,
    )


class AuditQuestionService:
    """Business logic for scopes, questions, and question options."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.scope_repo = AuditScopeRepository(db)
        self.question_repo = AuditQuestionRepository(db)
        self.option_repo = AuditQuestionOptionRepository(db)
        self.area_repo = AuditAreaRepository(db)

    # ═══════════════════════════════════════════════════════════════════════
    # SCOPES
    # ═══════════════════════════════════════════════════════════════════════

    async def get_scopes_by_area(self, area_id: UUID) -> list[ScopeDetailResponse]:
        area = await self.area_repo.get_by_id(area_id)
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
        scopes = await self.scope_repo.get_by_area_id(area_id)
        return [_scope_to_detail(s) for s in scopes]

    async def create_scope(
        self, area_id: UUID, payload: ScopeCreate, *, user_id: int | None = None
    ) -> ScopeResponse:
        area = await self.area_repo.get_by_id(area_id)
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
        scope = await self.scope_repo.create(area_id=area_id, name=payload.name, created_by=user_id)
        await self.db.commit()
        await self.db.refresh(scope)
        return ScopeResponse.model_validate(scope)

    async def update_scope(
        self, scope_id: UUID, payload: ScopeUpdate, *, user_id: int | None = None
    ) -> ScopeResponse:
        scope = await self.scope_repo.get_by_id(scope_id)
        if not scope:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found")
        scope = await self.scope_repo.update(scope, name=payload.name, updated_by=user_id)
        await self.db.commit()
        await self.db.refresh(scope)
        return ScopeResponse.model_validate(scope)

    async def delete_scope(self, scope_id: UUID, *, user_id: int | None = None) -> None:
        scope = await self.scope_repo.get_by_id(scope_id)
        if not scope:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found")
        await self.scope_repo.soft_delete(scope, updated_by=user_id)
        await self.db.commit()

    # ═══════════════════════════════════════════════════════════════════════
    # QUESTIONS
    # ═══════════════════════════════════════════════════════════════════════

    async def get_questions_by_scope(self, scope_id: UUID) -> list[QuestionDetailResponse]:
        scope = await self.scope_repo.get_by_id(scope_id)
        if not scope:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found")
        questions = await self.question_repo.get_by_scope_id(scope_id)
        return [_question_to_detail(q) for q in questions]

    async def create_question(
        self, scope_id: UUID, payload: QuestionCreate, *, user_id: int | None = None
    ) -> QuestionDetailResponse:
        scope = await self.scope_repo.get_by_id(scope_id)
        if not scope:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found")

        question = await self.question_repo.create(
            scope_id=scope_id,
            text=payload.text,
            percentage=payload.percentage,
            is_mandatory=payload.is_mandatory,
            created_by=user_id,
        )

        # If options are provided, create them in bulk
        if payload.options:
            await self.option_repo.bulk_create(
                question_id=question.id,
                options=[opt.model_dump() for opt in payload.options],
                created_by=user_id,
            )

        await self.db.commit()

        # Reload with options
        question = await self.question_repo.get_by_id(question.id)
        return _question_to_detail(question)

    async def update_question(
        self, question_id: UUID, payload: QuestionUpdate, *, user_id: int | None = None
    ) -> QuestionDetailResponse:
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        question = await self.question_repo.update(
            question,
            text=payload.text,
            percentage=payload.percentage,
            is_mandatory=payload.is_mandatory,
            updated_by=user_id,
        )
        await self.db.commit()
        question = await self.question_repo.get_by_id(question_id)
        return _question_to_detail(question)

    async def delete_question(self, question_id: UUID, *, user_id: int | None = None) -> None:
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        await self.question_repo.soft_delete(question, updated_by=user_id)
        await self.db.commit()

    # ═══════════════════════════════════════════════════════════════════════
    # QUESTION OPTIONS (Scoring Criteria)
    # ═══════════════════════════════════════════════════════════════════════

    async def get_options_by_question(self, question_id: UUID) -> list[OptionResponse]:
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        options = await self.option_repo.get_by_question_id(question_id)
        return [OptionResponse.model_validate(o) for o in options]

    async def create_option(
        self, question_id: UUID, payload: OptionCreate, *, user_id: int | None = None
    ) -> OptionResponse:
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        option = await self.option_repo.create(
            question_id=question_id,
            label=payload.label,
            value=payload.value,
            created_by=user_id,
        )
        await self.db.commit()
        await self.db.refresh(option)
        return OptionResponse.model_validate(option)

    async def update_option(
        self, option_id: UUID, payload: OptionUpdate, *, user_id: int | None = None
    ) -> OptionResponse:
        option = await self.option_repo.get_by_id(option_id)
        if not option:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
        option = await self.option_repo.update(
            option,
            label=payload.label,
            value=payload.value,
            updated_by=user_id,
        )
        await self.db.commit()
        await self.db.refresh(option)
        return OptionResponse.model_validate(option)

    async def delete_option(self, option_id: UUID, *, user_id: int | None = None) -> None:
        option = await self.option_repo.get_by_id(option_id)
        if not option:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
        await self.option_repo.soft_delete(option, updated_by=user_id)
        await self.db.commit()

    # ═══════════════════════════════════════════════════════════════════════
    # SCORE RECALCULATION (US 3.3)
    # ═══════════════════════════════════════════════════════════════════════

    async def recalculate_scope_scores(self, scope_id: UUID) -> ScopeDetailResponse:
        """
        Return the scope with recalculated total_percentage based on
        current question weightages. Useful after question add/edit/delete.
        """
        scope = await self.scope_repo.get_by_id(scope_id)
        if not scope:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found")
        return _scope_to_detail(scope)
