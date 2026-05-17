import os
import logging
import asyncio
import json as json_mod
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .database import init_db, SessionLocal, engine
from .models import Setting
from .routers.auth import verify_token
from sqlalchemy import select, text
import json

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .rate_limit import limiter

# Structured JSON log formatter for production
class _JsonFormatter(logging.Formatter):
    def format(self, record):
        obj = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json_mod.dumps(obj, ensure_ascii=False)


_LOG_FORMAT = os.environ.get("LOG_FORMAT", "text")  # "json" or "text"
if _LOG_FORMAT == "json":
    _handler = logging.StreamHandler()
    _handler.setFormatter(_JsonFormatter())
    logging.root.handlers = [_handler]
    logging.root.setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def daily_job():
    logger.info("Running daily workflow")
    async with SessionLocal() as db:
        from .workflows.daily import run_daily_workflow

        execution = await run_daily_workflow(db)
        logger.info(
            "Daily workflow finished: id=%s status=%s summary=%s",
            execution.id,
            execution.status,
            execution.summary_json,
        )


async def _get_schedule_config() -> tuple[int, int]:
    """Async helper to read cron config from DB."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT value FROM settings WHERE key='schedule_config'"))
            row = result.fetchone()
            if row:
                cfg = json.loads(row[0])
                hour = int(cfg.get("cron_hour", 6))
                minute = int(cfg.get("cron_minute", 0))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return hour, minute
                logger.warning("Invalid schedule_config cron time hour=%s minute=%s; using 06:00", hour, minute)
    except Exception:
        pass
    return 6, 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.environ.get("DB_PATH", "/app/data/paperpulse.db").rsplit("/", 1)[0], exist_ok=True)
    await init_db()
    logger.info("Database initialized")

    # Mark any stale 'running' executions as interrupted (from previous crashes)
    async with SessionLocal() as db:
        from .models import WorkflowExecution
        from sqlalchemy import update
        from datetime import datetime, timezone
        await db.execute(
            update(WorkflowExecution)
            .where(WorkflowExecution.status == "running")
            .values(status="interrupted", error_message="Process restarted before completion")
        )
        await db.commit()
        logger.info("Cleaned up stale running executions")

    hour, minute = await _get_schedule_config()
    scheduler.add_job(daily_job, "cron", hour=hour, minute=minute, id="daily_job", replace_existing=True)
    scheduler.start()
    logger.info(f"Scheduler started: daily job at {hour:02d}:{minute:02d}")

    yield

    scheduler.shutdown()
    from .services.ai_analyzer import close_http_client
    await close_http_client()


app = FastAPI(title="PaperPulse", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})

# Cache for admin_user existence check to avoid DB query on every request
_admin_registered: bool | None = None


def set_admin_registered(value: bool) -> None:
    global _admin_registered
    _admin_registered = value


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global _admin_registered
        path = request.url.path
        # Allow auth endpoints, health check, and non-API paths
        if not path.startswith("/api/") or path.startswith("/api/auth/") or path == "/api/health":
            return await call_next(request)

        # Check if admin user is registered; if not, allow all (first-time setup)
        if _admin_registered is None:
            async with SessionLocal() as db:
                result = await db.execute(select(Setting).where(Setting.key == "admin_user"))
                _admin_registered = result.scalar_one_or_none() is not None

        if not _admin_registered:
            return await call_next(request)

        # Verify JWT token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "未登录"})

        token = auth_header[7:]
        payload = verify_token(token)
        if payload is None:
            return JSONResponse(status_code=401, content={"detail": "登录已过期，请重新登录"})

        return await call_next(request)


app.add_middleware(AuthMiddleware)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# CORS for development (set CORS_ORIGINS env var, e.g. "http://localhost:5173")
_cors_origins = os.environ.get("CORS_ORIGINS", "")
if _cors_origins:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in _cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Routers
from .routers import feeds, papers, keywords, settings, analysis, dashboard, auth, executions, workflows, reports, reading_queue, zotero, workspaces, email_topic_rules
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(email_topic_rules.router)
app.include_router(feeds.router)
app.include_router(papers.router)
app.include_router(keywords.router)
app.include_router(settings.router)
app.include_router(analysis.router)
app.include_router(dashboard.router)
app.include_router(executions.router)
app.include_router(workflows.router)
app.include_router(reports.router)
app.include_router(reading_queue.router)
app.include_router(zotero.router)


@app.get("/api/health")
async def health_check():
    checks = {"status": "ok", "version": app.version}
    # DB connectivity
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        checks["status"] = "degraded"
    # Scheduler
    checks["scheduler"] = "running" if scheduler.running else "stopped"
    return checks


# Serve frontend static files
STATIC_DIR = os.environ.get("STATIC_DIR", "/app/static")
if os.path.isdir(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        if "." in os.path.basename(full_path):
            raise HTTPException(status_code=404, detail="Static file not found")
        return FileResponse(
            f"{STATIC_DIR}/index.html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
            },
        )
