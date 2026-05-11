from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import EmailDelivery, Report, ReportItem
from ..schemas import EmailDeliveryOut, ReportCreate, ReportDetail, ReportItemOut, ReportOut
from ..services.report_center import create_report_from_recent_analyses, send_report_email

router = APIRouter(prefix="/api/reports", tags=["reports"])


def report_out(report: Report) -> ReportOut:
    return ReportOut(
        id=report.id,
        title=report.title,
        source=report.source,
        status=report.status,
        threshold=report.threshold,
        paper_count=report.paper_count,
        max_relevance_score=report.max_relevance_score,
        created_at=report.created_at,
        sent_at=report.sent_at,
    )


def report_item_out(item: ReportItem) -> ReportItemOut:
    return ReportItemOut(
        id=item.id,
        report_id=item.report_id,
        paper_id=item.paper_id,
        title=item.title,
        authors=item.authors,
        abstract=item.abstract,
        url=item.url,
        journal_name=item.journal_name,
        relevance_score=item.relevance_score,
        summary=item.summary,
        keywords=item.keywords,
    )


def delivery_out(delivery: EmailDelivery) -> EmailDeliveryOut:
    return EmailDeliveryOut(
        id=delivery.id,
        report_id=delivery.report_id,
        recipient=delivery.recipient,
        subject=delivery.subject,
        status=delivery.status,
        error_message=delivery.error_message,
        paper_count=delivery.paper_count,
        created_at=delivery.created_at,
        sent_at=delivery.sent_at,
    )


async def get_report_or_404(db: AsyncSession, report_id: int) -> Report:
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.items), selectinload(Report.deliveries))
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    return report


@router.get("", response_model=list[ReportOut])
async def list_reports(limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).order_by(desc(Report.created_at), desc(Report.id)).limit(limit))
    return [report_out(report) for report in result.scalars().all()]


@router.post("", response_model=ReportOut)
async def create_report(payload: ReportCreate, db: AsyncSession = Depends(get_db)):
    report = await create_report_from_recent_analyses(
        db,
        threshold=payload.threshold,
        source=payload.source,
    )
    return report_out(report)


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    report = await get_report_or_404(db, report_id)
    base = report_out(report).model_dump()
    return ReportDetail(
        **base,
        markdown=report.markdown or "",
        html=report.html or "",
        items=[report_item_out(item) for item in report.items],
        deliveries=[delivery_out(delivery) for delivery in report.deliveries],
    )


@router.post("/{report_id}/send", response_model=EmailDeliveryOut)
async def send_report(report_id: int, db: AsyncSession = Depends(get_db)):
    try:
        delivery = await send_report_email(db, report_id)
    except ValueError:
        raise HTTPException(404, "Report not found")
    return delivery_out(delivery)


@router.get("/{report_id}/markdown")
async def download_report_markdown(report_id: int, db: AsyncSession = Depends(get_db)):
    report = await get_report_or_404(db, report_id)
    filename = f"paperpulse-report-{report.id}.md"
    return Response(
        content=report.markdown or "",
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/deliveries", response_model=list[EmailDeliveryOut])
async def list_report_deliveries(report_id: int, db: AsyncSession = Depends(get_db)):
    await get_report_or_404(db, report_id)
    result = await db.execute(
        select(EmailDelivery)
        .where(EmailDelivery.report_id == report_id)
        .order_by(desc(EmailDelivery.created_at), desc(EmailDelivery.id))
    )
    return [delivery_out(delivery) for delivery in result.scalars().all()]
