"""API v1 router — includes all protected sub-routers."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_current_user
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.pets import (
    protected_router as protected_pets_router,
    unprotected_router as unprotected_pets_router,
)
from app.api.v1.store import router as store_router
from app.api.v1.users import (
    protected_router as protected_users_router,
    unprotected_router as unprotected_users_router,
)

PROTECTED_ROUTE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "****** missing, invalid, or expired."},
    403: {"description": "Authenticated user does not have access to this resource."},
}


router = APIRouter(prefix="/api/v1")

router.include_router(health_router)
router.include_router(
    protected_pets_router,
    dependencies=[Depends(require_current_user)],
    responses=PROTECTED_ROUTE_RESPONSES,
)
router.include_router(unprotected_pets_router)
router.include_router(
    store_router,
    dependencies=[Depends(require_current_user)],
    responses=PROTECTED_ROUTE_RESPONSES,
)
router.include_router(auth_router, dependencies=[], responses={})
router.include_router(unprotected_users_router, dependencies=[], responses={})
router.include_router(
    protected_users_router,
    dependencies=[Depends(require_current_user)],
    responses=PROTECTED_ROUTE_RESPONSES,
)
