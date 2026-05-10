from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Feed, Paper
from ..schemas import FeedCreate, FeedUpdate, FeedOut
from ..services.rss_fetcher import fetch_feed

router = APIRouter(prefix="/api/feeds", tags=["feeds"])


@router.get("", response_model=list[FeedOut])
async def list_feeds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feed).order_by(Feed.created_at.desc()))
    feeds = result.scalars().all()
    out = []
    for f in feeds:
        count = await db.execute(select(func.count()).where(Paper.feed_id == f.id))
        fo = FeedOut.model_validate(f)
        fo.paper_count = count.scalar() or 0
        out.append(fo)
    return out


@router.post("", response_model=FeedOut)
async def create_feed(data: FeedCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Feed).where(Feed.url == data.url))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Feed URL already exists")
    feed = Feed(**data.model_dump())
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    fo = FeedOut.model_validate(feed)
    fo.paper_count = 0
    return fo


@router.put("/{feed_id}", response_model=FeedOut)
async def update_feed(feed_id: int, data: FeedUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(404, "Feed not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(feed, k, v)
    await db.commit()
    await db.refresh(feed)
    count = await db.execute(select(func.count()).where(Paper.feed_id == feed.id))
    fo = FeedOut.model_validate(feed)
    fo.paper_count = count.scalar() or 0
    return fo


@router.delete("/{feed_id}")
async def delete_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(404, "Feed not found")
    await db.delete(feed)
    await db.commit()
    return {"success": True}


@router.post("/{feed_id}/fetch")
async def fetch_single_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(404, "Feed not found")
    papers = await fetch_feed(db, feed)
    return {"success": True, "new_papers": len(papers)}
