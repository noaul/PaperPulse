import hashlib
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Setting

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    username: str


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


async def _get_admin_user(db: AsyncSession) -> dict | None:
    result = await db.execute(select(Setting).where(Setting.key == "admin_user"))
    row = result.scalar_one_or_none()
    if row:
        return json.loads(row.value)
    return None


async def _save_admin_user(db: AsyncSession, username: str, password_hash: str):
    value = json.dumps({"username": username, "password_hash": password_hash})
    result = await db.execute(select(Setting).where(Setting.key == "admin_user"))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(Setting(key="admin_user", value=value))
    await db.commit()


async def _save_token(db: AsyncSession, token: str):
    result = await db.execute(select(Setting).where(Setting.key == "auth_token"))
    row = result.scalar_one_or_none()
    if row:
        row.value = token
    else:
        db.add(Setting(key="auth_token", value=token))
    await db.commit()


async def _get_token(db: AsyncSession) -> str | None:
    result = await db.execute(select(Setting).where(Setting.key == "auth_token"))
    row = result.scalar_one_or_none()
    if row:
        return row.value
    return None


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await _get_admin_user(db)
    if not user:
        raise HTTPException(400, "未注册管理员账户，请先注册")

    if user["username"] != req.username or user["password_hash"] != _hash_password(req.password):
        raise HTTPException(401, "用户名或密码错误")

    token = str(uuid.uuid4())
    await _save_token(db, token)
    return TokenResponse(token=token, username=user["username"])


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await _get_admin_user(db)
    if existing:
        raise HTTPException(400, "管理员账户已存在")

    if len(req.password) < 4:
        raise HTTPException(400, "密码长度不能少于4位")

    password_hash = _hash_password(req.password)
    await _save_admin_user(db, req.username, password_hash)

    token = str(uuid.uuid4())
    await _save_token(db, token)
    return TokenResponse(token=token, username=req.username)


@router.get("/check")
async def check_auth(db: AsyncSession = Depends(get_db)):
    """Check if an admin user exists (used by frontend to decide login vs register)."""
    user = await _get_admin_user(db)
    return {"registered": user is not None}
