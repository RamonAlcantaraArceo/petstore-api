"""API v1 router — includes all sub-routers."""

from fastapi import APIRouter, Depends
from fastapi.security import APIKeyHeader

from app.api.v1.pets import router as pets_router
from app.api.v1.store import router as store_router
from app.api.v1.users import router as users_router

api_key_scheme = APIKeyHeader(
    name="X-API-Key", description="API key required to access protected endpoints."
)


def require_api_key(_: str = Depends(api_key_scheme)) -> None:
    """Dependency to declare the X-API-Key header for OpenAPI/Swagger.

    Args:
        _ (str): Value of the X-API-Key header, injected by FastAPI's APIKeyHeader dependency.

    Returns:
        None
    """
    pass

router = APIRouter(prefix="/api/v1")

router.include_router(pets_router, dependencies=[Depends(require_api_key)])
router.include_router(store_router, dependencies=[Depends(require_api_key)])
router.include_router(users_router, dependencies=[Depends(require_api_key)])
