"""
Service layer for Audit Template business logic.
Handles default template seeding, cloning, and CRUD orchestration.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_models import AuditArea, AuditQuestion, AuditQuestionOption, AuditScope
from repositories.audit_template_repository import AuditTemplateRepository
from schemas.audit_template import (
    TemplateCloneRequest,
    TemplateCreate,
    TemplateDetailResponse,
    TemplateResponse,
    TemplateUpdate,
)

# Default audit areas per US 3.1
DEFAULT_TEMPLATE_NAME = "Default Audit Template"
DEFAULT_AREAS: list[dict[str, int | str]] = [
    {"name": "Project Execution", "weightage": 20},
    {"name": "Engineering Excellence", "weightage": 20},
    {"name": "Communication", "weightage": 20},
    {"name": "People Management", "weightage": 20},
    {"name": "Learning & Innovation", "weightage": 20},
]


def _compute_total_weightage(areas: list) -> int:
    """Sum weightage from eagerly loaded area objects."""
    return sum(getattr(a, "weightage", 0) for a in areas)


def _template_to_response(template) -> TemplateResponse:
    areas = getattr(template, "areas", []) or []
    resp = TemplateResponse.model_validate(template)
    resp.total_weightage = _compute_total_weightage(areas)
    return resp


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


def _template_to_detail_response(template) -> TemplateDetailResponse:
    areas = getattr(template, "areas", []) or []
    area_details = []
    for area in areas:
        scopes = getattr(area, "scopes", []) or []
        area_details.append(
            {
                "id": area.id,
                "template_id": area.template_id,
                "name": area.name,
                "weightage": area.weightage,
                "scopes": [_scope_detail(s) for s in scopes],
                "created_at": area.created_at,
                "updated_at": area.updated_at,
            }
        )
    return TemplateDetailResponse(
        id=template.id,
        name=template.name,
        isactive=template.isactive,
        areas=area_details,
        total_weightage=_compute_total_weightage(areas),
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


class AuditTemplateService:
    """Business logic for audit templates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditTemplateRepository(db)

    # ── Percentage Validation ─────────────────────────────────────────────

    @staticmethod
    def _validate_scope_percentages(areas: list[dict]) -> None:
        """
        For every template, the sum of question
        percentages MUST equal exactly 100.  Raises 422 on failure.
        """
        total = 0
        for area in areas:
            for scope in area.get("scopes", []):
                questions = scope.get("questions", [])
                if not questions:
                    continue
                total += sum(q.get("percentage", 0) for q in questions)
        if total != 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Total weightage of all questions should be exactly 100%",
            )

    @staticmethod
    def _validate_area_names(areas: list[dict]) -> None:
        """Area names must be unique within the template (case-insensitive)."""
        seen: set[str] = set()
        for area in areas:
            key = area["name"].strip().lower()
            if key in seen:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Duplicate area name: '{area['name']}'",
                )
            seen.add(key)

    @staticmethod
    def _validate_scope_names(areas: list[dict]) -> None:
        """Scope names must be unique within each area (case-insensitive)."""
        for area in areas:
            seen: set[str] = set()
            for scope in area.get("scopes", []):
                key = scope["name"].strip().lower()
                if key in seen:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Duplicate scope name '{scope['name']}' in area '{area['name']}'",
                    )
                seen.add(key)

    @staticmethod
    def _validate_question_names(areas: list[dict]) -> None:
        """Question texts must be unique within each scope (case-insensitive)."""
        for area in areas:
            for scope in area.get("scopes", []):
                seen: set[str] = set()
                for q in scope.get("questions", []):
                    key = q["text"].strip().lower()
                    if key in seen:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=(
                                f"Duplicate question text '{q['text']}' "
                                f"in scope '{scope['name']}', area '{area['name']}'"
                            ),
                        )
                    seen.add(key)

    @staticmethod
    def _validate_option_labels(areas: list[dict]) -> None:
        """Option labels must be unique within each question (case-insensitive)."""
        for area in areas:
            for scope in area.get("scopes", []):
                for q in scope.get("questions", []):
                    seen: set[str] = set()
                    for opt in q.get("options", []) or []:
                        key = opt["label"].strip().lower()
                        if key in seen:
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=(
                                    f"Duplicate option label '{opt['label']}' "
                                    f"in question '{q['text']}', scope '{scope['name']}'"
                                ),
                            )
                        seen.add(key)

    @staticmethod
    def _validate_option_values(areas: list[dict]) -> None:
        """Option values must be unique within each question."""
        for area in areas:
            for scope in area.get("scopes", []):
                for q in scope.get("questions", []):
                    seen: set[int] = set()
                    for opt in q.get("options", []) or []:
                        val = opt["value"]
                        if val in seen:
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=(
                                    f"Duplicate option value {val} "
                                    f"in question '{q['text']}', scope '{scope['name']}'"
                                ),
                            )
                        seen.add(val)

    @staticmethod
    def _validate_empty_question_scopes_areas(areas: list[dict]) -> None:
        """
        Validate that:
        - Every area has at least one scope
        - Every scope has at least one question
        - Every question has at least one option
        """
        for area in areas:
            scopes = area.get("scopes", [])
            if not scopes:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Area '{area['name']}' must have at least one scope",
                )
            for scope in scopes:
                questions = scope.get("questions", [])
                if not questions:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Scope '{scope['name']}' in area '{area['name']}' "
                            f"must have at least one question"
                        ),
                    )
                for q in questions:
                    options = q.get("options", []) or []
                    if not options:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=(
                                f"Question '{q['text']}' in scope '{scope['name']}', "
                                f"area '{area['name']}' must have at least one option"
                            ),
                        )

    # ── List ──────────────────────────────────────────────────────────────

    async def get_all_templates(self, *, include_inactive: bool = False) -> list[TemplateResponse]:
        templates = await self.repo.get_all(include_inactive=include_inactive)
        return [_template_to_response(t) for t in templates]

    # ── Detail ────────────────────────────────────────────────────────────

    async def get_template_detail(self, template_id: UUID) -> TemplateDetailResponse:
        template = await self.repo.get_by_id_with_details(template_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        return _template_to_detail_response(template)

    # ── Create (full tree) ────────────────────────────────────────────────

    async def create_template(
        self, payload: TemplateCreate, *, user_id: int | None = None
    ) -> TemplateDetailResponse:
        """
        Create a template with areas → scopes → questions → options
        in a single atomic transaction.
        """
        # Name uniqueness
        existing = await self.repo.get_by_name(payload.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Template with name '{payload.name}' already exists",
            )

        # Validate all constraints
        areas_data = [a.model_dump() for a in payload.areas]
        self._validate_empty_question_scopes_areas(areas_data)
        self._validate_area_names(areas_data)
        self._validate_scope_names(areas_data)
        self._validate_question_names(areas_data)
        self._validate_option_labels(areas_data)
        self._validate_option_values(areas_data)
        self._validate_scope_percentages(areas_data)

        # Atomic tree creation
        template = await self.repo.create_with_tree(
            name=payload.name,
            areas=areas_data,
            created_by=user_id,
        )
        await self.db.commit()

        # Reload full detail
        detail = await self.repo.get_by_id_with_details(template.id)
        return _template_to_detail_response(detail)

    # ── Update (ID-based merge) ─────────────────────────────────────────────

    async def update_template(
        self, template_id: UUID, payload: TemplateUpdate, *, user_id: int | None = None
    ) -> TemplateDetailResponse:
        """
        Update a template with ID-based merging at every level:
        - Items WITH id  → update existing record in place
        - Items WITHOUT id → create new record
        - Existing items NOT in payload → soft-deleted
        """
        # Load full tree
        template = await self.repo.get_by_id_with_details(template_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

        # Name uniqueness (allow keeping the same name)
        if payload.name != template.name:
            existing = await self.repo.get_by_name(payload.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Template with name '{payload.name}' already exists",
                )

        # Validate all constraints
        areas_data = [a.model_dump() for a in payload.areas]
        self._validate_empty_question_scopes_areas(areas_data)
        self._validate_area_names(areas_data)
        self._validate_scope_names(areas_data)
        self._validate_question_names(areas_data)
        self._validate_option_labels(areas_data)
        self._validate_option_values(areas_data)
        self._validate_scope_percentages(areas_data)

        # Update template name
        template.name = payload.name
        if user_id is not None:
            template.updated_by = user_id

        # ── AREAS: merge ──────────────────────────────────────────────
        existing_areas = {a.id: a for a in (template.areas or [])}
        payload_area_ids = {a.id for a in payload.areas if a.id}

        # Soft-delete areas not in payload
        for area_id, area_obj in existing_areas.items():
            if area_id not in payload_area_ids:
                area_obj.isactive = False
                if user_id is not None:
                    area_obj.updated_by = user_id
                # Also soft-delete all children of removed area
                for scope in getattr(area_obj, "scopes", []) or []:
                    scope.isactive = False
                    if user_id is not None:
                        scope.updated_by = user_id
                    for q in getattr(scope, "questions", []) or []:
                        q.isactive = False
                        if user_id is not None:
                            q.updated_by = user_id
                        for o in getattr(q, "options", []) or []:
                            o.isactive = False
                            if user_id is not None:
                                o.updated_by = user_id

        # Process each area in payload
        for area_payload in payload.areas:
            if area_payload.id and area_payload.id in existing_areas:
                # UPDATE existing area
                area_obj = existing_areas[area_payload.id]
                area_obj.name = area_payload.name
                area_obj.weightage = area_payload.weightage
                if user_id is not None:
                    area_obj.updated_by = user_id
            else:
                # CREATE new area
                area_obj = AuditArea(
                    template_id=template_id,
                    name=area_payload.name,
                    weightage=area_payload.weightage,
                    isactive=True,
                    created_by=user_id,
                    updated_by=user_id,
                )
                self.db.add(area_obj)
                await self.db.flush()

            # ── SCOPES: merge within this area ────────────────────────
            if area_payload.id and area_payload.id in existing_areas:
                existing_scopes = {s.id: s for s in (getattr(area_obj, "scopes", []) or [])}
            else:
                existing_scopes = {}

            payload_scope_ids = {s.id for s in area_payload.scopes if s.id}

            # Soft-delete scopes not in payload
            for scope_id, scope_obj in existing_scopes.items():
                if scope_id not in payload_scope_ids:
                    scope_obj.isactive = False
                    if user_id is not None:
                        scope_obj.updated_by = user_id
                    for q in getattr(scope_obj, "questions", []) or []:
                        q.isactive = False
                        if user_id is not None:
                            q.updated_by = user_id
                        for o in getattr(q, "options", []) or []:
                            o.isactive = False
                            if user_id is not None:
                                o.updated_by = user_id

            for scope_payload in area_payload.scopes:
                if scope_payload.id and scope_payload.id in existing_scopes:
                    scope_obj = existing_scopes[scope_payload.id]
                    scope_obj.name = scope_payload.name
                    if user_id is not None:
                        scope_obj.updated_by = user_id

                    # Load existing questions for existing scope
                    existing_questions = {
                        q.id: q for q in (getattr(scope_obj, "questions", []) or [])
                    }
                else:
                    scope_obj = AuditScope(
                        area_id=area_obj.id,
                        name=scope_payload.name,
                        isactive=True,
                        created_by=user_id,
                        updated_by=user_id,
                    )
                    self.db.add(scope_obj)
                    await self.db.flush()

                    # New scope: no existing questions
                    existing_questions = {}

                # ── QUESTIONS: merge within this scope ────────────────
                payload_q_ids = {q.id for q in scope_payload.questions if q.id}

                # Soft-delete questions not in payload
                for q_id, q_obj in existing_questions.items():
                    if q_id not in payload_q_ids:
                        q_obj.isactive = False
                        if user_id is not None:
                            q_obj.updated_by = user_id
                        for o in getattr(q_obj, "options", []) or []:
                            o.isactive = False
                            if user_id is not None:
                                o.updated_by = user_id

                for q_payload in scope_payload.questions:
                    if q_payload.id and q_payload.id in existing_questions:
                        q_obj = existing_questions[q_payload.id]
                        q_obj.text = q_payload.text
                        q_obj.percentage = q_payload.percentage
                        q_obj.is_mandatory = q_payload.is_mandatory
                        if user_id is not None:
                            q_obj.updated_by = user_id

                        # Existing question: options should be loaded
                        existing_options = {o.id: o for o in (getattr(q_obj, "options", []) or [])}
                    else:
                        q_obj = AuditQuestion(
                            scope_id=scope_obj.id,
                            text=q_payload.text,
                            percentage=q_payload.percentage,
                            is_mandatory=q_payload.is_mandatory,
                            isactive=True,
                            created_by=user_id,
                            updated_by=user_id,
                        )
                        self.db.add(q_obj)
                        await self.db.flush()

                        # New question: definitely no existing options
                        existing_options = {}

                    # ── OPTIONS: merge within this question ───────────
                    payload_o_ids = {o.id for o in q_payload.options if o.id}

                    # Soft-delete options not in payload
                    for o_id, o_obj in existing_options.items():
                        if o_id not in payload_o_ids:
                            o_obj.isactive = False
                            if user_id is not None:
                                o_obj.updated_by = user_id

                    for o_payload in q_payload.options:
                        if o_payload.id and o_payload.id in existing_options:
                            o_obj = existing_options[o_payload.id]
                            o_obj.label = o_payload.label
                            o_obj.value = o_payload.value
                            if user_id is not None:
                                o_obj.updated_by = user_id
                        else:
                            o_obj = AuditQuestionOption(
                                question_id=q_obj.id,
                                label=o_payload.label,
                                value=o_payload.value,
                                isactive=True,
                                created_by=user_id,
                                updated_by=user_id,
                            )
                            self.db.add(o_obj)

        await self.db.commit()

        detail = await self.repo.get_by_id_with_details(template_id)
        return _template_to_detail_response(detail)

    # ── Delete (soft) ─────────────────────────────────────────────────────

    async def delete_template(self, template_id: UUID, *, user_id: int | None = None) -> None:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
        await self.repo.soft_delete(template, updated_by=user_id)
        await self.db.commit()

    # ── Seed default template (US 3.1) ────────────────────────────────────

    async def seed_default_template(self, *, user_id: int | None = None) -> TemplateDetailResponse:
        """
        Create the default template with the five standard audit areas
        if it does not already exist. If it does, return the existing one.
        """
        existing = await self.repo.get_by_name(DEFAULT_TEMPLATE_NAME)
        if existing:
            detail = await self.repo.get_by_id_with_details(existing.id)
            return _template_to_detail_response(detail)

        template = await self.repo.create_with_tree(
            name=DEFAULT_TEMPLATE_NAME,
            areas=DEFAULT_AREAS,
            created_by=user_id,
        )
        await self.db.commit()

        detail = await self.repo.get_by_id_with_details(template.id)
        return _template_to_detail_response(detail)

    # ── Clone template (US 3.2) ──────────────────────────────────────────

    async def clone_template(
        self,
        template_id: UUID,
        payload: TemplateCloneRequest,
        *,
        user_id: int | None = None,
    ) -> TemplateDetailResponse:
        """
        Create a completely new template from (possibly modified) data.
        The source template_id is validated to exist but the new template
        is built entirely from the payload — not a DB-level copy.
        """
        # Verify source exists
        source = await self.repo.get_by_id(template_id)
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source template not found",
            )

        # Name uniqueness
        existing = await self.repo.get_by_name(payload.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Template with name '{payload.name}' already exists",
            )

        # Validate all constraints
        areas_data = [a.model_dump() for a in payload.areas]
        self._validate_empty_question_scopes_areas(areas_data)
        self._validate_area_names(areas_data)
        self._validate_scope_names(areas_data)
        self._validate_question_names(areas_data)
        self._validate_option_labels(areas_data)
        self._validate_option_values(areas_data)
        self._validate_scope_percentages(areas_data)

        # Atomic tree creation
        new_template = await self.repo.create_with_tree(
            name=payload.name,
            areas=areas_data,
            created_by=user_id,
        )
        await self.db.commit()

        detail = await self.repo.get_by_id_with_details(new_template.id)
        return _template_to_detail_response(detail)
