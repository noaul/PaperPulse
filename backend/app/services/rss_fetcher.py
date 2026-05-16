import feedparser
import html
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Feed, Paper, Setting
import logging

logger = logging.getLogger(__name__)

TRACKING_QUERY_PARAMS = {
    "dgcid",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "ref",
    "ref_src",
}

LATEST_FETCHED_PAPER_IDS_KEY = "latest_fetched_paper_ids"


def latest_fetched_key(workspace_id: int | None = None) -> str:
    if workspace_id is None:
        return LATEST_FETCHED_PAPER_IDS_KEY
    return f"{LATEST_FETCHED_PAPER_IDS_KEY}:{int(workspace_id)}"


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


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_paper_url(url: str | None) -> str:
    if not url:
        return ""

    raw_url = str(url).strip()
    if not raw_url:
        return ""

    try:
        parts = urlsplit(raw_url)
    except ValueError:
        return raw_url

    query_items = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered_key = key.lower()
        if lowered_key.startswith("utm_") or lowered_key in TRACKING_QUERY_PARAMS:
            continue
        query_items.append((key, value))

    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urlencode(query_items, doseq=True),
        parts.fragment,
    ))


def get_entry_text(entry, *fields: str) -> str:
    for field in fields:
        value = getattr(entry, field, None)
        if isinstance(value, str) and value.strip():
            return clean_text(value)
        if isinstance(value, dict):
            detail_value = value.get("value") or value.get("content")
            if detail_value:
                return clean_text(detail_value)
    return ""


def extract_abstract(entry) -> str:
    direct = get_entry_text(
        entry,
        "summary",
        "description",
        "subtitle",
        "abstract",
        "summary_detail",
        "description_detail",
    )
    if direct:
        return direct

    content = getattr(entry, "content", None)
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                value = item.get("value") or item.get("content")
                if value:
                    return clean_text(value)
    return ""


async def fetch_feed(db: AsyncSession, feed: Feed) -> list[Paper]:
    try:
        parsed = feedparser.parse(feed.url)
    except Exception as e:
        logger.error(f"Failed to fetch {feed.url}: {e}")
        return []

    new_papers = []
    for entry in parsed.entries:
        doi = getattr(entry, "doi", None) or ""
        raw_link = getattr(entry, "link", "") or ""
        link = normalize_paper_url(raw_link)
        title = clean_text(getattr(entry, "title", "Untitled")) or "Untitled"

        # Deduplicate by DOI or URL
        if doi:
            existing = await db.execute(select(Paper).where(Paper.doi == doi, Paper.workspace_id == feed.workspace_id))
            if existing.scalar_one_or_none():
                continue
        elif link:
            candidate_urls = {link, str(raw_link).strip()}
            existing = await db.execute(
                select(Paper).where(Paper.url.in_(candidate_urls), Paper.workspace_id == feed.workspace_id)
            )
            if existing.scalar_one_or_none():
                continue

        authors = ""
        if hasattr(entry, "authors"):
            authors = ", ".join(a.get("name", "") for a in entry.authors)
        elif hasattr(entry, "author"):
            authors = entry.author

        abstract = extract_abstract(entry)

        paper = Paper(
            feed_id=feed.id,
            workspace_id=feed.workspace_id,
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


async def save_latest_fetched_paper_ids(
    db: AsyncSession,
    paper_ids: list[int],
    *,
    workspace_id: int | None = None,
) -> None:
    normalized = []
    for paper_id in paper_ids:
        if paper_id is not None and paper_id not in normalized:
            normalized.append(int(paper_id))

    value = json.dumps(normalized)
    keys = [latest_fetched_key(workspace_id)]
    if workspace_id in (None, 1) and LATEST_FETCHED_PAPER_IDS_KEY not in keys:
        keys.append(LATEST_FETCHED_PAPER_IDS_KEY)
    for key in keys:
        setting = await db.get(Setting, key)
        if setting:
            setting.value = value
        else:
            db.add(Setting(key=key, value=value))
    await db.commit()


async def get_latest_fetched_paper_ids(db: AsyncSession, workspace_id: int | None = None) -> list[int] | None:
    setting = await db.get(Setting, latest_fetched_key(workspace_id))
    if not setting and workspace_id is not None:
        setting = await db.get(Setting, LATEST_FETCHED_PAPER_IDS_KEY)
    if not setting:
        return None
    try:
        parsed = json.loads(setting.value or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []

    ids = []
    for value in parsed:
        try:
            paper_id = int(value)
        except (TypeError, ValueError):
            continue
        if paper_id not in ids:
            ids.append(paper_id)
    return ids


async def fetch_all_feeds(db: AsyncSession, workspace_id: int | None = None) -> list[Paper]:
    query = select(Feed).where(Feed.enabled == True)
    if workspace_id is not None:
        query = query.where(Feed.workspace_id == workspace_id)
    result = await db.execute(query)
    feeds = result.scalars().all()
    all_papers = []
    for feed in feeds:
        papers = await fetch_feed(db, feed)
        all_papers.extend(papers)
    await save_latest_fetched_paper_ids(
        db,
        [paper.id for paper in all_papers if paper.id is not None],
        workspace_id=workspace_id,
    )
    return all_papers
