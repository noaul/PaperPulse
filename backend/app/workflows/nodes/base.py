from ..context import WorkflowContext


class WorkflowNode:
    def __init__(self, name: str):
        self.name = name

    async def run(self, context: WorkflowContext) -> None:
        raise NotImplementedError
