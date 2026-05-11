from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..workflows.daily import run_daily_workflow

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("/daily/run")
async def run_daily(db: AsyncSession = Depends(get_db)):
    execution = await run_daily_workflow(db)
    return {
        "success": execution.status == "success",
        "execution_id": execution.id,
        "status": execution.status,
        "summary": execution.summary_dict,
    }
