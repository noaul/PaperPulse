import feedparser
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Feed, Paper
import logging

logger = logging.getLogger(__name__)


def parse_date(entry) -> datetime | None:
    for field in ("published_parsed", "updated_parsed"):
        val = getattr(entry, field, None)
        if val:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(val), tz=timezone.utc)
            except Exception:
                pass
    return None


async def fetch_feed(db: AsyncSession, feed: Feed) -> list[Paper]:
    try:
        parsed = feedparser.parse(feed.url)
    except Exception as e:
        logger.error(f"Failed to fetch {feed.url}: {e}")
        return []

    new_papers = []
    for entry in parsed.entries:
        doi = getattr(entry, "doi", None) or ""
        link = getattr(entry, "link", "") or ""
        title = getattr(entry, "title", "Untitled")

        # Deduplicate by DOI or URL
        if doi:
            existing = await db.execute(select(Paper).where(Paper.doi == doi))
            if existing.scalar_one_or_none():
                continue
        elif link:
            existing = await db.execute(select(Paper).where(Paper.url == link))
            if existing.scalar_one_or_none():
                continue

        authors = ""
        if hasattr(entry, "authors"):
            authors = ", ".join(a.get("name", "") for a in entry.authors)
        elif hasattr(entry, "author"):
            authors = entry.author

        abstract = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""

        paper = Paper(
            feed_id=feed.id,
            title=title,
            authors=authors,
            abstract=abstract,
            doi=doi or None,
            url=link,
            published_at=parse_date(entry),
        )
        db.add(paper)
        new_papers.append(paper)

    if new_papers:
        feed.last_fetched = datetime.now(timezone.utc)
        await db.commit()
        for p in new_papers:
            await db.refresh(p)

    logger.info(f"Feed '{feed.name}': {len(new_papers)} new papers")
    return new_papers


async def fetch_all_feeds(db: AsyncSession) -> list[Paper]:
    result = await db.execute(select(Feed).where(Feed.enabled == True))
    feeds = result.scalars().all()
    all_papers = []
    for feed in feeds:
        papers = await fetch_feed(db, feed)
        all_papers.extend(papers)
    return all_papers
