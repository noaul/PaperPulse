from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..dependencies import get_current_workspace
from ..models import Feed, Paper, Workspace
from ..schemas import FeedBulkDelete, FeedCreate, FeedUpdate, FeedOut
from ..services.rss_fetcher import fetch_feed, save_latest_fetched_paper_ids

router = APIRouter(prefix="/api/feeds", tags=["feeds"])


@router.get("", response_model=list[FeedOut])
async def list_feeds(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    result = await db.execute(
        select(Feed)
        .where(Feed.workspace_id == workspace.id)
        .order_by(Feed.created_at.desc())
    )
    feeds = result.scalars().all()
    out = []
    for f in feeds:
        count = await db.execute(
            select(func.count()).where(Paper.feed_id == f.id, Paper.workspace_id == workspace.id)
        )
        fo = FeedOut.model_validate(f)
        fo.paper_count = count.scalar() or 0
        out.append(fo)
    return out


@router.post("", response_model=FeedOut)
async def create_feed(
    data: FeedCreate,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    existing = await db.execute(select(Feed).where(Feed.url == data.url, Feed.workspace_id == workspace.id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Feed URL already exists")
    feed = Feed(**data.model_dump(), workspace_id=workspace.id)
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    fo = FeedOut.model_validate(feed)
    fo.paper_count = 0
    return fo


@router.post("/fetch-all")
async def fetch_all_enabled_feeds(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    result = await db.execute(
        select(Feed)
        .where(Feed.enabled == True, Feed.workspace_id == workspace.id)
        .order_by(Feed.created_at.desc())
    )
    feeds = result.scalars().all()
    all_papers = []
    per_feed = []

    for feed in feeds:
        papers = await fetch_feed(db, feed)
        all_papers.extend(papers)
        per_feed.append({
            "feed_id": feed.id,
            "name": feed.name,
            "new_papers": len(papers),
        })

    paper_ids = [paper.id for paper in all_papers if paper.id is not None]
    await save_latest_fetched_paper_ids(db, paper_ids, workspace_id=workspace.id)
    return {
        "success": True,
        "feed_count": len(feeds),
        "new_papers": len(all_papers),
        "paper_ids": paper_ids,
        "feeds": per_feed,
    }


@router.post("/bulk-delete")
async def bulk_delete_feeds(
    payload: FeedBulkDelete,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    unique_ids = []
    for feed_id in payload.ids:
        if feed_id not in unique_ids:
            unique_ids.append(feed_id)

    if not unique_ids:
        return {"success": True, "deleted_count": 0, "missing_ids": []}

    result = await db.execute(select(Feed).where(Feed.id.in_(unique_ids), Feed.workspace_id == workspace.id))
    feeds = result.scalars().all()
    found_ids = {feed.id for feed in feeds}
    for feed in feeds:
        await db.delete(feed)
    await db.commit()

    missing_ids = [feed_id for feed_id in unique_ids if feed_id not in found_ids]
    return {
        "success": True,
        "deleted_count": len(feeds),
        "missing_ids": missing_ids,
    }


@router.put("/{feed_id}", response_model=FeedOut)
async def update_feed(
    feed_id: int,
    data: FeedUpdate,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    result = await db.execute(select(Feed).where(Feed.id == feed_id, Feed.workspace_id == workspace.id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(404, "Feed not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(feed, k, v)
    await db.commit()
    await db.refresh(feed)
    count = await db.execute(select(func.count()).where(Paper.feed_id == feed.id, Paper.workspace_id == workspace.id))
    fo = FeedOut.model_validate(feed)
    fo.paper_count = count.scalar() or 0
    return fo


@router.delete("/{feed_id}")
async def delete_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    result = await db.execute(select(Feed).where(Feed.id == feed_id, Feed.workspace_id == workspace.id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(404, "Feed not found")
    await db.delete(feed)
    await db.commit()
    return {"success": True}


@router.post("/{feed_id}/fetch")
async def fetch_single_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    result = await db.execute(select(Feed).where(Feed.id == feed_id, Feed.workspace_id == workspace.id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(404, "Feed not found")
    papers = await fetch_feed(db, feed)
    paper_ids = [paper.id for paper in papers if paper.id is not None]
    await save_latest_fetched_paper_ids(db, paper_ids, workspace_id=workspace.id)
    return {"success": True, "new_papers": len(papers), "paper_ids": paper_ids}
