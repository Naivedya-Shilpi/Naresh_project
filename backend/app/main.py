"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create the local SQLite tables before serving requests."""
    init_db()
    yield


OPENAPI_TAGS = [
    {"name": "system", "description": "Service metadata and liveness health checks."},
    {
        "name": "meetings",
        "description": "Upload meetings, inspect metadata, run audio/AI processing stages, and fetch transcripts.",
    },
]

app = FastAPI(
    title="Meeting Transcriber API",
    description="Modular monolith REST API for uploading meeting videos, processing audio/AI pipelines, and retrieving structured transcripts.",
    version="0.10.0",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

ALLOWED_ORIGINS = list(
    dict.fromkeys([settings.frontend_origin, "http://localhost:3000", "http://127.0.0.1:3000"])
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)
