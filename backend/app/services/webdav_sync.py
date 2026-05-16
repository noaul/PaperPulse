import json
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import AnalysisResult, Feed, Keyword, Paper, Setting

logger = logging.getLogger(__name__)


async def get_webdav_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Setting).where(Setting.key == "webdav_config"))
    row = result.scalar_one_or_none()
    if row:
        return json.loads(row.value)
    return {}


def _get_client(config: dict):
    from webdav3.client import Client
    options = {
        "webdav_hostname": config["url"],
        "webdav_login": config.get("username", ""),
        "webdav_password": config.get("password", ""),
    }
    return Client(options)


def _dt(value) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def export_data(db: AsyncSession, workspace_id: int = 1) -> bool:
    config = await get_webdav_config(db)
    if not config.get("url"):
        logger.info("WebDAV not configured")
        return False

    feeds_result = await db.execute(select(Feed).where(Feed.workspace_id == workspace_id))
    feeds = [{"name": f.name, "url": f.url, "journal_name": f.journal_name, "enabled": f.enabled} for f in feeds_result.scalars().all()]

    kw_result = await db.execute(select(Keyword).where(Keyword.workspace_id == workspace_id))
    keywords = [{"word": k.word, "category": k.category, "enabled": k.enabled} for k in kw_result.scalars().all()]

    papers_result = await db.execute(
        select(Paper, Feed.url)
        .outerjoin(Feed, Paper.feed_id == Feed.id)
        .where(Paper.workspace_id == workspace_id)
    )
    papers = [
        {
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "doi": paper.doi,
            "url": paper.url,
            "published_at": _dt(paper.published_at),
            "fetched_at": _dt(paper.fetched_at),
            "category": paper.category,
            "feed_url": feed_url,
        }
        for paper, feed_url in papers_result.all()
    ]

    analyses_result = await db.execute(
        select(AnalysisResult, Paper.doi, Paper.url, Paper.title, Keyword.word)
        .join(Paper, AnalysisResult.paper_id == Paper.id)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .where(AnalysisResult.workspace_id == workspace_id)
    )
    analysis_results = [
        {
            "paper_doi": paper_doi,
            "paper_url": paper_url,
            "paper_title": paper_title,
            "keyword_word": keyword_word,
            "relevance_score": analysis.relevance_score,
            "summary": analysis.summary,
            "analyzed_at": _dt(analysis.analyzed_at),
        }
        for analysis, paper_doi, paper_url, paper_title, keyword_word in analyses_result.all()
    ]

    data = {
        "feeds": feeds,
        "keywords": keywords,
        "papers": papers,
        "analysis_results": analysis_results,
    }
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    try:
        client = _get_client(config)
        remote_path = config.get("remote_path", "/PaperPulse/")
        if not client.check(remote_path):
            client.mkdir(remote_path)
        import io
        client.upload_sync(remote_path + "paperpulse_backup.json", io.BytesIO(content))
        logger.info(f"Data exported to WebDAV: {remote_path}")
        return True
    except Exception as e:
        logger.error(f"WebDAV export failed: {e}")
        return False


async def import_data(db: AsyncSession) -> bool:
    config = await get_webdav_config(db)
    if not config.get("url"):
        return False

    try:
        client = _get_client(config)
        remote_path = config.get("remote_path", "/PaperPulse/") + "paperpulse_backup.json"
        import io
        buf = io.BytesIO()
        client.download_sync(remote_path, buf)
        buf.seek(0)
        data = json.loads(buf.read().decode("utf-8"))

        feed_by_url = {}
        for feed_data in data.get("feeds", []):
            existing = await db.execute(select(Feed).where(Feed.url == feed_data["url"]))
            feed = existing.scalar_one_or_none()
            if not feed:
                feed = Feed(**feed_data)
                db.add(feed)
                await db.flush()
            feed_by_url[feed.url] = feed

        keyword_by_word = {}
        for kw_data in data.get("keywords", []):
            existing = await db.execute(select(Keyword).where(Keyword.word == kw_data["word"]))
            keyword = existing.scalar_one_or_none()
            if not keyword:
                keyword = Keyword(**kw_data)
                db.add(keyword)
                await db.flush()
            keyword_by_word[keyword.word] = keyword

        paper_by_key = {}
        for paper_data in data.get("papers", []):
            paper = None
            doi = paper_data.get("doi")
            url = paper_data.get("url")
            if doi:
                paper = (await db.execute(select(Paper).where(Paper.doi == doi))).scalar_one_or_none()
            if not paper and url:
                paper = (await db.execute(select(Paper).where(Paper.url == url))).scalar_one_or_none()
            if not paper:
                feed = feed_by_url.get(paper_data.get("feed_url"))
                paper = Paper(
                    feed_id=feed.id if feed else None,
                    title=paper_data.get("title") or "Untitled",
                    authors=paper_data.get("authors"),
                    abstract=paper_data.get("abstract"),
                    doi=doi,
                    url=url,
                    published_at=_parse_dt(paper_data.get("published_at")),
                    fetched_at=_parse_dt(paper_data.get("fetched_at")),
                    category=paper_data.get("category"),
                )
                db.add(paper)
                await db.flush()
            for key in (paper.doi, paper.url, paper.title):
                if key:
                    paper_by_key[key] = paper

        for analysis_data in data.get("analysis_results", []):
            paper = (
                paper_by_key.get(analysis_data.get("paper_doi"))
                or paper_by_key.get(analysis_data.get("paper_url"))
                or paper_by_key.get(analysis_data.get("paper_title"))
            )
            keyword = keyword_by_word.get(analysis_data.get("keyword_word"))
            if not paper or not keyword:
                continue
            existing = await db.execute(
                select(AnalysisResult).where(
                    AnalysisResult.paper_id == paper.id,
                    AnalysisResult.keyword_id == keyword.id,
                )
            )
            if existing.scalar_one_or_none():
                continue
            db.add(AnalysisResult(
                paper_id=paper.id,
                keyword_id=keyword.id,
                relevance_score=float(analysis_data.get("relevance_score") or 0),
                summary=analysis_data.get("summary"),
                analyzed_at=_parse_dt(analysis_data.get("analyzed_at")),
            ))

        await db.commit()
        logger.info("Data imported from WebDAV")
        return True
    except Exception as e:
        logger.error(f"WebDAV import failed: {e}")
        return False
