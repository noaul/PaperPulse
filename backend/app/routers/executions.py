from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_workspace
from ..models import WorkflowExecution, WorkflowExecutionLog, Workspace
from ..schemas import WorkflowExecutionDetail, WorkflowExecutionLogOut, WorkflowExecutionOut
from ..workflows.context import to_json

router = APIRouter(prefix="/api/executions", tags=["executions"])

ACTIVE_STATUSES = {"running", "paused", "pending"}
TERMINAL_STATUSES = {"success", "failed", "cancelled"}


def execution_out(execution: WorkflowExecution) -> WorkflowExecutionOut:
    return WorkflowExecutionOut(
        id=execution.id,
        workflow_name=execution.workflow_name,
        status=execution.status,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        duration_ms=execution.duration_ms,
        summary=execution.summary_dict,
        error_message=execution.error_message,
    )


def log_out(log: WorkflowExecutionLog) -> WorkflowExecutionLogOut:
    return WorkflowExecutionLogOut(
        id=log.id,
        execution_id=log.execution_id,
        node_name=log.node_name,
        level=log.level,
        message=log.message,
        data=log.data_dict,
        created_at=log.created_at,
    )


async def set_execution_control(
    db: AsyncSession,
    execution_id: int,
    action: str,
    workspace_id: int | None = None,
) -> WorkflowExecution:
    execution = await db.get(WorkflowExecution, execution_id)
    if not execution or (workspace_id is not None and execution.workspace_id != workspace_id):
        raise HTTPException(404, "Execution not found")

    if execution.status in TERMINAL_STATUSES and not (action == "cancel" and execution.status == "cancelled"):
        raise HTTPException(400, "Execution already finished")

    summary = execution.summary_dict
    if action == "pause":
        if execution.status not in ACTIVE_STATUSES:
            raise HTTPException(400, "Only active executions can be paused")
        execution.status = "paused"
        summary["execution_control"] = "pause_requested"
        summary["literature_summary"] = "文献汇总分析暂停请求已发送，当前论文处理完后暂停。"
    elif action == "resume":
        if execution.status != "paused":
            raise HTTPException(400, "Only paused executions can be resumed")
        execution.status = "running"
        summary["execution_control"] = "running"
        summary["literature_summary"] = "文献汇总分析已继续。"
    elif action == "cancel":
        if execution.status not in ACTIVE_STATUSES and execution.status != "cancelled":
            raise HTTPException(400, "Only active executions can be cancelled")
        execution.status = "cancelled"
        summary["execution_control"] = "cancel_requested"
        summary["literature_summary"] = "文献汇总分析取消请求已发送。"
    else:
        raise HTTPException(400, "Unsupported execution control action")

    execution.summary_json = to_json(summary)
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return execution


@router.get("", response_model=list[WorkflowExecutionOut])
async def list_executions(
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    query = (
        select(WorkflowExecution)
        .where(WorkflowExecution.workspace_id == workspace.id)
        .order_by(desc(WorkflowExecution.started_at))
        .limit(limit)
    )
    if status:
        query = query.where(WorkflowExecution.status == status)
    result = await db.execute(query)
    return [execution_out(row) for row in result.scalars().all()]


@router.get("/{execution_id}", response_model=WorkflowExecutionDetail)
async def get_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    execution = await db.get(WorkflowExecution, execution_id)
    if not execution or execution.workspace_id != workspace.id:
        raise HTTPException(404, "Execution not found")

    logs_result = await db.execute(
        select(WorkflowExecutionLog)
        .where(WorkflowExecutionLog.execution_id == execution_id)
        .order_by(WorkflowExecutionLog.created_at, WorkflowExecutionLog.id)
    )
    base = execution_out(execution).model_dump()
    return WorkflowExecutionDetail(**base, logs=[log_out(log) for log in logs_result.scalars().all()])


@router.get("/{execution_id}/logs", response_model=list[WorkflowExecutionLogOut])
async def list_execution_logs(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    execution = await db.get(WorkflowExecution, execution_id)
    if not execution or execution.workspace_id != workspace.id:
        raise HTTPException(404, "Execution not found")

    result = await db.execute(
        select(WorkflowExecutionLog)
        .where(WorkflowExecutionLog.execution_id == execution_id)
        .order_by(WorkflowExecutionLog.created_at, WorkflowExecutionLog.id)
    )
    return [log_out(log) for log in result.scalars().all()]


@router.post("/{execution_id}/pause", response_model=WorkflowExecutionOut)
async def pause_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    execution = await set_execution_control(db, execution_id, "pause", workspace_id=workspace.id)
    return execution_out(execution)


@router.post("/{execution_id}/resume", response_model=WorkflowExecutionOut)
async def resume_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    execution = await set_execution_control(db, execution_id, "resume", workspace_id=workspace.id)
    return execution_out(execution)


@router.post("/{execution_id}/cancel", response_model=WorkflowExecutionOut)
async def cancel_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    execution = await set_execution_control(db, execution_id, "cancel", workspace_id=workspace.id)
    return execution_out(execution)
