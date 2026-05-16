from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import os

DB_PATH = os.environ.get("DB_PATH", "/app/data/paperpulse.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_compat_columns(conn)


async def _has_column(conn, table_name: str, column_name: str) -> bool:
    result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
    return any(row[1] == column_name for row in result.fetchall())


async def _add_column_if_missing(conn, table_name: str, column_sql: str) -> None:
    column_name = column_sql.split()[0]
    if not await _has_column(conn, table_name, column_name):
        await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))


async def _ensure_compat_columns(conn) -> None:
    """Keep existing SQLite deployments compatible with new workspace columns."""
    workspace_tables = [
        "feeds",
        "papers",
        "keywords",
        "analysis_results",
        "reports",
        "report_items",
        "email_deliveries",
        "reading_queue_items",
        "weknora_syncs",
        "workflow_executions",
    ]
    for table in workspace_tables:
        await _add_column_if_missing(conn, table, "workspace_id INTEGER NOT NULL DEFAULT 1")
    await _add_column_if_missing(conn, "reports", "topic_rule_id INTEGER")

    result = await conn.execute(text("SELECT COUNT(*) FROM workspaces"))
    if (result.scalar() or 0) == 0:
        await conn.execute(text(
            "INSERT INTO workspaces "
            "(id, name, slug, color, icon, sort_order, is_default, enabled, created_at, updated_at) "
            "VALUES (1, '默认工作区', 'default', '#4F46E5', 'folder', 0, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ))
