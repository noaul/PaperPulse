from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import AnalysisResult, Paper, Keyword, Feed, ReadingQueueItem
from ..schemas import AnalysisOut, ReadingQueueItemOut
from .reading_queue import item_out
from ..services.rss_fetcher import clean_text, normalize_paper_url
from ..workflows.daily import (
    create_analysis_workflow_execution,
    create_fetch_analyze_workflow_execution,
    run_analysis_workflow,
    run_analysis_workflow_execution,
    run_fetch_analyze_workflow,
    run_fetch_analyze_workflow_execution,
    run_send_report_workflow,
)
from typing import Optional

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("")
async def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_score: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
):
    count_query = select(func.count(AnalysisResult.id))
    if min_score is not None:
        count_query = count_query.where(AnalysisResult.relevance_score >= min_score)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        select(
            AnalysisResult,
            Paper.title,
            Paper.abstract,
            Paper.authors,
            Paper.url,
            Feed.journal_name,
            Keyword.word,
        )
        .join(Paper, AnalysisResult.paper_id == Paper.id)
        .outerjoin(Feed, Paper.feed_id == Feed.id)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .order_by(desc(AnalysisResult.analyzed_at), desc(AnalysisResult.relevance_score))
    )
    if min_score is not None:
        query = query.where(AnalysisResult.relevance_score >= min_score)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()
    out = []
    for ar, title, abstract, authors, url, journal_name, word in rows:
        ao = AnalysisOut.model_validate(ar)
        ao.paper_title = clean_text(title)
        ao.paper_abstract = clean_text(abstract)
        ao.paper_authors = clean_text(authors)
        ao.paper_url = normalize_paper_url(url)
        ao.journal_name = journal_name
        ao.keyword_word = word
        out.append(ao)
    import math
    return {
        "items": out,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


@router.post("/run")
async def run_analysis(db: AsyncSession = Depends(get_db)):
    execution = await run_analysis_workflow(db)
    summary = execution.summary_dict
    return {
        "success": execution.status == "success",
        "analyzed": summary.get("analyzed", 0),
        "execution_id": execution.id,
        "status": execution.status,
    }


@router.post("/run-background")
async def run_analysis_background(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    execution = await create_analysis_workflow_execution(db)
    background_tasks.add_task(run_analysis_workflow_execution, execution.id)
    return {
        "success": True,
        "analyzed": 0,
        "execution_id": execution.id,
        "status": execution.status,
        "summary": execution.summary_dict,
    }


@router.post("/fetch-and-analyze")
async def fetch_and_analyze(db: AsyncSession = Depends(get_db)):
    execution = await run_fetch_analyze_workflow(db)
    summary = execution.summary_dict
    return {
        "success": execution.status == "success",
        "new_papers": summary.get("new_papers", 0),
        "analyses": summary.get("analyses", 0),
        "execution_id": execution.id,
        "status": execution.status,
    }


@router.post("/fetch-and-analyze-background")
async def fetch_and_analyze_background(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    execution = await create_fetch_analyze_workflow_execution(db)
    background_tasks.add_task(run_fetch_analyze_workflow_execution, execution.id)
    return {
        "success": True,
        "new_papers": 0,
        "analyses": 0,
        "execution_id": execution.id,
        "status": execution.status,
        "summary": execution.summary_dict,
    }


@router.post("/send-report")
async def send_report(db: AsyncSession = Depends(get_db)):
    execution = await run_send_report_workflow(db)
    summary = execution.summary_dict
    return {
        "success": execution.status == "success" and bool(summary.get("email_sent")),
        "execution_id": execution.id,
        "status": execution.status,
        "skipped": bool(summary.get("email_skipped")),
        "message": summary.get("email_reason", ""),
        "paper_count": summary.get("email_paper_count", 0),
    }


@router.post("/{analysis_id}/add-to-reading-queue", response_model=ReadingQueueItemOut)
async def add_analysis_to_reading_queue(analysis_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AnalysisResult, Paper, Keyword)
        .join(Paper, AnalysisResult.paper_id == Paper.id)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .where(AnalysisResult.id == analysis_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Analysis result not found")

    analysis, paper, keyword = row
    normalized_url = normalize_paper_url(paper.url)
    existing_query = select(ReadingQueueItem)
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
        return item_out(existing)

    item = ReadingQueueItem(
        title=clean_text(paper.title),
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
    return item_out(item)
