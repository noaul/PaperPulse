from .base import WorkflowNode
from ..context import WorkflowContext
from ...services.ai_analyzer import analyze_new_papers


class AiAnalyzeNode(WorkflowNode):
    def __init__(self):
        super().__init__("ai-analyze")

    async def run(self, context: WorkflowContext) -> None:
        async def on_progress(progress: dict) -> None:
            await context.update_summary(progress)

        paper_ids = None
        if "fetched_paper_ids" in context.state:
            paper_ids = context.state["fetched_paper_ids"]

        results = await analyze_new_papers(
            context.db,
            progress_callback=on_progress,
            control_callback=context.wait_if_paused_or_cancelled,
            paper_ids=paper_ids,
            workspace_id=context.workspace_id,
            raise_errors=True,
        )
        analyzed = int(context.summary.get("analysis_analyzed", 0))
        total = int(context.summary.get("analysis_total", analyzed))
        related = int(context.summary.get("analysis_related", 0))
        literature_summary = f"本次共分析 {analyzed}/{total} 篇论文，其中 {related} 篇与主题词相关。"
        await context.update_summary(
            analyses=len(results),
            analyzed=analyzed,
            analysis_results=len(results),
            literature_summary=literature_summary,
        )
        await context.log(
            "info",
            f"Analysis progress {analyzed}/{total}, related {related}",
            {
                "analysis_total": total,
                "analysis_analyzed": analyzed,
                "analysis_related": related,
                "analysis_results": len(results),
            },
        )
