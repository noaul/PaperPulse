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
from .database import init_db, SessionLocal
from .models import Setting
from sqlalchemy import select
import json

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


def _get_schedule_config_sync():
    """Sync helper to read cron config before scheduler starts."""
    import sqlite3
    db_path = os.environ.get("DB_PATH", "/app/data/paperpulse.db")
    if not os.path.exists(db_path):
        return 6, 0
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT value FROM settings WHERE key='schedule_config'").fetchone()
        conn.close()
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

    hour, minute = _get_schedule_config_sync()
    scheduler.add_job(daily_job, "cron", hour=hour, minute=minute, id="daily_job", replace_existing=True)
    scheduler.start()
    logger.info(f"Scheduler started: daily job at {hour:02d}:{minute:02d}")

    yield

    scheduler.shutdown()


app = FastAPI(title="PaperPulse", version="1.0.0", lifespan=lifespan)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Allow auth endpoints, health check, and non-API paths
        if not path.startswith("/api/") or path.startswith("/api/auth/") or path == "/api/health":
            return await call_next(request)

        # Check if admin user is registered; if not, allow all (first-time setup)
        async with SessionLocal() as db:
            result = await db.execute(select(Setting).where(Setting.key == "admin_user"))
            admin_user = result.scalar_one_or_none()

            if not admin_user:
                return await call_next(request)

        # Verify JWT token (no DB query needed)
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "未登录"})

        from .routers.auth import verify_token
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
    return {"status": "ok", "version": app.version}


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
