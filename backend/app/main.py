from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.csrf import CsrfMiddleware
from app.core.observability import init_observability
from app.core.schema import ensure_schema
from app.db.base import Base
from app.db.session import engine
from app.realtime.hub import hub
from app import models  # noqa: F401  ensure models are registered


def _run_alembic_upgrade() -> None:
    """Apply Alembic migrations when available; fall back to create_all for demos."""
    try:
        from alembic import command
        from alembic.config import Config

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", str(engine.url))
        command.upgrade(cfg, "head")
    except Exception:
        Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _run_alembic_upgrade()
    ensure_schema(engine)
    await hub.start()
    yield
    await hub.stop()


app = FastAPI(
    title="Studio Sunny HQ API",
    description="Company operating system for Studio Sunny.",
    version="0.2.0",
    lifespan=lifespan,
)

init_observability(app)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(CsrfMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token"],
    expose_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health():
    return {"status": "ok", "product": "Studio Sunny HQ"}
