import json

from sqlalchemy import select

from .base import WorkflowNode
from ..context import WorkflowContext
from ...models import Setting
from ...services.email_sender import send_daily_report


async def get_relevance_threshold(context: WorkflowContext) -> float:
    result = await context.db.execute(select(Setting).where(Setting.key == "schedule_config"))
    row = result.scalar_one_or_none()
    if not row:
        return 6.0
    try:
        return float(json.loads(row.value).get("relevance_threshold", 6.0))
    except Exception:
        return 6.0


class EmailReportNode(WorkflowNode):
    def __init__(self):
        super().__init__("email-report")

    async def run(self, context: WorkflowContext) -> None:
        threshold = await get_relevance_threshold(context)
        result = await send_daily_report(context.db, threshold=threshold)
        sent = bool(result.get("sent"))
        await context.update_summary(
            email_sent=sent,
            email_skipped=bool(result.get("skipped")),
            email_reason=result.get("reason", ""),
            email_paper_count=int(result.get("paper_count", 0)),
        )
        level = "info" if sent or result.get("skipped") else "warning"
        await context.log(level, "Email report completed" if sent else "Email report skipped or failed", {
            "threshold": threshold,
            **result,
        })
