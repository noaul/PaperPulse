from sqlalchemy.ext.asyncio import AsyncSession

from ..database import SessionLocal
from ..models import WorkflowExecution
from .engine import WorkflowEngine
from .nodes.ai_analyze import AiAnalyzeNode
from .nodes.email_report import EmailReportNode
from .nodes.fetch_rss import FetchRssNode
from .nodes.webdav_backup import WebdavBackupNode
from .nodes.weknora_sync import WeKnoraSyncNode


async def run_analysis_workflow(db: AsyncSession) -> WorkflowExecution:
    return await WorkflowEngine(db).run("manual-analysis", [AiAnalyzeNode()])


async def run_fetch_analyze_workflow(db: AsyncSession) -> WorkflowExecution:
    return await WorkflowEngine(db).run("manual-fetch-analyze", [FetchRssNode(), AiAnalyzeNode()])


async def run_send_report_workflow(db: AsyncSession) -> WorkflowExecution:
    return await WorkflowEngine(db).run("manual-send-report", [EmailReportNode()])


async def run_daily_workflow(db: AsyncSession) -> WorkflowExecution:
    return await WorkflowEngine(db).run(
        "daily-paperpulse",
        [FetchRssNode(), AiAnalyzeNode(), EmailReportNode(), WeKnoraSyncNode(), WebdavBackupNode()],
    )


def analysis_initial_summary() -> dict:
    return {
        "analysis_total": 0,
        "analysis_analyzed": 0,
        "analysis_related": 0,
        "analysis_results": 0,
        "analysis_current_title": "",
        "literature_summary": "",
        "execution_control": "running",
    }


async def create_analysis_workflow_execution(db: AsyncSession) -> WorkflowExecution:
    return await WorkflowEngine(db).create_execution("manual-analysis", analysis_initial_summary())


async def create_fetch_analyze_workflow_execution(db: AsyncSession) -> WorkflowExecution:
    return await WorkflowEngine(db).create_execution(
        "manual-fetch-analyze",
        {"new_papers": 0, **analysis_initial_summary()},
    )


async def run_analysis_workflow_execution(execution_id: int) -> None:
    async with SessionLocal() as db:
        await WorkflowEngine(db).run_existing(execution_id, [AiAnalyzeNode()])


async def run_fetch_analyze_workflow_execution(execution_id: int) -> None:
    async with SessionLocal() as db:
        await WorkflowEngine(db).run_existing(execution_id, [FetchRssNode(), AiAnalyzeNode()])
