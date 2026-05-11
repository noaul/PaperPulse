import json
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AnalysisResult, Feed, Keyword, Paper, Report, Setting, WeKnoraSync
from .rss_fetcher import clean_text, normalize_paper_url
from .weknora_client import WeKnoraClient


DEFAULT_WEKNORA_CONFIG = {
    "enabled": False,
    "base_url": "http://localhost:8080/api/v1",
    "api_key": "",
    "knowledge_base_id": "",
    "min_score_to_sync": 6.0,
    "sync_reports": True,
    "sync_papers": True,
}


class ManualKnowledgeClient(Protocol):
    async def create_manual_knowledge(
        self,
        knowledge_base_id: str,
        title: str,
        content: str,
        channel: str = "api",
    ) -> dict:
        ...


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def get_weknora_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Setting).where(Setting.key == "weknora_config"))
    row = result.scalar_one_or_none()
    if not row:
        return DEFAULT_WEKNORA_CONFIG.copy()

    try:
        saved = json.loads(row.value or "{}")
    except json.JSONDecodeError:
        saved = {}
    return {**DEFAULT_WEKNORA_CONFIG, **saved}


def is_weknora_ready(config: dict) -> bool:
    return bool(
        config.get("enabled")
        and str(config.get("base_url") or "").strip()
        and str(config.get("api_key") or "").strip()
        and str(config.get("knowledge_base_id") or "").strip()
    )


def build_weknora_client(config: dict) -> WeKnoraClient:
    return WeKnoraClient(
        base_url=str(config.get("base_url") or ""),
        api_key=str(config.get("api_key") or ""),
    )


async def find_successful_sync(
    db: AsyncSession,
    *,
    sync_type: str,
    paper_id: int | None = None,
    report_id: int | None = None,
) -> WeKnoraSync | None:
    query = select(WeKnoraSync).where(
        WeKnoraSync.sync_type == sync_type,
        WeKnoraSync.status == "success",
    )
    if paper_id is not None:
        query = query.where(WeKnoraSync.paper_id == paper_id)
    if report_id is not None:
        query = query.where(WeKnoraSync.report_id == report_id)

    result = await db.execute(query.order_by(desc(WeKnoraSync.synced_at), desc(WeKnoraSync.id)).limit(1))
    return result.scalar_one_or_none()


def _format_datetime(value: datetime | None) -> str:
    if not value:
        return "-"
    return value.date().isoformat()


def render_paper_markdown(
    paper: Paper,
    analysis_rows: list[tuple[AnalysisResult, Keyword, str | None]],
) -> str:
    title = clean_text(paper.title)
    authors = clean_text(paper.authors)
    abstract = clean_text(paper.abstract)
    url = normalize_paper_url(paper.url)

    best_score = max((float(row[0].relevance_score or 0) for row in analysis_rows), default=0.0)
    summaries = []
    keywords = []
    journal = ""
    for analysis, keyword, journal_name in analysis_rows:
        if analysis.summary and analysis.summary not in summaries:
            summaries.append(analysis.summary)
        if keyword.word and keyword.word not in keywords:
            keywords.append(keyword.word)
        if journal_name and not journal:
            journal = journal_name

    lines = [
        f"# {title}",
        "",
        f"- DOI: {paper.doi or '-'}",
        f"- URL: {url or '-'}",
        f"- Journal: {journal or '-'}",
        f"- Authors: {authors or '-'}",
        f"- Published At: {_format_datetime(paper.published_at)}",
        f"- PaperPulse Score: {best_score:.1f}",
        f"- Matched Keywords: {', '.join(keywords) or '-'}",
        "",
        "## AI Summary",
        "",
        "\n\n".join(clean_text(summary) for summary in summaries) or "-",
        "",
        "## Abstract",
        "",
        abstract or "-",
        "",
        "## Source",
        "",
        url or paper.doi or "-",
    ]
    return "\n".join(lines).strip() + "\n"


async def _paper_analysis_rows(
    db: AsyncSession,
    paper_id: int,
) -> list[tuple[AnalysisResult, Keyword, str | None]]:
    result = await db.execute(
        select(AnalysisResult, Keyword, Feed.journal_name)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .join(Paper, AnalysisResult.paper_id == Paper.id)
        .outerjoin(Feed, Paper.feed_id == Feed.id)
        .where(AnalysisResult.paper_id == paper_id)
        .order_by(desc(AnalysisResult.relevance_score))
    )
    return list(result.all())


def _extract_knowledge_id(response: dict) -> str:
    data = response.get("data") if isinstance(response, dict) else None
    if isinstance(data, dict):
        return str(data.get("id") or "")
    return ""


async def sync_report_to_weknora(
    db: AsyncSession,
    report_id: int,
    *,
    client: ManualKnowledgeClient | None = None,
) -> WeKnoraSync | None:
    config = await get_weknora_config(db)
    if not is_weknora_ready(config) or not config.get("sync_reports", True):
        return None

    existing = await find_successful_sync(db, sync_type="report", report_id=report_id)
    if existing:
        return existing

    report = await db.get(Report, report_id)
    if not report:
        raise ValueError("Report not found")

    sync = WeKnoraSync(report_id=report.id, sync_type="report", status="pending")
    db.add(sync)
    await db.flush()

    try:
        wk_client = client or build_weknora_client(config)
        response = await wk_client.create_manual_knowledge(
            str(config["knowledge_base_id"]),
            report.title,
            report.markdown or "",
            channel="api",
        )
        sync.weknora_knowledge_id = _extract_knowledge_id(response)
        sync.status = "success"
        sync.synced_at = utc_now()
    except Exception as exc:
        sync.status = "failed"
        sync.error_message = str(exc)

    await db.commit()
    await db.refresh(sync)
    return sync


async def sync_paper_to_weknora(
    db: AsyncSession,
    paper_id: int,
    *,
    client: ManualKnowledgeClient | None = None,
) -> WeKnoraSync | None:
    config = await get_weknora_config(db)
    if not is_weknora_ready(config) or not config.get("sync_papers", True):
        return None

    existing = await find_successful_sync(db, sync_type="paper", paper_id=paper_id)
    if existing:
        return existing

    paper = await db.get(Paper, paper_id)
    if not paper:
        raise ValueError("Paper not found")

    rows = await _paper_analysis_rows(db, paper_id)
    best_score = max((float(row[0].relevance_score or 0) for row in rows), default=0.0)
    if best_score < float(config.get("min_score_to_sync", 0) or 0):
        return None

    sync = WeKnoraSync(paper_id=paper.id, sync_type="paper", status="pending")
    db.add(sync)
    await db.flush()

    try:
        wk_client = client or build_weknora_client(config)
        response = await wk_client.create_manual_knowledge(
            str(config["knowledge_base_id"]),
            clean_text(paper.title),
            render_paper_markdown(paper, rows),
            channel="api",
        )
        sync.weknora_knowledge_id = _extract_knowledge_id(response)
        sync.status = "success"
        sync.synced_at = utc_now()
    except Exception as exc:
        sync.status = "failed"
        sync.error_message = str(exc)

    await db.commit()
    await db.refresh(sync)
    return sync


async def sync_papers_to_weknora(db: AsyncSession, paper_ids: list[int]) -> list[WeKnoraSync]:
    syncs = []
    for paper_id in paper_ids:
        sync = await sync_paper_to_weknora(db, paper_id)
        if sync:
            syncs.append(sync)
    return syncs
