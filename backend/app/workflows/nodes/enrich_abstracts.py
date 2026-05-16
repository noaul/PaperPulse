from .base import WorkflowNode
from ..context import WorkflowContext


class EnrichAbstractsNode(WorkflowNode):
    def __init__(self):
        super().__init__("enrich_abstracts")

    async def run(self, context: WorkflowContext) -> None:
        from ...services.abstract_enrichment import enrich_recent_papers
        workspace_id = context.execution.workspace_id
        enriched = await enrich_recent_papers(context.db, workspace_id, limit=30)
        context.summary["abstracts_enriched"] = enriched
        await context.log("info", f"Enriched {enriched} paper abstracts")
