"""
Router for Audit Scope, Question, and Question Option endpoints (US 3.3).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.auth import token_required
from database.async_db import get_db
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
from services.audit_question_service import AuditQuestionService

router = APIRouter(tags=["Audit Questions"])


def _get_service(db: AsyncSession = Depends(get_db)) -> AuditQuestionService:
    return AuditQuestionService(db)


# ═══════════════════════════════════════════════════════════════════════════
# SCOPE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/areas/{area_id}/scopes",
    response_model=list[ScopeDetailResponse],
    summary="List all scopes for an area",
)
async def list_scopes(
    area_id: UUID,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.get_scopes_by_area(area_id)


@router.post(
    "/areas/{area_id}/scopes",
    response_model=ScopeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new scope to an area",
)
async def create_scope(
    area_id: UUID,
    payload: ScopeCreate,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.create_scope(area_id, payload, user_id=current_user.get("user_id"))


@router.put(
    "/scopes/{scope_id}",
    response_model=ScopeResponse,
    summary="Update a scope",
)
async def update_scope(
    scope_id: UUID,
    payload: ScopeUpdate,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.update_scope(scope_id, payload, user_id=current_user.get("user_id"))


@router.delete(
    "/scopes/{scope_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a scope and its questions",
)
async def delete_scope(
    scope_id: UUID,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    await service.delete_scope(scope_id, user_id=current_user.get("user_id"))


# ═══════════════════════════════════════════════════════════════════════════
# QUESTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/scopes/{scope_id}/questions",
    response_model=list[QuestionDetailResponse],
    summary="List all questions for a scope",
)
async def list_questions(
    scope_id: UUID,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.get_questions_by_scope(scope_id)


@router.post(
    "/scopes/{scope_id}/questions",
    response_model=QuestionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new question to a scope (optionally with scoring options)",
)
async def create_question(
    scope_id: UUID,
    payload: QuestionCreate,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.create_question(scope_id, payload, user_id=current_user.get("user_id"))


@router.put(
    "/questions/{question_id}",
    response_model=QuestionDetailResponse,
    summary="Update a question",
)
async def update_question(
    question_id: UUID,
    payload: QuestionUpdate,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.update_question(question_id, payload, user_id=current_user.get("user_id"))


@router.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a question and its options",
)
async def delete_question(
    question_id: UUID,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    await service.delete_question(question_id, user_id=current_user.get("user_id"))


# ═══════════════════════════════════════════════════════════════════════════
# QUESTION OPTION (SCORING CRITERIA) ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/questions/{question_id}/options",
    response_model=list[OptionResponse],
    summary="List all scoring options for a question",
)
async def list_options(
    question_id: UUID,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.get_options_by_question(question_id)


@router.post(
    "/questions/{question_id}/options",
    response_model=OptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a scoring option to a question",
)
async def create_option(
    question_id: UUID,
    payload: OptionCreate,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.create_option(question_id, payload, user_id=current_user.get("user_id"))


@router.put(
    "/options/{option_id}",
    response_model=OptionResponse,
    summary="Update a scoring option",
)
async def update_option(
    option_id: UUID,
    payload: OptionUpdate,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.update_option(option_id, payload, user_id=current_user.get("user_id"))


@router.delete(
    "/options/{option_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a scoring option",
)
async def delete_option(
    option_id: UUID,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    await service.delete_option(option_id, user_id=current_user.get("user_id"))


# ═══════════════════════════════════════════════════════════════════════════
# RECALCULATION ENDPOINT (US 3.3)
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/scopes/{scope_id}/recalculate",
    response_model=ScopeDetailResponse,
    summary="Recalculate scores for a scope after criteria changes",
)
async def recalculate_scope(
    scope_id: UUID,
    service: AuditQuestionService = Depends(_get_service),
    current_user: Annotated[dict, Depends(token_required)] = None,
):
    return await service.recalculate_scope_scores(scope_id)
