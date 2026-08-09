from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.assessments import router as assessments_router
from app.api.routes.devices import router as devices_router
from app.api.routes.health import router as health_router
from app.api.routes.info import router as info_router
from app.core.config import ensure_runtime_secrets, get_settings
from app.core.database import Database
from app.services.vault import CredentialVault

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the database and vault for the life of the process.

    Failures here are allowed to propagate. NetVault's lifespan once swallowed
    startup errors and served a half-initialised app, which is worse than not
    starting: the API answered, just wrongly.
    """
    resolved = ensure_runtime_secrets(get_settings())

    database = Database(resolved.db_path)
    await database.connect()

    app.state.settings = resolved
    app.state.db = database
    app.state.vault = CredentialVault(database, resolved.credentials_master_key)

    try:
        yield
    finally:
        await database.disconnect()


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["content-type"],
)

app.include_router(health_router)
app.include_router(info_router)
app.include_router(assessments_router)
app.include_router(devices_router)
