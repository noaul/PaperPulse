from .base import WorkflowNode
from ..context import WorkflowContext
from ...services.email_sender import send_daily_report


class EmailReportNode(WorkflowNode):
    def __init__(self):
        super().__init__("email-report")

    async def run(self, context: WorkflowContext) -> None:
        paper_ids = context.state.get("fetched_paper_ids")
        result = await send_daily_report(
            context.db,
            paper_ids=paper_ids,
            analyzed_count=int(context.summary.get("analysis_analyzed", 0)),
            related_count=int(context.summary.get("analysis_related", 0)),
            workspace_id=context.workspace_id,
        )
        sent = bool(result.get("sent"))
        await context.update_summary(
            email_report_id=result.get("report_id"),
            email_sent=sent,
            email_skipped=bool(result.get("skipped")),
            email_reason=result.get("reason", ""),
            email_paper_count=int(result.get("paper_count", 0)),
            email_sent_count=int(result.get("sent_count", 1 if sent else 0)),
            email_topic_reports=result.get("topic_reports", []),
        )
        level = "info" if sent or result.get("skipped") else "warning"
        await context.log(level, "Email report completed" if sent else "Email report skipped or failed", {
            **result,
        })
