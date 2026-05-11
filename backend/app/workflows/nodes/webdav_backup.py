from .base import WorkflowNode
from ..context import WorkflowContext
from ...services.webdav_sync import export_data, get_webdav_config


class WebdavBackupNode(WorkflowNode):
    def __init__(self):
        super().__init__("webdav-backup")

    async def run(self, context: WorkflowContext) -> None:
        config = await get_webdav_config(context.db)
        if not config.get("url"):
            context.summary["webdav_exported"] = False
            await context.log("info", "WebDAV backup skipped", {"reason": "not_configured"})
            return

        exported = await export_data(context.db)
        context.summary["webdav_exported"] = exported
        level = "info" if exported else "warning"
        await context.log(level, "WebDAV backup completed" if exported else "WebDAV backup failed", {
            "exported": exported,
        })
