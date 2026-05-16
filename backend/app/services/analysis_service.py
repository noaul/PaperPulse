"""Service layer for analysis-related business logic."""
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AnalysisResult, Paper, Keyword, ReadingQueueItem
from .rss_fetcher import clean_text, normalize_paper_url


async def add_analysis_to_reading_queue(
    db: AsyncSession,
    analysis_id: int,
    workspace_id: int,
) -> ReadingQueueItem:
    """Add an analysis result to the reading queue. Returns the queue item."""
    result = await db.execute(
        select(AnalysisResult, Paper, Keyword)
        .join(Paper, AnalysisResult.paper_id == Paper.id)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .where(AnalysisResult.id == analysis_id, AnalysisResult.workspace_id == workspace_id)
    )
    row = result.first()
    if not row:
        raise ValueError("Analysis result not found")

    analysis, paper, keyword = row
    normalized_url = normalize_paper_url(paper.url)

    # Check for existing item
    existing_query = select(ReadingQueueItem).where(ReadingQueueItem.workspace_id == workspace_id)
    if normalized_url:
        existing_query = existing_query.where(ReadingQueueItem.url == normalized_url)
    else:
        existing_query = existing_query.where(ReadingQueueItem.title == clean_text(paper.title))

    existing = (await db.execute(existing_query)).scalar_one_or_none()
    if existing:
        tags = existing.tags
        if keyword.word not in tags:
            existing.set_tags([*tags, keyword.word])
            db.add(existing)
            await db.commit()
            await db.refresh(existing)
        return existing

    item = ReadingQueueItem(
        title=clean_text(paper.title),
        workspace_id=workspace_id,
        url=normalized_url,
        abstract=clean_text(paper.abstract),
        notes=(
            f"来自 AI 分析结果 #{analysis.id}。"
            f"相关性 {analysis.relevance_score:.1f}。"
            f"{analysis.summary or ''}"
        ).strip(),
        status="unread",
    )
    item.set_tags([keyword.word])
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
