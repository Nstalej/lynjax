from fastapi import APIRouter

from app.core.config import settings
from app.schemas.assessments import InfoResponse

router = APIRouter(prefix="/api/v1")


@router.get("/info", response_model=InfoResponse)
def info() -> InfoResponse:
    return InfoResponse(
        name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        network_policy=settings.network_policy,
    )
