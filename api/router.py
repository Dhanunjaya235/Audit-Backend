"""
Central API router that aggregates all sub-routers under /api/v1.
"""

from fastapi import APIRouter

from routers.audit_area_router import router as area_router
from routers.audit_question_router import router as question_router
from routers.audit_template_router import router as template_router

api_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_router.include_router(template_router)
api_router.include_router(area_router)
api_router.include_router(question_router)
