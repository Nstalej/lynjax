from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.assessments import InfoResponse

router = APIRouter(prefix="/api/v1")


@router.get("/info", response_model=InfoResponse)
def info(settings: Annotated[Settings, Depends(get_settings)]) -> InfoResponse:
    return InfoResponse(
        name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        network_policy=settings.network_policy,
    )
