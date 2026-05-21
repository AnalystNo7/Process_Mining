from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.analytics import router as analytics_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.physical_datasets import router as physical_datasets_router
from app.api.v1.projects import router as projects_router
from app.api.v1.role_mappings import router as role_mappings_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.users import router as users_router
from app.api.v1.virtual_datasets import router as virtual_datasets_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging(settings)

app = FastAPI(title="Process Mining API", version="0.1.0")

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(physical_datasets_router, prefix="/api/v1")
app.include_router(role_mappings_router, prefix="/api/v1")
app.include_router(virtual_datasets_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
