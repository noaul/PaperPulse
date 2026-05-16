from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_workspace
from ..models import ReadingQueueItem, Workspace
from ..schemas import (
    ReadingQueueItemCreate,
    ReadingQueueItemOut,
    ReadingQueueItemUpdate,
    ReadingQueueListOut,
)

router = APIRouter(prefix="/api/reading-queue", tags=["reading-queue"])


def item_out(item: ReadingQueueItem) -> ReadingQueueItemOut:
    return ReadingQueueItemOut(
        id=item.id,
        title=item.title,
        url=item.url or "",
        abstract=item.abstract or "",
        tags=item.tags,
        status=item.status,
        notes=item.notes or "",
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def get_item_or_404(db: AsyncSession, item_id: int, workspace_id: int) -> ReadingQueueItem:
    result = await db.execute(
        select(ReadingQueueItem).where(
            ReadingQueueItem.id == item_id,
            ReadingQueueItem.workspace_id == workspace_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Reading queue item not found")
    return item


@router.get("", response_model=ReadingQueueListOut)
async def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    query = select(ReadingQueueItem).where(ReadingQueueItem.workspace_id == workspace.id)
    count_query = select(func.count(ReadingQueueItem.id)).where(ReadingQueueItem.workspace_id == workspace.id)

    if search:
        like = f"%{search.strip()}%"
        condition = or_(ReadingQueueItem.title.ilike(like), ReadingQueueItem.abstract.ilike(like))
        query = query.where(condition)
        count_query = count_query.where(condition)
    if status:
        query = query.where(ReadingQueueItem.status == status)
        count_query = count_query.where(ReadingQueueItem.status == status)

    if tag:
        result = await db.execute(query.order_by(desc(ReadingQueueItem.created_at), desc(ReadingQueueItem.id)))
        rows = [item for item in result.scalars().all() if tag in item.tags]
        total = len(rows)
        start = (page - 1) * page_size
        page_items = rows[start:start + page_size]
    else:
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        result = await db.execute(
            query
            .order_by(desc(ReadingQueueItem.created_at), desc(ReadingQueueItem.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        page_items = result.scalars().all()

    pages = max(1, (total + page_size - 1) // page_size)
    return ReadingQueueListOut(
        items=[item_out(item) for item in page_items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=ReadingQueueItemOut)
async def create_item(
    payload: ReadingQueueItemCreate,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    item = ReadingQueueItem(
        workspace_id=workspace.id,
        title=payload.title.strip(),
        url=payload.url.strip(),
        abstract=payload.abstract.strip(),
        notes=payload.notes.strip(),
        status="unread",
    )
    item.set_tags(payload.tags)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item_out(item)


@router.get("/{item_id}", response_model=ReadingQueueItemOut)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    item = await get_item_or_404(db, item_id, workspace.id)
    return item_out(item)


@router.put("/{item_id}", response_model=ReadingQueueItemOut)
async def update_item(
    item_id: int,
    payload: ReadingQueueItemUpdate,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    item = await get_item_or_404(db, item_id, workspace.id)
    data = payload.model_dump(exclude_unset=True)

    if "title" in data:
        item.title = data["title"].strip()
    if "url" in data:
        item.url = (data["url"] or "").strip()
    if "abstract" in data:
        item.abstract = (data["abstract"] or "").strip()
    if "notes" in data:
        item.notes = (data["notes"] or "").strip()
    if "status" in data:
        item.status = data["status"]
    if "tags" in data:
        item.set_tags(data["tags"] or [])

    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item_out(item)


@router.delete("/{item_id}")
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    item = await get_item_or_404(db, item_id, workspace.id)
    await db.delete(item)
    await db.commit()
    return {"success": True}
