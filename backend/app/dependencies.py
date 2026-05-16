import re

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import Workspace

DEFAULT_WORKSPACE_NAME = "默认工作区"
DEFAULT_WORKSPACE_SLUG = "default"


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", (value or "").strip().lower()).strip("-")
    return normalized or "workspace"


async def ensure_default_workspace(db: AsyncSession) -> Workspace:
    result = await db.execute(
        select(Workspace)
        .where(Workspace.is_default == True)
        .order_by(Workspace.id)
        .limit(1)
    )
    workspace = result.scalar_one_or_none()
    if workspace:
        return workspace

    result = await db.execute(select(Workspace).order_by(Workspace.id).limit(1))
    workspace = result.scalar_one_or_none()
    if workspace:
        workspace.is_default = True
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)
        return workspace

    workspace = Workspace(
        id=1,
        name=DEFAULT_WORKSPACE_NAME,
        slug=DEFAULT_WORKSPACE_SLUG,
        is_default=True,
        enabled=True,
        sort_order=0,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def get_current_workspace(
    x_workspace_id: int | None = Header(default=None, alias="X-Workspace-Id"),
    db: AsyncSession = Depends(get_db),
) -> Workspace:
    if x_workspace_id is None:
        return await ensure_default_workspace(db)

    result = await db.execute(
        select(Workspace).where(
            Workspace.id == x_workspace_id,
            Workspace.enabled == True,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(404, "工作区不存在或已禁用")
    return workspace
