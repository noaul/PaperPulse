from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Paper, Feed, AnalysisResult, Keyword
from ..schemas import PaperOut
from typing import Optional

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("", response_model=list[PaperOut])
async def list_papers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    feed_id: Optional[int] = None,
    keyword: Optional[str] = None,
    min_score: Optional[float] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Paper, Feed.journal_name).outerjoin(Feed, Paper.feed_id == Feed.id)

    if feed_id:
        query = query.where(Paper.feed_id == feed_id)
    if search:
        query = query.where(Paper.title.ilike(f"%{search}%") | Paper.abstract.ilike(f"%{search}%"))

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

        if min_score is not None and (po.relevance_score or 0) < min_score:
            continue

        papers.append(po)

    return papers


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
