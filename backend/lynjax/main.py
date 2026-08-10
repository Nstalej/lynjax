from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lynjax.api.routes.auth import router as auth_router
from lynjax.api.routes.devices import router as devices_router
from lynjax.api.routes.health import router as health_router
from lynjax.api.routes.info import router as info_router
from lynjax.api.routes.network import router as network_router
from lynjax.core.config import ensure_runtime_secrets, get_settings
from lynjax.core.database import Database
from lynjax.core.logging import configure_logging
from lynjax.services.devices import DeviceRepository
from lynjax.services.reports.store import ReportStore
from lynjax.services.scheduler import build_scheduler
from lynjax.services.vault import CredentialVault
from lynjax.web import mount_frontend

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the database and vault for the life of the process.

    Failures here are allowed to propagate. NetVault's lifespan once swallowed
    startup errors and served a half-initialised app, which is worse than not
    starting: the API answered, just wrongly.
    """
    resolved = ensure_runtime_secrets(get_settings())
    configure_logging(resolved)

    database = Database(resolved.db_path)
    await database.connect()

    app.state.settings = resolved
    app.state.db = database
    app.state.vault = CredentialVault(database, resolved.credentials_master_key)
    app.state.reports = ReportStore()

    scheduler = None
    if resolved.polling_enabled:
        scheduler = build_scheduler(
            DeviceRepository(database),
            app.state.vault,
            resolved,
            interval_minutes=resolved.polling_interval_minutes,
            concurrency=resolved.polling_concurrency,
        )
        await scheduler.start()
    app.state.scheduler = scheduler

    try:
        yield
    finally:
        if scheduler is not None:
            await scheduler.stop()
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
app.include_router(auth_router)
app.include_router(info_router)
app.include_router(devices_router)
app.include_router(network_router)

# Mounted last: the SPA claims "/" and would otherwise shadow the routers.
mount_frontend(app)
