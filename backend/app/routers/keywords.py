from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..models import Keyword
from ..schemas import KeywordCreate, KeywordUpdate, KeywordOut

router = APIRouter(prefix="/api/keywords", tags=["keywords"])


@router.get("", response_model=list[KeywordOut])
async def list_keywords(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Keyword).order_by(Keyword.category, Keyword.word))
    return [KeywordOut.model_validate(k) for k in result.scalars().all()]


@router.post("", response_model=KeywordOut)
async def create_keyword(data: KeywordCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Keyword).where(Keyword.word == data.word))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Keyword already exists")
    kw = Keyword(**data.model_dump())
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    return KeywordOut.model_validate(kw)


@router.put("/{kw_id}", response_model=KeywordOut)
async def update_keyword(kw_id: int, data: KeywordUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Keyword).where(Keyword.id == kw_id))
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(404, "Keyword not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(kw, k, v)
    await db.commit()
    await db.refresh(kw)
    return KeywordOut.model_validate(kw)


@router.delete("/{kw_id}")
async def delete_keyword(kw_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Keyword).where(Keyword.id == kw_id))
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(404, "Keyword not found")
    await db.delete(kw)
    await db.commit()
    return {"success": True}
