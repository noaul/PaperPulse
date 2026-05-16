from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import ensure_default_workspace, slugify
from ..models import Workspace
from ..schemas import WorkspaceCreate, WorkspaceOut, WorkspaceUpdate

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


async def _unique_slug(db: AsyncSession, requested: str, workspace_id: int | None = None) -> str:
    base = slugify(requested)
    candidate = base
    index = 2
    while True:
        query = select(Workspace).where(Workspace.slug == candidate)
        if workspace_id is not None:
            query = query.where(Workspace.id != workspace_id)
        existing = (await db.execute(query)).scalar_one_or_none()
        if not existing:
            return candidate
        candidate = f"{base}-{index}"
        index += 1


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(db: AsyncSession = Depends(get_db)):
    await ensure_default_workspace(db)
    result = await db.execute(select(Workspace).order_by(Workspace.sort_order, Workspace.id))
    return [WorkspaceOut.model_validate(workspace) for workspace in result.scalars().all()]


@router.post("", response_model=WorkspaceOut)
async def create_workspace(payload: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    await ensure_default_workspace(db)
    workspace = Workspace(
        name=payload.name.strip(),
        slug=await _unique_slug(db, payload.slug or payload.name),
        description=payload.description,
        color=payload.color or "#4F46E5",
        icon=payload.icon or "folder",
        enabled=True,
        is_default=False,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceOut.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(workspace_id: int, db: AsyncSession = Depends(get_db)):
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(404, "Workspace not found")
    return WorkspaceOut.model_validate(workspace)


@router.put("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(workspace_id: int, payload: WorkspaceUpdate, db: AsyncSession = Depends(get_db)):
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(404, "Workspace not found")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        workspace.name = data["name"].strip()
    if "slug" in data and data["slug"]:
        workspace.slug = await _unique_slug(db, data["slug"], workspace_id)
    for field in ("description", "color", "icon", "sort_order", "enabled"):
        if field in data:
            setattr(workspace, field, data[field])
    if data.get("is_default"):
        result = await db.execute(select(Workspace).where(Workspace.id != workspace.id))
        for other in result.scalars().all():
            other.is_default = False
            db.add(other)
        workspace.is_default = True

    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceOut.model_validate(workspace)


@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: int, db: AsyncSession = Depends(get_db)):
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(404, "Workspace not found")
    if workspace.is_default:
        raise HTTPException(400, "默认工作区不能删除")
    workspace.enabled = False
    db.add(workspace)
    await db.commit()
    return {"success": True}
