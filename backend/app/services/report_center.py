import json
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AnalysisResult, EmailDelivery, Feed, Keyword, Paper, Report, ReportItem, Setting
from .email_sender import build_email_html, get_email_config, open_smtp_connection
from .rss_fetcher import clean_text, normalize_paper_url


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _report_title(now: datetime | None = None) -> str:
    current = now or _utc_now()
    return f"PaperPulse Literature Report - {current.strftime('%Y-%m-%d')}"


def _render_markdown(title: str, items: list[dict]) -> str:
    lines = [f"# {title}", ""]
    if not items:
        lines.append("No papers matched the configured threshold.")
        return "\n".join(lines)

    for index, item in enumerate(items, start=1):
        lines.extend([
            f"## {index}. {item['title']}",
            "",
            f"- Score: {item['score']:.1f}",
            f"- Journal: {item.get('journal') or '-'}",
            f"- Authors: {item.get('authors') or '-'}",
            f"- Keywords: {', '.join(item.get('keywords') or []) or '-'}",
            f"- Link: {item.get('url') or '-'}",
            "",
            f"**AI Summary:** {item.get('summary') or '-'}",
            "",
            f"**Abstract:** {item.get('abstract') or '-'}",
            "",
        ])
    return "\n".join(lines).strip() + "\n"


async def collect_recent_report_items(db: AsyncSession, threshold: float) -> list[dict]:
    today = _utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(AnalysisResult, Paper, Keyword, Feed.journal_name)
        .join(Paper, AnalysisResult.paper_id == Paper.id)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .outerjoin(Feed, Paper.feed_id == Feed.id)
        .where(AnalysisResult.analyzed_at >= today)
        .where(AnalysisResult.relevance_score >= threshold)
        .order_by(desc(AnalysisResult.relevance_score), desc(AnalysisResult.analyzed_at))
    )

    grouped: dict[int, dict] = {}
    for analysis, paper, keyword, journal_name in result.all():
        item = grouped.setdefault(
            paper.id,
            {
                "paper_id": paper.id,
                "title": clean_text(paper.title),
                "authors": clean_text(paper.authors),
                "abstract": clean_text(paper.abstract),
                "url": normalize_paper_url(paper.url),
                "journal": journal_name or "",
                "score": float(analysis.relevance_score or 0),
                "summary": analysis.summary or "",
                "keywords": [],
            },
        )
        item["score"] = max(float(item["score"]), float(analysis.relevance_score or 0))
        if analysis.summary and float(analysis.relevance_score or 0) >= float(item["score"]):
            item["summary"] = analysis.summary
        if keyword.word not in item["keywords"]:
            item["keywords"].append(keyword.word)

    return sorted(grouped.values(), key=lambda item: item["score"], reverse=True)


async def create_report_from_recent_analyses(
    db: AsyncSession,
    *,
    threshold: float = 6.0,
    source: str = "manual",
) -> Report:
    items = await collect_recent_report_items(db, threshold)
    title = _report_title()
    markdown = _render_markdown(title, items)
    html = await build_email_html(items)
    report = Report(
        title=title,
        source=source,
        status="ready",
        threshold=threshold,
        paper_count=len(items),
        max_relevance_score=max((item["score"] for item in items), default=0),
        markdown=markdown,
        html=html,
    )
    db.add(report)
    await db.flush()

    for item in items:
        db.add(ReportItem(
            report_id=report.id,
            paper_id=item["paper_id"],
            title=item["title"],
            authors=item["authors"],
            abstract=item["abstract"],
            url=item["url"],
            journal_name=item["journal"],
            relevance_score=item["score"],
            summary=item["summary"],
            keywords_json=json.dumps(item["keywords"], ensure_ascii=False),
        ))

    await db.commit()
    await db.refresh(report)
    return report


async def _load_report(db: AsyncSession, report_id: int) -> Report:
    report = await db.get(Report, report_id)
    if not report:
        raise ValueError("Report not found")
    return report


async def send_report_email(db: AsyncSession, report_id: int) -> EmailDelivery:
    report = await _load_report(db, report_id)
    config = await get_email_config(db)
    recipient = config.get("recipient") or ""
    subject = f"[PaperPulse] {report.title}"
    delivery = EmailDelivery(
        report_id=report.id,
        recipient=recipient,
        subject=subject,
        status="pending",
        paper_count=report.paper_count,
    )
    db.add(delivery)
    await db.flush()

    if not config.get("enabled") or not recipient:
        delivery.status = "skipped"
        delivery.error_message = "邮件未启用或收件人为空"
        await db.commit()
        await db.refresh(delivery)
        return delivery

    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{config.get('sender_name', 'PaperPulse')} <{config['smtp_user']}>"
        msg["To"] = recipient
        msg.attach(MIMEText(report.html or report.markdown, "html", "utf-8"))

        with open_smtp_connection(config) as server:
            if int(config.get("smtp_port", 587)) != 465:
                server.starttls()
            server.login(config["smtp_user"], config["smtp_password"])
            server.send_message(msg)

        now = _utc_now()
        delivery.status = "sent"
        delivery.sent_at = now
        report.sent_at = now
        report.status = "sent"
        db.add(report)
    except Exception as exc:
        delivery.status = "failed"
        delivery.error_message = str(exc)

    await db.commit()
    await db.refresh(delivery)
    return delivery


async def create_and_send_recent_report(db: AsyncSession, threshold: float, source: str = "manual") -> dict:
    report = await create_report_from_recent_analyses(db, threshold=threshold, source=source)
    delivery = await send_report_email(db, report.id)
    return {
        "report_id": report.id,
        "sent": delivery.status == "sent",
        "skipped": delivery.status == "skipped",
        "reason": delivery.error_message or "",
        "paper_count": report.paper_count,
        "delivery_id": delivery.id,
    }
