import json
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AnalysisResult, EmailDelivery, EmailTopicRule, Feed, Keyword, Paper, Report, ReportItem, Setting
from .email_sender import build_email_html, get_email_config, open_smtp_connection
from .rss_fetcher import clean_text, normalize_paper_url
from .topic_rule_engine import evaluate_rule


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _report_title(now: datetime | None = None, topic_name: str | None = None) -> str:
    current = now or _utc_now()
    suffix = f" - {topic_name}" if topic_name else ""
    return f"PaperPulse Literature Report{suffix} - {current.strftime('%Y-%m-%d')}"


def _render_markdown(title: str, items: list[dict]) -> str:
    lines = [f"# {title}", ""]
    if not items:
        lines.append("No papers with a positive score were found.")
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


async def collect_recent_report_items(
    db: AsyncSession,
    *,
    paper_ids: list[int] | None = None,
    workspace_id: int = 1,
    topic_rule: EmailTopicRule | None = None,
) -> list[dict]:
    today = _utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    query = (
        select(AnalysisResult, Paper, Keyword, Feed.journal_name)
        .join(Paper, AnalysisResult.paper_id == Paper.id)
        .join(Keyword, AnalysisResult.keyword_id == Keyword.id)
        .outerjoin(Feed, Paper.feed_id == Feed.id)
        .where(AnalysisResult.relevance_score > 0)
        .where(AnalysisResult.workspace_id == workspace_id)
        .where(Paper.workspace_id == workspace_id)
        .where(Keyword.workspace_id == workspace_id)
        .order_by(desc(AnalysisResult.relevance_score), desc(AnalysisResult.analyzed_at))
    )
    if paper_ids is None:
        query = query.where(AnalysisResult.analyzed_at >= today)
    elif not paper_ids:
        return []
    else:
        query = query.where(AnalysisResult.paper_id.in_(paper_ids))

    result = await db.execute(query)

    grouped: dict[int, dict] = {}
    paper_keyword_scores: dict[int, dict[int, float]] = {}
    for analysis, paper, keyword, journal_name in result.all():
        paper_keyword_scores.setdefault(paper.id, {})[keyword.id] = float(analysis.relevance_score or 0)
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

    items = list(grouped.values())
    if topic_rule:
        items = [
            item
            for item in items
            if evaluate_rule(
                topic_rule.rule_type,
                required_keyword_ids=topic_rule.keyword_ids,
                exclude_keyword_ids=topic_rule.exclude_keyword_ids,
                paper_keyword_scores=paper_keyword_scores.get(item["paper_id"], {}),
            )
        ]

    return sorted(items, key=lambda item: item["score"], reverse=True)


async def create_report_from_recent_analyses(
    db: AsyncSession,
    *,
    source: str = "manual",
    paper_ids: list[int] | None = None,
    analyzed_count: int | None = None,
    related_count: int | None = None,
    workspace_id: int = 1,
    topic_rule: EmailTopicRule | None = None,
) -> Report:
    items = await collect_recent_report_items(
        db,
        paper_ids=paper_ids,
        workspace_id=workspace_id,
        topic_rule=topic_rule,
    )
    title = _report_title(topic_name=topic_rule.name if topic_rule else None)
    markdown = _render_markdown(title, items)
    html = await build_email_html(
        items,
        analyzed_count=analyzed_count,
        related_count=related_count,
    )
    report = Report(
        title=title,
        workspace_id=workspace_id,
        topic_rule_id=topic_rule.id if topic_rule else None,
        source=source,
        status="ready",
        threshold=0.0,
        paper_count=len(items),
        markdown=markdown,
        html=html,
    )
    db.add(report)
    await db.flush()

    for item in items:
        db.add(ReportItem(
            report_id=report.id,
            workspace_id=workspace_id,
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
    if report.topic_rule_id:
        rule = await db.get(EmailTopicRule, report.topic_rule_id)
        if rule and rule.recipients:
            recipient = rule.recipients
    subject = f"[PaperPulse] {report.title}"
    delivery = EmailDelivery(
        report_id=report.id,
        workspace_id=report.workspace_id,
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


def report_has_email_content(report: Report) -> bool:
    return report.paper_count > 0


async def create_and_send_recent_report(
    db: AsyncSession,
    source: str = "manual",
    *,
    paper_ids: list[int] | None = None,
    analyzed_count: int | None = None,
    related_count: int | None = None,
    workspace_id: int = 1,
) -> dict:
    rule_result = await db.execute(
        select(EmailTopicRule)
        .where(EmailTopicRule.workspace_id == workspace_id, EmailTopicRule.enabled == True)
        .order_by(EmailTopicRule.id)
    )
    rules = rule_result.scalars().all()
    if rules:
        topic_reports = []
        sent_count = 0
        total_papers = 0
        for rule in rules:
            report = await create_report_from_recent_analyses(
                db,
                source=source,
                paper_ids=paper_ids,
                analyzed_count=analyzed_count,
                related_count=related_count,
                workspace_id=workspace_id,
                topic_rule=rule,
            )
            delivery = None
            if report.paper_count > 0:
                delivery = await send_report_email(db, report.id)
                if delivery.status == "sent":
                    sent_count += 1
            total_papers += report.paper_count
            topic_reports.append({
                "topic_rule_id": rule.id,
                "report_id": report.id,
                "paper_count": report.paper_count,
                "sent": bool(delivery and delivery.status == "sent"),
                "skipped": report.paper_count == 0 or bool(delivery and delivery.status == "skipped"),
                "reason": "" if report.paper_count > 0 else "没有匹配该主题规则的论文",
                "delivery_id": delivery.id if delivery else None,
            })

        first = topic_reports[0] if topic_reports else {}
        return {
            "report_id": first.get("report_id"),
            "sent": sent_count > 0,
            "sent_count": sent_count,
            "skipped": sent_count == 0,
            "reason": "" if sent_count > 0 else "没有主题邮件发送",
            "paper_count": total_papers,
            "delivery_id": first.get("delivery_id"),
            "topic_reports": topic_reports,
        }

    report = await create_report_from_recent_analyses(
        db,
        source=source,
        paper_ids=paper_ids,
        analyzed_count=analyzed_count,
        related_count=related_count,
        workspace_id=workspace_id,
    )
    if not report_has_email_content(report):
        return {
            "report_id": report.id,
            "sent": False,
            "skipped": True,
            "reason": "没有可发送的论文",
            "paper_count": report.paper_count,
            "delivery_id": None,
        }
    delivery = await send_report_email(db, report.id)
    return {
        "report_id": report.id,
        "sent": delivery.status == "sent",
        "skipped": delivery.status == "skipped",
        "reason": delivery.error_message or "",
        "paper_count": report.paper_count,
        "delivery_id": delivery.id,
    }
