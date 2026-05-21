from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging(settings)

app = FastAPI(title="Process Mining API", version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
