from .base import WorkflowNode
from ..context import WorkflowContext
from ...services.rss_fetcher import fetch_all_feeds


class FetchRssNode(WorkflowNode):
    def __init__(self):
        super().__init__("fetch-rss")

    async def run(self, context: WorkflowContext) -> None:
        papers = await fetch_all_feeds(context.db)
        paper_ids = [paper.id for paper in papers if paper.id is not None]
        context.state["fetched_paper_ids"] = paper_ids
        await context.update_summary(
            new_papers=len(papers),
            analysis_total=len(papers),
            analysis_analyzed=0,
            analysis_related=0,
            analysis_results=0,
            analysis_current_title="",
        )
        await context.log("info", f"Fetched {len(papers)} new papers", {"new_papers": len(papers)})
