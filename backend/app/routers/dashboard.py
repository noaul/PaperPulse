from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from ..database import get_db
from ..dependencies import get_current_workspace
from ..models import Paper, Feed, AnalysisResult, Keyword, Workspace
from ..schemas import DashboardStats, RecentPaperOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Total feeds
    result = await db.execute(select(func.count(Feed.id)).where(Feed.workspace_id == workspace.id))
    total_feeds = result.scalar() or 0

    # Total papers
    result = await db.execute(select(func.count(Paper.id)).where(Paper.workspace_id == workspace.id))
    total_papers = result.scalar() or 0

    # Today's papers
    result = await db.execute(
        select(func.count(Paper.id)).where(Paper.fetched_at >= today_start, Paper.workspace_id == workspace.id)
    )
    today_papers = result.scalar() or 0

    # Today's analyses
    result = await db.execute(
        select(func.count(AnalysisResult.id)).where(
            AnalysisResult.analyzed_at >= today_start,
            AnalysisResult.workspace_id == workspace.id,
        )
    )
    today_analyses = result.scalar() or 0

    # High relevance today (score >= 6)
    result = await db.execute(
        select(func.count(func.distinct(AnalysisResult.paper_id)))
        .where(AnalysisResult.analyzed_at >= today_start)
        .where(AnalysisResult.relevance_score >= 6.0)
        .where(AnalysisResult.workspace_id == workspace.id)
    )
    high_relevance_today = result.scalar() or 0

    # Total keywords
    result = await db.execute(select(func.count(Keyword.id)).where(Keyword.workspace_id == workspace.id))
    total_keywords = result.scalar() or 0

    return DashboardStats(
        total_feeds=total_feeds,
        total_papers=total_papers,
        total_keywords=total_keywords,
        today_papers=today_papers,
        today_analyses=today_analyses,
        high_relevance_today=high_relevance_today,
    )


@router.get("/recent-high-relevance", response_model=list[RecentPaperOut])
async def get_recent_high_relevance(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    # Get papers with highest relevance score, most recent first
    query = (
        select(
            Paper.id,
            Paper.title,
            Feed.journal_name,
            func.max(AnalysisResult.relevance_score).label("relevance_score"),
            Paper.published_at,
        )
        .outerjoin(Feed, Paper.feed_id == Feed.id)
        .join(AnalysisResult, AnalysisResult.paper_id == Paper.id)
        .where(Paper.workspace_id == workspace.id, AnalysisResult.workspace_id == workspace.id)
        .group_by(Paper.id)
        .having(func.max(AnalysisResult.relevance_score) >= 5.0)
        .order_by(desc("relevance_score"), desc(Paper.fetched_at))
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    papers = []
    for pid, title, journal_name, score, published_at in rows:
        papers.append(RecentPaperOut(
            id=pid,
            title=title,
            journal=journal_name,
            relevance_score=score,
            published_date=published_at.strftime("%Y-%m-%d") if published_at else None,
        ))

    return papers



@router.get("/chart-data")
async def get_chart_data(
    days: int = Query(14, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Return daily aggregated data for dashboard charts."""
    from sqlalchemy import cast, Date
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    # Daily new papers
    paper_q = await db.execute(
        select(
            cast(Paper.fetched_at, Date).label("day"),
            func.count(Paper.id),
        )
        .where(Paper.workspace_id == workspace.id, Paper.fetched_at >= cutoff)
        .group_by("day")
        .order_by("day")
    )
    daily_papers = {str(row[0]): row[1] for row in paper_q.all()}

    # Daily analyses
    analysis_q = await db.execute(
        select(
            cast(AnalysisResult.analyzed_at, Date).label("day"),
            func.count(AnalysisResult.id),
            func.count(func.distinct(AnalysisResult.paper_id)),
        )
        .where(AnalysisResult.workspace_id == workspace.id, AnalysisResult.analyzed_at >= cutoff)
        .group_by("day")
        .order_by("day")
    )
    daily_analyses = {}
    daily_related = {}
    for row in analysis_q.all():
        daily_analyses[str(row[0])] = row[1]
        daily_related[str(row[0])] = row[2]

    # Build date series
    dates = []
    for i in range(days):
        d = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        dates.append(d)

    # Total papers cumulative
    total_before = (await db.execute(
        select(func.count(Paper.id)).where(Paper.workspace_id == workspace.id, Paper.fetched_at < cutoff)
    )).scalar() or 0

    cumulative = []
    running = total_before
    for d in dates:
        running += daily_papers.get(d, 0)
        cumulative.append(running)

    return {
        "dates": dates,
        "daily_new_papers": [daily_papers.get(d, 0) for d in dates],
        "daily_analyses": [daily_analyses.get(d, 0) for d in dates],
        "daily_related_papers": [daily_related.get(d, 0) for d in dates],
        "cumulative_papers": cumulative,
    }
