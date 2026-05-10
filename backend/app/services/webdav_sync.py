import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Feed, Keyword, Setting

logger = logging.getLogger(__name__)


async def get_webdav_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Setting).where(Setting.key == "webdav_config"))
    row = result.scalar_one_or_none()
    if row:
        return json.loads(row.value)
    return {}


def _get_client(config: dict):
    from webdav3.client import Client
    options = {
        "webdav_hostname": config["url"],
        "webdav_login": config.get("username", ""),
        "webdav_password": config.get("password", ""),
    }
    return Client(options)


async def export_data(db: AsyncSession) -> bool:
    config = await get_webdav_config(db)
    if not config.get("url"):
        logger.info("WebDAV not configured")
        return False

    feeds_result = await db.execute(select(Feed))
    feeds = [{"name": f.name, "url": f.url, "journal_name": f.journal_name, "enabled": f.enabled} for f in feeds_result.scalars().all()]

    kw_result = await db.execute(select(Keyword))
    keywords = [{"word": k.word, "category": k.category, "enabled": k.enabled} for k in kw_result.scalars().all()]

    data = {"feeds": feeds, "keywords": keywords}
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    try:
        client = _get_client(config)
        remote_path = config.get("remote_path", "/PaperPulse/")
        if not client.check(remote_path):
            client.mkdir(remote_path)
        import io
        client.upload_sync(remote_path + "paperpulse_backup.json", io.BytesIO(content))
        logger.info(f"Data exported to WebDAV: {remote_path}")
        return True
    except Exception as e:
        logger.error(f"WebDAV export failed: {e}")
        return False


async def import_data(db: AsyncSession) -> bool:
    config = await get_webdav_config(db)
    if not config.get("url"):
        return False

    try:
        client = _get_client(config)
        remote_path = config.get("remote_path", "/PaperPulse/") + "paperpulse_backup.json"
        import io
        buf = io.BytesIO()
        client.download_sync(remote_path, buf)
        buf.seek(0)
        data = json.loads(buf.read().decode("utf-8"))

        for feed_data in data.get("feeds", []):
            existing = await db.execute(select(Feed).where(Feed.url == feed_data["url"]))
            if not existing.scalar_one_or_none():
                db.add(Feed(**feed_data))

        for kw_data in data.get("keywords", []):
            existing = await db.execute(select(Keyword).where(Keyword.word == kw_data["word"]))
            if not existing.scalar_one_or_none():
                db.add(Keyword(**kw_data))

        await db.commit()
        logger.info("Data imported from WebDAV")
        return True
    except Exception as e:
        logger.error(f"WebDAV import failed: {e}")
        return False
