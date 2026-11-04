"""
brAInfection V2 — Application entry point.

Creates the FastAPI app, registers middleware, routers and static mounts.
"""
import logging
import sys
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine

# Import all models so SQLAlchemy knows about them
import app.models  # noqa: F401

# Routes
from app.routes.visitors import router as visitors_router
from app.routes.sessions import router as sessions_router
from app.routes.consent import router as consent_router
from app.routes.devices import router as devices_router
from app.routes.locations import router as locations_router
from app.routes.camera import router as camera_router
from app.routes.telemetry import router as telemetry_router
from app.routes.admin import router as admin_router
from app.routes.legacy import router as legacy_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    stream=sys.stdout,
)
logger = logging.getLogger("brAInfection")

# ---------------------------------------------------------------------------
# Lifespan: create tables on startup (dev convenience; Alembic is canonical)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.is_dev:
        Base.metadata.create_all(bind=engine)
        logger.info("Dev mode: ensured all tables exist.")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent

app = FastAPI(
    title="brAInfection — Phishing Awareness Lab",
    version="2.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
settings = get_settings()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add a unique request ID to every request for traceability."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    # Log request (never log sensitive values: tokens, coordinates, full UA)
    logger.info(
        "req=%s method=%s path=%s status=%d",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return a consistent JSON error shape for unhandled exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled exception req=%s: %s", request_id, exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred.",
            "request_id": request_id,
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(visitors_router)
app.include_router(sessions_router)
app.include_router(consent_router)
app.include_router(devices_router)
app.include_router(locations_router)
app.include_router(camera_router)
app.include_router(telemetry_router)
app.include_router(admin_router)
app.include_router(legacy_router)

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/admin")
def admin_page():
    return FileResponse(BASE / "static" / "admin.html")


@app.get("/health")
def health():
    return {"status": "ok"}
