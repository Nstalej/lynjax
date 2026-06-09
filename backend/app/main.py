from fastapi import FastAPI

from app.api.routes.assessments import router as assessments_router
from app.api.routes.health import router as health_router
from app.api.routes.info import router as info_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.version)
app.include_router(health_router)
app.include_router(info_router)
app.include_router(assessments_router)
