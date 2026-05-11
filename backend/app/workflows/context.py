import json
import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkflowExecution, WorkflowExecutionLog


class WorkflowCancelled(Exception):
    pass


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


class WorkflowContext:
    def __init__(self, db: AsyncSession, execution: WorkflowExecution):
        self.db = db
        self.execution = execution
        self.current_node = "workflow"
        self.summary: dict[str, Any] = {}
        self.state: dict[str, Any] = {}

    async def update_summary(self, values: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        latest_summary = self.execution.summary_dict
        merged = {**self.summary, **latest_summary}
        merged.update(values or {})
        merged.update(kwargs)
        self.summary = merged
        self.execution.summary_json = to_json(self.summary)
        self.db.add(self.execution)
        await self.db.commit()
        return self.summary

    async def wait_if_paused_or_cancelled(self, poll_interval: float = 1.0) -> None:
        while True:
            await self.db.refresh(self.execution)
            latest_summary = self.execution.summary_dict
            self.summary = {**self.summary, **latest_summary}
            control = str(latest_summary.get("execution_control", "running"))

            if control in {"cancel_requested", "cancelled"}:
                self.execution.status = "cancelled"
                await self.update_summary(
                    execution_control="cancelled",
                    literature_summary="文献汇总分析已取消。",
                )
                await self.log("warning", "Workflow cancelled by user")
                raise WorkflowCancelled("用户已取消分析")

            if control in {"pause_requested", "paused"}:
                if self.execution.status != "paused" or control != "paused":
                    self.execution.status = "paused"
                    await self.update_summary(
                        execution_control="paused",
                        literature_summary="文献汇总分析已暂停，可继续或取消。",
                    )
                    await self.log("warning", "Workflow paused by user")
                await asyncio.sleep(poll_interval)
                continue

            if self.execution.status == "paused":
                self.execution.status = "running"
                await self.update_summary(execution_control="running")
                await self.log("info", "Workflow resumed by user")

            return

    async def log(
        self,
        level: str,
        message: str,
        data: dict[str, Any] | None = None,
        node_name: str | None = None,
    ) -> WorkflowExecutionLog:
        log = WorkflowExecutionLog(
            execution_id=self.execution.id,
            node_name=node_name or self.current_node,
            level=level,
            message=message,
            data_json=to_json(data or {}),
        )
        self.db.add(log)
        await self.db.commit()
        return log
