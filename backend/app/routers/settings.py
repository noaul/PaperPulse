import json
import smtplib
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Setting
from ..schemas import AIConfig, EmailConfig, WebDAVConfig, ScheduleConfig
from ..services.ai_analyzer import build_chat_completions_url, DEFAULT_AI_CONFIG

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


@router.post("/ai/test")
async def test_ai_config(data: AIConfig | None = None, db: AsyncSession = Depends(get_db)):
    config = data.model_dump() if data else await _get_setting(db, "ai_config", AIConfig().model_dump())
    if not config.get("enabled"):
        raise HTTPException(400, "AI 功能未启用")
    if not config.get("api_key"):
        raise HTTPException(400, "AI API Key 为空")
    if not config.get("model"):
        raise HTTPException(400, "模型名称为空")

    try:
        url = build_chat_completions_url(config.get("api_base", ""))
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.get("model", DEFAULT_AI_CONFIG["model"]),
                    "messages": [{"role": "user", "content": "Reply OK"}],
                    "temperature": 0,
                    "max_tokens": 8,
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(exc.response.status_code, f"AI 服务返回错误: {exc.response.text[:200]}") from exc
    except Exception as exc:
        raise HTTPException(400, f"AI 连接失败: {exc}") from exc

    return {"success": True}


@router.post("/email/test")
async def test_email_config(data: EmailConfig | None = None, db: AsyncSession = Depends(get_db)):
    config = data.model_dump() if data else await _get_setting(db, "email_config", EmailConfig().model_dump())
    required = ["smtp_server", "smtp_user", "smtp_password", "recipient"]
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise HTTPException(400, f"邮件配置不完整: {', '.join(missing)}")

    try:
        msg = "Subject: PaperPulse test\n\nPaperPulse email configuration test."
        with smtplib.SMTP(config["smtp_server"], int(config.get("smtp_port", 587)), timeout=20) as server:
            server.starttls()
            server.login(config["smtp_user"], config["smtp_password"])
            server.sendmail(config["smtp_user"], [config["recipient"]], msg.encode("utf-8"))
    except Exception as exc:
        raise HTTPException(400, f"邮件发送失败: {exc}") from exc

    return {"success": True}


@router.post("/webdav/test")
async def test_webdav_config(data: WebDAVConfig | None = None, db: AsyncSession = Depends(get_db)):
    config = data.model_dump() if data else await _get_setting(db, "webdav_config", WebDAVConfig().model_dump())
    if not config.get("url"):
        raise HTTPException(400, "WebDAV URL 为空")

    try:
        from webdav3.client import Client

        client = Client({
            "webdav_hostname": config["url"],
            "webdav_login": config.get("username", ""),
            "webdav_password": config.get("password", ""),
        })
        remote_path = config.get("remote_path") or "/"
        exists = client.check(remote_path)
    except Exception as exc:
        raise HTTPException(400, f"WebDAV 连接失败: {exc}") from exc

    return {"success": True, "path_exists": exists}
