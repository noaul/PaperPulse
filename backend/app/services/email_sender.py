import smtplib
import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Setting
from .rss_fetcher import normalize_paper_url
from datetime import datetime

logger = logging.getLogger(__name__)


async def get_email_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Setting).where(Setting.key == "email_config"))
    row = result.scalar_one_or_none()
    if row:
        return json.loads(row.value)
    return {}


def build_paper_url(url: str | None, doi: str | None) -> str:
    if url:
        return normalize_paper_url(url)
    if doi:
        return f"https://doi.org/{doi}"
    return ""


def open_smtp_connection(config: dict):
    server = config["smtp_server"]
    port = int(config.get("smtp_port", 587))
    if port == 465:
        return smtplib.SMTP_SSL(server, port, timeout=20)
    return smtplib.SMTP(server, port, timeout=20)


async def build_email_html(
    papers_data: list[dict],
    *,
    threshold: float | None = None,
    analyzed_count: int | None = None,
    related_count: int | None = None,
) -> str:
    html = """<html><head><style>
    body{font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#333}
    .paper{border:1px solid #e0e0e0;border-radius:8px;padding:16px;margin:12px 0;background:#fafafa}
    .title{font-size:16px;font-weight:bold;color:#1a5276;margin-bottom:6px}
    .title a{color:#1a5276;text-decoration:none}
    .meta{font-size:13px;color:#666;margin-bottom:8px}
    .score{display:inline-block;background:#27ae60;color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold}
    .score.mid{background:#f39c12}
    .score.low{background:#e74c3c}
    .summary{font-size:14px;color:#555;margin-top:6px;padding:8px;background:#eaf2f8;border-radius:4px}
    .abstract{font-size:13px;color:#555;margin-top:8px;line-height:1.5}
    .keyword-tag{display:inline-block;background:#3498db;color:white;padding:1px 6px;border-radius:3px;font-size:11px;margin:2px}
    h2{color:#2c3e50;border-bottom:2px solid #3498db;padding-bottom:6px}
    </style></head><body>
    <h2>📄 PaperPulse Daily Report</h2>
    <p style="color:#666">""" + datetime.now().strftime("%Y-%m-%d") + """</p>
    """

    if not papers_data:
        detail_parts = []
        if threshold is not None:
            detail_parts.append(f"报告阈值 {float(threshold):.1f}")
        if analyzed_count is not None:
            detail_parts.append(f"本次分析 {int(analyzed_count)} 篇")
        if related_count is not None:
            detail_parts.append(f"AI 判定相关 {int(related_count)} 篇")
        details = "，".join(detail_parts)
        if details:
            details = f"（{details}）"
        html += f"""
        <div class="paper">
            <div class="title">未达到报告阈值的论文</div>
            <div class="summary">本次日报没有论文达到配置的相关性阈值{details}。</div>
        </div>"""

    for item in papers_data:
        score = item.get("score", 0)
        score_class = "" if score >= 7 else "mid" if score >= 5 else "low"
        html += f"""
        <div class="paper">
            <div class="title"><a href="{item.get('url', '#')}">{item['title']}</a></div>
            <div class="meta">{item.get('authors', '')} | {item.get('journal', '')} | <span class="score {score_class}">Score: {score:.1f}</span></div>
            <div>{' '.join(f'<span class="keyword-tag">{k}</span>' for k in item.get('keywords', []))}</div>
            <div class="summary">{item.get('summary', '')}</div>
            <div class="abstract"><strong>Abstract:</strong> {item.get('abstract', '')}</div>
        </div>"""

    html += "</body></html>"
    return html


async def send_daily_report(
    db: AsyncSession,
    threshold: float = 6.0,
    *,
    paper_ids: list[int] | None = None,
    analyzed_count: int | None = None,
    related_count: int | None = None,
) -> dict:
    from .report_center import create_and_send_recent_report

    result = await create_and_send_recent_report(
        db,
        threshold=threshold,
        source="daily-email",
        paper_ids=paper_ids,
        analyzed_count=analyzed_count,
        related_count=related_count,
    )
    if result["sent"]:
        logger.info("Email sent: report=%s papers=%s", result["report_id"], result["paper_count"])
    elif result["skipped"]:
        logger.info("Email skipped: %s", result["reason"])
    else:
        logger.error("Email failed: %s", result["reason"])
    return result
