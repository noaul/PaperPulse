from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Paper, Feed, AnalysisResult, Keyword
from ..schemas import PaperOut
from typing import Optional
import math

router = APIRouter(prefix="/api/papers", tags=["papers"])


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
):
    effective_min_score = min_score if min_score is not None else min_relevance

    # Build base query
    query = select(Paper, Feed.journal_name).outerjoin(Feed, Paper.feed_id == Feed.id)

    if feed_id:
        query = query.where(Paper.feed_id == feed_id)
    if journal:
        query = query.where(Feed.journal_name == journal)
    if search:
        query = query.where(Paper.title.ilike(f"%{search}%") | Paper.abstract.ilike(f"%{search}%"))

    # If keyword or min_score filters are used, fetch a larger set and filter in Python
    needs_post_filter = keyword or effective_min_score is not None
    if needs_post_filter:
        # Fetch enough rows to fill multiple pages after filtering
        fetch_limit = page * page_size * 5
        query = query.order_by(desc(Paper.fetched_at)).limit(fetch_limit)
    else:
        # Count total for simple queries
        count_query = select(func.count(Paper.id))
        if feed_id:
            count_query = count_query.where(Paper.feed_id == feed_id)
        if journal:
            count_query = count_query.select_from(Paper).outerjoin(Feed, Paper.feed_id == Feed.id)
            count_query = count_query.where(Feed.journal_name == journal)
        if search:
            count_query = count_query.where(
                Paper.title.ilike(f"%{search}%") | Paper.abstract.ilike(f"%{search}%")
            )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(desc(Paper.fetched_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    papers = []
    for paper, journal_name in rows:
        po = PaperOut.model_validate(paper)
        po.journal_name = journal_name

        # Get best analysis score
        ar_result = await db.execute(
            select(AnalysisResult, Keyword.word)
            .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
            .where(AnalysisResult.paper_id == paper.id)
            .order_by(desc(AnalysisResult.relevance_score))
            .limit(1)
        )
        ar_row = ar_result.first()
        if ar_row:
            po.relevance_score = ar_row[0].relevance_score
            po.analysis_summary = ar_row[0].summary

        if keyword:
            kw_result = await db.execute(
                select(AnalysisResult).join(Keyword).where(
                    AnalysisResult.paper_id == paper.id,
                    Keyword.word.ilike(f"%{keyword}%"),
                )
            )
            if not kw_result.first():
                continue

        if effective_min_score is not None and (po.relevance_score or 0) < effective_min_score:
            continue

        papers.append(po)

    if needs_post_filter:
        total = len(papers)
        start = (page - 1) * page_size
        papers = papers[start:start + page_size]

    pages = max(1, math.ceil(total / page_size))

    return {
        "items": papers,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/{paper_id}", response_model=PaperOut)
async def get_paper(paper_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Paper, Feed.journal_name).outerjoin(Feed).where(Paper.id == paper_id))
    row = result.first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Paper not found")
    paper, journal_name = row
    po = PaperOut.model_validate(paper)
    po.journal_name = journal_name
    ar_result = await db.execute(
        select(AnalysisResult, Keyword.word)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .where(AnalysisResult.paper_id == paper.id)
        .order_by(desc(AnalysisResult.relevance_score))
        .limit(1)
    )
    ar_row = ar_result.first()
    if ar_row:
        po.relevance_score = ar_row[0].relevance_score
        po.analysis_summary = ar_row[0].summary
    return po
