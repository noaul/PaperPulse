import json
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Setting
from ..schemas import AIConfig, EmailConfig, WebDAVConfig, ScheduleConfig

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _get_setting(db: AsyncSession, key: str, default: dict) -> dict:
    result = await db.execute(select(Setting).where(Setting.key == key))
    row = result.scalar_one_or_none()
    return json.loads(row.value) if row else default


async def _set_setting(db: AsyncSession, key: str, value: dict):
    result = await db.execute(select(Setting).where(Setting.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = json.dumps(value, ensure_ascii=False)
    else:
        db.add(Setting(key=key, value=json.dumps(value, ensure_ascii=False)))
    await db.commit()


@router.get("/ai")
async def get_ai_config(db: AsyncSession = Depends(get_db)):
    return await _get_setting(db, "ai_config", AIConfig().model_dump())


@router.put("/ai")
async def set_ai_config(data: AIConfig, db: AsyncSession = Depends(get_db)):
    await _set_setting(db, "ai_config", data.model_dump())
    return {"success": True}


@router.get("/email")
async def get_email_config(db: AsyncSession = Depends(get_db)):
    return await _get_setting(db, "email_config", EmailConfig().model_dump())


@router.put("/email")
async def set_email_config(data: EmailConfig, db: AsyncSession = Depends(get_db)):
    await _set_setting(db, "email_config", data.model_dump())
    return {"success": True}


@router.get("/webdav")
async def get_webdav_config(db: AsyncSession = Depends(get_db)):
    return await _get_setting(db, "webdav_config", WebDAVConfig().model_dump())


@router.put("/webdav")
async def set_webdav_config(data: WebDAVConfig, db: AsyncSession = Depends(get_db)):
    await _set_setting(db, "webdav_config", data.model_dump())
    return {"success": True}


@router.get("/schedule")
async def get_schedule_config(db: AsyncSession = Depends(get_db)):
    return await _get_setting(db, "schedule_config", ScheduleConfig().model_dump())


@router.put("/schedule")
async def set_schedule_config(data: ScheduleConfig, db: AsyncSession = Depends(get_db)):
    await _set_setting(db, "schedule_config", data.model_dump())
    return {"success": True}
