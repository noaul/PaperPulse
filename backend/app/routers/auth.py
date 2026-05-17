import json
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Setting

router = APIRouter(prefix="/api/auth", tags=["auth"])

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "168"))  # 7 days


def _resolve_jwt_secret() -> str:
    """Auto-generate and persist a random JWT secret if using the insecure default."""
    import secrets
    env_val = os.environ.get("JWT_SECRET", "")
    if env_val and env_val != "paperpulse-change-me-in-production":
        return env_val
    # Persist to data dir so it survives restarts
    data_dir = os.path.dirname(os.environ.get("DB_PATH", "/app/data/paperpulse.db"))
    secret_file = os.path.join(data_dir, ".jwt_secret")
    if os.path.isfile(secret_file):
        return open(secret_file).read().strip()
    secret = secrets.token_urlsafe(32)
    os.makedirs(data_dir, exist_ok=True)
    with open(secret_file, "w") as f:
        f.write(secret)
    return secret


JWT_SECRET = _resolve_jwt_secret()

# Simple in-memory rate limiter for login attempts
_login_attempts: dict[str, list[float]] = defaultdict(list)
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 60


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
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    # Support legacy SHA-256 hashes for seamless migration
    import hashlib
    if len(hashed) == 64 and all(c in "0123456789abcdef" for c in hashed):
        if hashlib.sha256(password.encode()).hexdigest() == hashed:
            return True
        return False
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _create_token(username: str) -> str:
    payload = {
        "sub": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Verify JWT token and return payload, or None if invalid."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    attempts = _login_attempts[client_ip]
    # Remove old entries
    _login_attempts[client_ip] = [t for t in attempts if now - t < _LOGIN_WINDOW_SECONDS]
    if len(_login_attempts[client_ip]) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(429, "登录尝试过于频繁，请稍后再试")


def _record_attempt(client_ip: str) -> None:
    _login_attempts[client_ip].append(time.time())


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


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = await _get_admin_user(db)
    if not user:
        _record_attempt(client_ip)
        raise HTTPException(400, "未注册管理员账户，请先注册")

    if user["username"] != req.username or not _verify_password(req.password, user["password_hash"]):
        _record_attempt(client_ip)
        raise HTTPException(401, "用户名或密码错误")

    # Auto-upgrade legacy SHA-256 hash to bcrypt on successful login
    if len(user["password_hash"]) == 64:
        new_hash = _hash_password(req.password)
        await _save_admin_user(db, user["username"], new_hash)

    token = _create_token(user["username"])
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

    # Update cached state
    from ..main import set_admin_registered
    set_admin_registered(True)

    token = _create_token(req.username)
    return TokenResponse(token=token, username=req.username)


@router.get("/check")
async def check_auth(db: AsyncSession = Depends(get_db)):
    """Check if an admin user exists (used by frontend to decide login vs register)."""
    user = await _get_admin_user(db)
    return {"registered": user is not None}
