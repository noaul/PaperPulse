from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..dependencies import get_current_workspace
from ..models import AnalysisResult, Paper, Keyword, Feed, Workspace
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
from ..rate_limit import limiter
from typing import Optional

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("")
async def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_score: Optional[float] = None,
    keyword_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    count_query = select(func.count(AnalysisResult.id)).where(AnalysisResult.workspace_id == workspace.id)
    if min_score is not None:
        count_query = count_query.where(AnalysisResult.relevance_score >= min_score)
    if keyword_id is not None:
        count_query = count_query.where(AnalysisResult.keyword_id == keyword_id)
    if keyword:
        count_query = count_query.join(Keyword, AnalysisResult.keyword_id == Keyword.id).where(Keyword.word.ilike(f"%{keyword}%"))
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
        .where(AnalysisResult.workspace_id == workspace.id)
        .order_by(desc(AnalysisResult.analyzed_at), desc(AnalysisResult.relevance_score))
    )
    if min_score is not None:
        query = query.where(AnalysisResult.relevance_score >= min_score)
    if keyword_id is not None:
        query = query.where(AnalysisResult.keyword_id == keyword_id)
    if keyword:
        query = query.where(Keyword.word.ilike(f"%{keyword}%"))
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
async def run_analysis(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    execution = await run_analysis_workflow(db, workspace_id=workspace.id)
    summary = execution.summary_dict
    return {
        "success": execution.status == "success",
        "analyzed": summary.get("analyzed", 0),
        "execution_id": execution.id,
        "status": execution.status,
    }


@router.post("/run-background")
@limiter.limit("5/minute")
async def run_analysis_background(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    execution = await create_analysis_workflow_execution(db, workspace_id=workspace.id)
    background_tasks.add_task(run_analysis_workflow_execution, execution.id)
    return {
        "success": True,
        "analyzed": 0,
        "execution_id": execution.id,
        "status": execution.status,
        "summary": execution.summary_dict,
    }


@router.post("/reanalyze")
async def reanalyze(
    days: int = Query(1, ge=1, le=30),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Re-analyze papers from the past N days, overwriting old results."""
    from datetime import datetime, timedelta, timezone
    from ..models import AnalysisResult as AR

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    # Find papers fetched in the last N days
    paper_result = await db.execute(
        select(Paper.id).where(
            Paper.workspace_id == workspace.id,
            Paper.fetched_at >= cutoff,
        )
    )
    paper_ids = [row[0] for row in paper_result.all()]
    if not paper_ids:
        return {"success": True, "message": f"过去{days}天内没有论文", "paper_count": 0}

    # Delete existing analysis results for these papers
    from sqlalchemy import delete
    await db.execute(
        delete(AR).where(AR.workspace_id == workspace.id, AR.paper_id.in_(paper_ids))
    )
    await db.commit()

    # Create execution and run in background
    execution = await create_analysis_workflow_execution(db, workspace_id=workspace.id)
    # Store paper_ids in summary so the node picks them up
    import json
    execution.summary_json = json.dumps({
        **execution.summary_dict,
        "target_paper_ids": paper_ids,
    })
    await db.commit()

    background_tasks.add_task(run_analysis_workflow_execution, execution.id)
    return {
        "success": True,
        "execution_id": execution.id,
        "paper_count": len(paper_ids),
        "days": days,
        "message": f"正在重新分析过去{days}天的{len(paper_ids)}篇论文",
    }


@router.post("/fetch-and-analyze")
async def fetch_and_analyze(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    execution = await run_fetch_analyze_workflow(db, workspace_id=workspace.id)
    summary = execution.summary_dict
    return {
        "success": execution.status == "success",
        "new_papers": summary.get("new_papers", 0),
        "analyses": summary.get("analyses", 0),
        "execution_id": execution.id,
        "status": execution.status,
    }


@router.post("/fetch-and-analyze-background")
@limiter.limit("5/minute")
async def fetch_and_analyze_background(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    execution = await create_fetch_analyze_workflow_execution(db, workspace_id=workspace.id)
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
async def send_report(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    execution = await run_send_report_workflow(db, workspace_id=workspace.id)
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
async def add_analysis_to_reading_queue(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    from ..services.analysis_service import add_analysis_to_reading_queue as svc_add
    try:
        item = await svc_add(db, analysis_id, workspace.id)
    except ValueError:
        raise HTTPException(404, "Analysis result not found")
    return item_out(item)
