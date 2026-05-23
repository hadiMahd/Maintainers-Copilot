"""API router registry."""

from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.memory import router as memory_router
from app.api.routes.memory_inspector import router as memory_inspector_router
from app.api.routes.users import router as users_router
from app.api.routes.widget_configs import router as widget_configs_router
from app.api.routes.widget_loader import loader_alias_router
from app.api.routes.widget_loader import router as widget_loader_router
from app.api.routes.widget_public import router as widget_public_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health")
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(users_router)
api_router.include_router(admin_router, prefix="/admin")
api_router.include_router(memory_router, prefix="/memory")
# memory_inspector shares the /memory prefix; memory.py owns POST endpoints,
# memory_inspector.py owns GET /long-term (inspection listing)
api_router.include_router(memory_inspector_router, prefix="/memory")
api_router.include_router(chat_router)
api_router.include_router(widget_configs_router, prefix="/admin/widget-configs")
api_router.include_router(widget_loader_router)
api_router.include_router(loader_alias_router)
api_router.include_router(widget_public_router)
