import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .database import init_db, SessionLocal
from .models import Setting
from sqlalchemy import select
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def daily_job():
    logger.info("Running daily job: fetch + analyze + email")
    async with SessionLocal() as db:
        from .services.rss_fetcher import fetch_all_feeds
        from .services.ai_analyzer import analyze_new_papers
        from .services.email_sender import send_daily_report
        from .services.webdav_sync import get_webdav_config

        papers = await fetch_all_feeds(db)
        logger.info(f"Fetched {len(papers)} new papers")

        results = await analyze_new_papers(db)
        logger.info(f"Analyzed {len(results)} papers")

        # Get threshold
        result = await db.execute(select(Setting).where(Setting.key == "schedule_config"))
        row = result.scalar_one_or_none()
        threshold = 6.0
        if row:
            cfg = json.loads(row.value)
            threshold = cfg.get("relevance_threshold", 6.0)

        await send_daily_report(db, threshold=threshold)

        # Auto WebDAV export if configured
        wdc = await get_webdav_config(db)
        if wdc.get("url"):
            from .services.webdav_sync import export_data
            await export_data(db)


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
            return cfg.get("cron_hour", 6), cfg.get("cron_minute", 0)
    except Exception:
        pass
    return 6, 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.environ.get("DB_PATH", "/app/data/paperpulse.db").rsplit("/", 1)[0], exist_ok=True)
    await init_db()
    logger.info("Database initialized")

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
        # Allow auth endpoints and non-API paths
        if not path.startswith("/api/") or path.startswith("/api/auth/"):
            return await call_next(request)

        # Check if admin user is registered; if not, allow all (first-time setup)
        async with SessionLocal() as db:
            result = await db.execute(select(Setting).where(Setting.key == "admin_user"))
            admin_user = result.scalar_one_or_none()

            if not admin_user:
                # No admin registered yet, allow access
                return await call_next(request)

            # Verify token
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(status_code=401, content={"detail": "未登录"})

            token = auth_header[7:]
            result = await db.execute(select(Setting).where(Setting.key == "auth_token"))
            token_row = result.scalar_one_or_none()

            if not token_row or token_row.value != token:
                return JSONResponse(status_code=401, content={"detail": "登录已过期，请重新登录"})

        return await call_next(request)


app.add_middleware(AuthMiddleware)

# Routers
from .routers import feeds, papers, keywords, settings, analysis, dashboard, auth
app.include_router(auth.router)
app.include_router(feeds.router)
app.include_router(papers.router)
app.include_router(keywords.router)
app.include_router(settings.router)
app.include_router(analysis.router)
app.include_router(dashboard.router)

# Serve frontend static files
STATIC_DIR = os.environ.get("STATIC_DIR", "/app/static")
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=f"{STATIC_DIR}/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(f"{STATIC_DIR}/index.html")
