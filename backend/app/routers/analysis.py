from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import AnalysisResult, Paper, Keyword
from ..schemas import AnalysisOut
from ..services.ai_analyzer import analyze_new_papers
from ..services.email_sender import send_daily_report
from ..services.rss_fetcher import fetch_all_feeds
from typing import Optional

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("", response_model=list[AnalysisOut])
async def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_score: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AnalysisResult, Paper.title, Keyword.word)
        .join(Paper, AnalysisResult.paper_id == Paper.id)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .order_by(desc(AnalysisResult.analyzed_at), desc(AnalysisResult.relevance_score))
    )
    if min_score is not None:
        query = query.where(AnalysisResult.relevance_score >= min_score)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()
    out = []
    for ar, title, word in rows:
        ao = AnalysisOut.model_validate(ar)
        ao.paper_title = title
        ao.keyword_word = word
        out.append(ao)
    return out


@router.post("/run")
async def run_analysis(db: AsyncSession = Depends(get_db)):
    results = await analyze_new_papers(db)
    return {"success": True, "analyzed": len(results)}


@router.post("/fetch-and-analyze")
async def fetch_and_analyze(db: AsyncSession = Depends(get_db)):
    papers = await fetch_all_feeds(db)
    results = await analyze_new_papers(db)
    return {"success": True, "new_papers": len(papers), "analyses": len(results)}


@router.post("/send-report")
async def send_report(db: AsyncSession = Depends(get_db)):
    sent = await send_daily_report(db)
    return {"success": sent}
