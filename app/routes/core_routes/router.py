from fastapi import APIRouter

from app.routes.core_routes.chat_route import router as chat_router

router = APIRouter()
router.include_router(chat_router)
