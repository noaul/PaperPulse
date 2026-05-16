from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..dependencies import get_current_workspace
from ..models import Paper, Feed, AnalysisResult, Keyword, Workspace
from ..schemas import PaperOut
from ..services.rss_fetcher import clean_text, normalize_paper_url
from ..services.weknora_sync import sync_paper_to_weknora
from typing import Optional
import math

router = APIRouter(prefix="/api/papers", tags=["papers"])


# Subquery: best analysis score per paper in workspace
def _best_score_subquery(workspace_id: int):
    return (
        select(
            AnalysisResult.paper_id,
            func.max(AnalysisResult.relevance_score).label("best_score"),
        )
        .where(AnalysisResult.workspace_id == workspace_id)
        .group_by(AnalysisResult.paper_id)
        .subquery()
    )


@router.get("")
async def list_papers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    feed_id: Optional[int] = None,
    journal: Optional[str] = None,
    keyword: Optional[str] = None,
    min_score: Optional[float] = None,
    min_relevance: Optional[float] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    effective_min_score = min_score if min_score is not None else min_relevance
    best_score_sq = _best_score_subquery(workspace.id)

    # Base query with LEFT JOIN to get best score in one pass
    base = (
        select(
            Paper,
            Feed.journal_name,
            best_score_sq.c.best_score,
        )
        .outerjoin(Feed, Paper.feed_id == Feed.id)
        .outerjoin(best_score_sq, Paper.id == best_score_sq.c.paper_id)
        .where(Paper.workspace_id == workspace.id)
    )

    # Filters
    if feed_id:
        base = base.where(Paper.feed_id == feed_id)
    if journal:
        base = base.where(Feed.journal_name == journal)
    if search:
        base = base.where(Paper.title.ilike(f"%{search}%") | Paper.abstract.ilike(f"%{search}%"))
    if effective_min_score is not None:
        base = base.where(best_score_sq.c.best_score >= effective_min_score)
    if keyword:
        # Join through AnalysisResult+Keyword to filter by keyword match
        kw_exists = (
            select(AnalysisResult.paper_id)
            .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
            .where(
                AnalysisResult.workspace_id == workspace.id,
                Keyword.word.ilike(f"%{keyword}%"),
            )
        ).correlate(Paper)
        base = base.where(Paper.id.in_(kw_exists))

    # Count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = base.order_by(desc(Paper.fetched_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    # Get summaries for these papers in one batch
    paper_ids = [row[0].id for row in rows]
    summaries: dict[int, tuple[float, str]] = {}
    if paper_ids:
        ar_q = (
            select(AnalysisResult.paper_id, AnalysisResult.relevance_score, AnalysisResult.summary)
            .where(
                AnalysisResult.workspace_id == workspace.id,
                AnalysisResult.paper_id.in_(paper_ids),
            )
            .order_by(AnalysisResult.paper_id, desc(AnalysisResult.relevance_score))
        )
        ar_rows = (await db.execute(ar_q)).all()
        for paper_id, score, summary in ar_rows:
            if paper_id not in summaries:
                summaries[paper_id] = (score, summary)

    papers = []
    for paper, journal_name, best_score in rows:
        po = PaperOut.model_validate(paper)
        po.title = clean_text(po.title)
        po.authors = clean_text(po.authors)
        po.abstract = clean_text(po.abstract)
        po.url = normalize_paper_url(po.url)
        po.journal_name = journal_name
        if paper.id in summaries:
            po.relevance_score = summaries[paper.id][0]
            po.analysis_summary = summaries[paper.id][1]
        elif best_score is not None:
            po.relevance_score = best_score
        papers.append(po)

    return {
        "items": papers,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


@router.get("/{paper_id}", response_model=PaperOut)
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    result = await db.execute(
        select(Paper, Feed.journal_name)
        .outerjoin(Feed)
        .where(Paper.id == paper_id, Paper.workspace_id == workspace.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Paper not found")
    paper, journal_name = row
    po = PaperOut.model_validate(paper)
    po.title = clean_text(po.title)
    po.authors = clean_text(po.authors)
    po.abstract = clean_text(po.abstract)
    po.url = normalize_paper_url(po.url)
    po.journal_name = journal_name
    ar_result = await db.execute(
        select(AnalysisResult.relevance_score, AnalysisResult.summary)
        .where(AnalysisResult.paper_id == paper.id, AnalysisResult.workspace_id == workspace.id)
        .order_by(desc(AnalysisResult.relevance_score))
        .limit(1)
    )
    ar_row = ar_result.first()
    if ar_row:
        po.relevance_score = ar_row[0]
        po.analysis_summary = ar_row[1]
    return po


@router.post("/{paper_id}/sync-weknora")
async def sync_paper_weknora(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    try:
        sync = await sync_paper_to_weknora(db, paper_id, workspace_id=workspace.id)
    except ValueError:
        raise HTTPException(404, "Paper not found")
    if not sync:
        return {"success": True, "synced": False, "reason": "WeKnora 未启用或论文未达到同步阈值"}
    return {
        "success": sync.status == "success",
        "synced": sync.status == "success",
        "status": sync.status,
        "weknora_knowledge_id": sync.weknora_knowledge_id,
        "error_message": sync.error_message,
    }



@router.post("/enrich-abstracts")
async def enrich_abstracts(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    from ..services.abstract_enrichment import enrich_recent_papers
    enriched = await enrich_recent_papers(db, workspace.id, limit=limit)
    return {"success": True, "enriched_count": enriched}
