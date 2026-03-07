"""API v1 router — includes all sub-routers."""

from fastapi import APIRouter

from app.api.v1.pets import router as pets_router
from app.api.v1.store import router as store_router
from app.api.v1.users import router as users_router

router = APIRouter(prefix="/api/v1")

router.include_router(pets_router)
router.include_router(store_router)
router.include_router(users_router)
