"""API router registry."""

from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.memory import router as memory_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health")
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(users_router)
api_router.include_router(admin_router, prefix="/admin")
api_router.include_router(memory_router, prefix="/memory")
api_router.include_router(chat_router)
