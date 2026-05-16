from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkflowExecution
from .context import WorkflowCancelled, WorkflowContext, to_json
from .nodes.base import WorkflowNode


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def duration_ms(start: datetime, end: datetime) -> int:
    if start.tzinfo is None and end.tzinfo is not None:
        start = start.replace(tzinfo=end.tzinfo)
    elif end.tzinfo is None and start.tzinfo is not None:
        end = end.replace(tzinfo=start.tzinfo)
    return max(0, int((end - start).total_seconds() * 1000))


class WorkflowEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_execution(
        self,
        workflow_name: str,
        initial_summary: dict | None = None,
        workspace_id: int = 1,
    ) -> WorkflowExecution:
        execution = WorkflowExecution(
            workflow_name=workflow_name,
            workspace_id=workspace_id,
            status="running",
            started_at=utc_now(),
            summary_json=to_json(initial_summary or {}),
        )
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def run(
        self,
        workflow_name: str,
        nodes: Iterable[WorkflowNode],
        *,
        workspace_id: int = 1,
        raise_on_failure: bool = False,
    ) -> WorkflowExecution:
        execution = await self.create_execution(workflow_name, workspace_id=workspace_id)
        return await self.run_existing(execution.id, nodes, raise_on_failure=raise_on_failure)

    async def run_existing(
        self,
        execution_id: int,
        nodes: Iterable[WorkflowNode],
        *,
        raise_on_failure: bool = False,
    ) -> WorkflowExecution:
        node_list = list(nodes)
        execution = await self.db.get(WorkflowExecution, execution_id)
        if not execution:
            raise ValueError(f"Workflow execution not found: {execution_id}")

        if not execution.started_at:
            execution.started_at = utc_now()
        execution.status = "running"
        execution.finished_at = None
        execution.duration_ms = None
        await self.db.commit()
        await self.db.refresh(execution)

        started_at = execution.started_at
        context = WorkflowContext(self.db, execution)
        context.summary.update(execution.summary_dict)
        await context.log(
            "info",
            "Workflow started",
            {"workflow": execution.workflow_name, "nodes": [node.name for node in node_list]},
            node_name="workflow",
        )

        try:
            for node in node_list:
                node_started_at = utc_now()
                context.current_node = node.name
                await context.log("info", f"Node {node.name} started", node_name=node.name)
                await node.run(context)
                node_finished_at = utc_now()
                await context.log(
                    "info",
                    f"Node {node.name} finished",
                    {"duration_ms": duration_ms(node_started_at, node_finished_at)},
                    node_name=node.name,
                )

            execution.status = "success"
            execution.summary_json = to_json(context.summary)
            await context.log("info", "Workflow finished", context.summary, node_name="workflow")
        except WorkflowCancelled as exc:
            execution.status = "cancelled"
            execution.error_message = str(exc)
            execution.summary_json = to_json({**context.summary, "execution_control": "cancelled"})
            await context.log(
                "warning",
                f"Workflow cancelled: {exc}",
                {"error_type": type(exc).__name__},
                node_name=context.current_node or "workflow",
            )
        except Exception as exc:
            execution.status = "failed"
            execution.error_message = str(exc)
            execution.summary_json = to_json(context.summary)
            await context.log(
                "error",
                f"Workflow failed: {exc}",
                {"error_type": type(exc).__name__},
                node_name=context.current_node or "workflow",
            )
            if raise_on_failure:
                raise
        finally:
            finished_at = utc_now()
            execution.finished_at = finished_at
            execution.duration_ms = duration_ms(started_at, finished_at)
            await self.db.commit()
            await self.db.refresh(execution)

        return execution
