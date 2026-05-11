from .base import WorkflowNode
from ..context import WorkflowContext
from ...services.weknora_sync import sync_papers_to_weknora, sync_report_to_weknora


class WeKnoraSyncNode(WorkflowNode):
    def __init__(self):
        super().__init__("weknora-sync")

    async def run(self, context: WorkflowContext) -> None:
        report_sync = None
        report_id = context.summary.get("email_report_id")
        if report_id:
            report_sync = await sync_report_to_weknora(context.db, int(report_id))

        paper_ids = context.state.get("fetched_paper_ids") or []
        paper_syncs = await sync_papers_to_weknora(context.db, list(paper_ids))

        reports_synced = 1 if report_sync and report_sync.status == "success" else 0
        papers_synced = sum(1 for sync in paper_syncs if sync.status == "success")
        failures = sum(1 for sync in paper_syncs if sync.status == "failed")
        if report_sync and report_sync.status == "failed":
            failures += 1

        await context.update_summary(
            weknora_reports_synced=reports_synced,
            weknora_papers_synced=papers_synced,
            weknora_sync_failures=failures,
        )

        level = "warning" if failures else "info"
        await context.log(level, "WeKnora sync completed", {
            "reports_synced": reports_synced,
            "papers_synced": papers_synced,
            "failures": failures,
        })
