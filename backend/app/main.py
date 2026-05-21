from fastapi import FastAPI

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging(settings)

app = FastAPI(title="Process Mining API", version="0.1.0")

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
