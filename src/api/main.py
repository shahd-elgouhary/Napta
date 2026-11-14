"""FastAPI application entrypoint for FieldWise AI - Egypt Edition."""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.config import get_settings
from src.api.routes import environment, farm, recommendations, scenarios, sources, voice

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fieldwise")

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Climate-smart crop rotation and farm planning platform for Egyptian farmers. "
        "Integrates NASA POWER climate data, SoilGrids, and deterministic agricultural decision engine."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing and audit logging middleware
@app.middleware("http")
async def audit_and_timing_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred. Please contact support or retry.",
                "detail": str(exc) if settings.DEBUG else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


# Centralized Validation Error Handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Invalid input schema. Please check the submitted fields.",
            "details": exc.errors(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# Include Domain Routers
app.include_router(farm.router)
app.include_router(environment.router)
app.include_router(recommendations.router)
app.include_router(scenarios.router)
app.include_router(sources.router)
app.include_router(voice.router)


# Health Check
@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint for monitoring, load balancers, and readiness probes."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "track": "Track B (The Body)",
    }


# Root information endpoint
@app.get("/", tags=["System"])
async def root_info():
    """Root info endpoint providing API metadata and links."""
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "health": "/health",
        "description": "FastAPI backend serving Egyptian farmers and agricultural experts.",
        "interfaces": {
            "farmer_pwa": "/farmer/",
            "expert_console": "Streamlit app on port 8501",
        },
    }


# Mount Farmer PWA static files if the directory exists
farmer_pwa_path = Path(__file__).resolve().parent.parent.parent / "apps" / "farmer_pwa"
if farmer_pwa_path.exists():
    app.mount("/farmer", StaticFiles(directory=str(farmer_pwa_path), html=True), name="farmer_pwa")
